import datetime
import json
import logging
import re
from http import HTTPStatus
from io import BytesIO
from pathlib import Path

import backoff
from jinja2 import Environment, FileSystemLoader, select_autoescape
from joblib import Parallel, delayed
from pydantic import BaseModel
from requests import RequestException
from requests.exceptions import HTTPError
from schedule import every, run_pending
from zimscraperlib.image import convert_image, resize_image
from zimscraperlib.image.conversion import convert_svg2png
from zimscraperlib.image.probing import format_for
from zimscraperlib.rewriting.css import CssRewriter
from zimscraperlib.rewriting.html import HtmlRewriter
from zimscraperlib.rewriting.url_rewriting import (
    ArticleUrlRewriter,
    HttpUrl,
    RewriteResult,
    ZimPath,
)
from zimscraperlib.zim import Creator
from zimscraperlib.zim.filesystem import (
    validate_file_creatable,
    validate_folder_writable,
)
from zimscraperlib.zim.indexing import IndexData

from mindtouch2zim.asset import AssetDetails, AssetProcessor
from mindtouch2zim.client import (
    LibraryPage,
    LibraryPageId,
    LibraryTree,
    MindtouchClient,
    MindtouchHome,
)
from mindtouch2zim.constants import (
    NAME,
    ROOT_DIR,
    VERSION,
    logger,
)
from mindtouch2zim.context import Context
from mindtouch2zim.download import stream_file
from mindtouch2zim.errors import NoIllustrationFoundError
from mindtouch2zim.html import get_text
from mindtouch2zim.html_rewriting import HtmlUrlsRewriter
from mindtouch2zim.libretexts.detailed_licensing import rewrite_detailed_licensing
from mindtouch2zim.libretexts.glossary import rewrite_glossary
from mindtouch2zim.libretexts.index import rewrite_index
from mindtouch2zim.libretexts.table_of_content import rewrite_table_of_content
from mindtouch2zim.ui import (
    ConfigModel,
    PageContentModel,
    PageModel,
    SharedModel,
)
from mindtouch2zim.utils import backoff_hdlr
from mindtouch2zim.zimconfig import ZimConfig

context = Context.get()


class ContentFilter(BaseModel):
    """Supports filtering documents by user provided attributes."""

    # If specified, only pages with title matching the regex are included.
    page_title_include: re.Pattern[str] | None
    # If specified, only page with matching ids are included.
    page_id_include: list[str] | None
    # If specified, page with title matching the regex are excluded.
    page_title_exclude: re.Pattern[str] | None
    # If specified, only this page and its subpages will be included.
    root_page_id: str | None

    def filter(self, page_tree: LibraryTree) -> list[LibraryPage]:
        """Filters pages based on the user's choices."""

        if self.root_page_id:
            page_tree = page_tree.sub_tree(self.root_page_id)

        def is_selected(
            title_include_re: re.Pattern[str] | None,
            title_exclude_re: re.Pattern[str] | None,
            id_include: list[LibraryPageId] | None,
            page: LibraryPage,
        ) -> bool:
            return (
                (
                    not title_include_re
                    or title_include_re.search(page.title) is not None
                )
                and (not id_include or page.id in id_include)
                and (
                    not title_exclude_re or title_exclude_re.search(page.title) is None
                )
            )

        # Find selected pages and their parent, and create a set of unique ids
        selected_ids = {
            selected_page.id
            for page in page_tree.pages.values()
            for selected_page in page.self_and_parents
            if is_selected(
                self.page_title_include,
                self.page_title_exclude,
                self.page_id_include,
                page,
            )
        }

        # Then transform set of ids into list of pages
        return [page for page in page_tree.pages.values() if page.id in selected_ids]


class Processor:
    """Generates ZIMs based on the user's configuration."""

    def __init__(self) -> None:
        """Initializes Processor."""

        self.mindtouch_client = MindtouchClient()
        self.asset_processor = AssetProcessor()
        self.asset_executor = Parallel(
            n_jobs=context.assets_workers,
            return_as="generator_unordered",
            backend="threading",
            timeout=600,  # fallback timeout of 10 minutes, should something go wrong
        )

        self.stats_items_done = 0
        # we add 1 more items to process so that progress is not 100% at the beginning
        # when we do not yet know how many items we have to process and so that we can
        # increase counter at the beginning of every for loop, not minding about what
        # could happen in the loop in terms of exit conditions
        self.stats_items_total = 1

    def run(self) -> Path:
        """Generates a zim for a single document.

        Returns the path to the gernated ZIM.
        """
        try:
            return self._run_internal()
        except Exception:
            logger.error(
                f"Problem encountered while processing "
                f"{context.current_thread_workitem}"
            )
            raise

    def _run_internal(self) -> Path:
        logger.setLevel(level=logging.DEBUG if context.debug else logging.INFO)

        self.zim_config = ZimConfig(
            file_name=context.file_name,
            name=context.name,
            title=context.title,
            publisher=context.publisher,
            creator=context.creator,
            description=context.description,
            long_description=context.long_description,
            tags=context.tags,
            secondary_color=context.secondary_color,
        )
        self.content_filter = ContentFilter(
            page_title_include=context.page_title_include,
            page_id_include=context.page_id_include,
            page_title_exclude=context.page_title_exclude,
            root_page_id=context.root_page_id,
        )

        # remove trailing slash which we do not want per convention
        context.library_url = context.library_url.rstrip("/")

        # initialize all paths, ensuring they are ok for operation
        context.output_folder.mkdir(exist_ok=True)
        validate_folder_writable(context.output_folder)

        context.tmp_folder.mkdir(exist_ok=True)
        validate_folder_writable(context.tmp_folder)

        context.cache_folder.mkdir(exist_ok=True)
        validate_folder_writable(context.cache_folder)

        logger.info("Generating ZIM")

        # create first progress report and and a timer to update every 10 seconds
        self._report_progress()
        every(10).seconds.do(  # pyright: ignore[reportUnknownMemberType]
            self._report_progress
        )

        self.formatted_config = self.zim_config.format(
            {
                "name": self.zim_config.name,
                "period": datetime.date.today().strftime("%Y-%m"),
            }
        )
        zim_file_name = f"{self.formatted_config.file_name}.zim"
        zim_path = context.output_folder / zim_file_name

        if zim_path.exists():
            if context.overwrite_existing_zim:
                zim_path.unlink()
            else:
                logger.error(f"  {zim_path} already exists, aborting.")
                raise SystemExit(2)

        validate_file_creatable(context.output_folder, zim_file_name)

        logger.info(f"  Writing to: {zim_path}")

        logger.debug(f"User-Agent: {context.wm_user_agent}")

        creator = Creator(zim_path, "index.html")

        logger.info("  Fetching and storing home page...")
        self.home = self.mindtouch_client.get_home()

        logger.info("  Fetching ZIM illustration...")
        zim_illustration = self._fetch_zim_illustration(self.home)

        logger.debug("Configuring metadata")
        creator.config_metadata(
            Name=self.formatted_config.name,
            Title=self.formatted_config.title,
            Publisher=self.formatted_config.publisher,
            Date=datetime.datetime.now(tz=datetime.UTC).date(),
            Creator=self.formatted_config.creator,
            Description=self.formatted_config.description,
            LongDescription=self.formatted_config.long_description,
            # As of 2024-09-4 all documentation is in English.
            Language=context.language_iso_639_3,
            Tags=self.formatted_config.tags,
            Scraper=f"{NAME} v{VERSION}",
            Illustration_48x48_at_1=zim_illustration.getvalue(),
        )

        # jinja2 environment setup
        self.jinja2_env = Environment(
            loader=FileSystemLoader(ROOT_DIR.joinpath("templates")),
            autoescape=select_autoescape(),
        )
        self.libretexts_glossary_template = self.jinja2_env.get_template(
            "libretexts.glossary.html"
        )
        self.libretexts_index_template = self.jinja2_env.get_template(
            "libretexts.index.html"
        )
        self.libretexts_detailed_licensing_template = self.jinja2_env.get_template(
            "libretexts.detailed-licensing.html"
        )
        self.libretexts_table_of_content_template = self.jinja2_env.get_template(
            "libretexts.table-of-content.html"
        )

        # Start creator early to detect problems early.
        with creator as creator:
            try:
                creator.add_item_for(
                    "favicon.ico",
                    content=self._fetch_favicon_from_illustration(
                        zim_illustration
                    ).getvalue(),
                )
                del zim_illustration

                self.run_with_creator(creator)
            except Exception:
                creator.can_finish = False
                raise

        if creator.can_finish:
            logger.info(f"ZIM creation completed, ZIM is at {zim_path}")
        else:
            logger.error("ZIM creation failed")

        # same reason than self.stats_items_done = 1 at the beginning, we need to add
        # a final item to complete the progress
        self.stats_items_done += 1
        self._report_progress()

        return zim_path

    def run_with_creator(self, creator: Creator):

        context.current_thread_workitem = "standard files"

        logger.info("  Storing configuration...")
        creator.add_item_for(
            "content/config.json",
            content=ConfigModel(
                secondary_color=self.zim_config.secondary_color
            ).model_dump_json(by_alias=True),
        )

        count_zimui_files = len(list(context.zimui_dist.rglob("*")))
        logger.info(
            f"Adding {count_zimui_files} Vue.JS UI files in {context.zimui_dist}"
        )
        self.stats_items_total += count_zimui_files
        for file in context.zimui_dist.rglob("*"):
            self.stats_items_done += 1
            run_pending()
            if file.is_dir():
                continue
            path = str(Path(file).relative_to(context.zimui_dist))
            logger.debug(f"Adding {path} to ZIM")
            if path == "index.html":  # Change index.html title and add to ZIM
                index_html_path = context.zimui_dist / path
                creator.add_item_for(
                    path=path,
                    content=index_html_path.read_text(encoding="utf-8").replace(
                        "<title>Vite App</title>",
                        f"<title>{self.formatted_config.title}</title>",
                    ),
                    mimetype="text/html",
                    is_front=True,
                )
            else:
                creator.add_item_for(
                    path=path,
                    fpath=file,
                    is_front=False,
                )

        mathjax = (Path(__file__) / "../mathjax").resolve()
        count_mathjax_files = len(list(mathjax.rglob("*")))
        self.stats_items_total += count_mathjax_files
        logger.info(f"Adding {count_mathjax_files} MathJax files in {mathjax}")
        for file in mathjax.rglob("*"):
            self.stats_items_done += 1
            run_pending()
            if not file.is_file():
                continue
            path = str(Path(file).relative_to(mathjax.parent))
            logger.debug(f"Adding {path} to ZIM")
            creator.add_item_for(
                path=path,
                fpath=file,
                is_front=False,
            )

        welcome_image = BytesIO()
        stream_file(
            self.home.welcome_image_url,
            byte_stream=welcome_image,
        )
        creator.add_item_for("content/logo.png", content=welcome_image.getvalue())
        del welcome_image

        self.items_to_download: dict[ZimPath, AssetDetails] = {}
        self._process_css(
            css_location=self.home.screen_css_url,
            target_filename="screen.css",
            creator=creator,
        )
        self._process_css(
            css_location=self.home.print_css_url,
            target_filename="print.css",
            creator=creator,
        )
        self._process_css(
            css_location=self.home.home_url,
            css_content="\n".join(self.home.inline_css),
            target_filename="inline.css",
            creator=creator,
        )

        logger.info("Fetching pages tree")
        context.current_thread_workitem = "pages tree"
        root_page_id = self.content_filter.root_page_id or "home"
        cover_page_id = (
            self.mindtouch_client.get_cover_page_id(root_page_id)
            or root_page_id  # if --root-page-id is not inside a book but a category
        )
        pages_tree = self.mindtouch_client.get_page_tree(cover_page_id)
        selected_pages = self.content_filter.filter(pages_tree)
        logger.info(
            f"{len(selected_pages)} pages (out of {len(pages_tree.pages)}) will be "
            "fetched and pushed to the ZIM"
        )
        creator.add_item_for(
            "content/shared.json",
            content=SharedModel(
                logo_path="content/logo.png",
                root_page_path=selected_pages[0].path,  # root is always first
                library_online_url=context.library_url,
                pages=[
                    PageModel(id=page.id, title=page.title, path=page.path)
                    for page in selected_pages
                ],
            ).model_dump_json(by_alias=True),
        )

        logger.info("Fetching pages content")
        context.current_thread_workitem = "pages content"
        # compute the list of existing pages to properly rewrite links leading
        # in-ZIM / out-of-ZIM
        self.stats_items_total += len(selected_pages)
        existing_html_pages = {
            ArticleUrlRewriter.normalize(HttpUrl(f"{context.library_url}/{page.path}"))
            for page in selected_pages
        }
        private_pages: list[LibraryPage] = []
        for page in selected_pages:
            self.stats_items_done += 1
            run_pending()
            try:
                if page.parent and page.parent in private_pages:
                    logger.debug(f"Ignoring page {page.id} (private page child)")
                    private_pages.append(page)
                    continue
                self._process_page(
                    creator=creator,
                    page=page,
                    existing_zim_paths=existing_html_pages,
                )
            except HTTPError as exc:
                if exc.response.status_code == HTTPStatus.FORBIDDEN:
                    if page == selected_pages[0]:
                        raise PermissionError(
                            "Root page is private, we cannot ZIM it, stopping"
                        ) from None
                    logger.debug(f"Ignoring page {page.id} (private page)")
                    private_pages.append(page)
                    continue
        logger.info(f"{len(private_pages)} private pages have been ignored")
        if len(private_pages) == len(selected_pages):
            # we should never get here since we already check fail early if root
            # page is private, but we are better safe than sorry
            raise OSError("All pages have been ignored, not creating an empty ZIM")
        del private_pages

        logger.info(f"  Retrieving {len(self.items_to_download)} assets...")
        context.current_thread_workitem = "assets"
        self.stats_items_total += len(self.items_to_download)

        res = self.asset_executor(
            delayed(self.asset_processor.process_asset)(
                asset_path, asset_details, creator
            )
            for asset_path, asset_details in self.items_to_download.items()
        )
        for _ in res:
            self.stats_items_done += 1
            run_pending()

        if self.asset_processor.bad_assets_count:
            logger.warning(
                f"{self.asset_processor.bad_assets_count} bad assets have been "
                "ignored"
            )

    def _process_css(
        self,
        creator: Creator,
        target_filename: str,
        css_location: str,
        css_content: str | bytes | None = None,
    ):
        """Process a given CSS stylesheet
        Download content if necessary, rewrite CSS and add CSS to ZIM
        """
        context.current_thread_workitem = f"CSS at {css_location}"
        if not css_location:
            raise ValueError(f"Cannot process empty css_location for {target_filename}")
        if not css_content:
            css_buffer = BytesIO()
            stream_file(css_location, byte_stream=css_buffer)
            css_content = css_buffer.getvalue()
        url_rewriter = CssUrlsRewriter(
            article_url=HttpUrl(css_location),
            article_path=ZimPath(target_filename),
        )
        css_rewriter = CssRewriter(
            url_rewriter=url_rewriter, base_href=None, remove_errors=True
        )
        result = css_rewriter.rewrite(content=css_content)
        # Rebuild the dict since we might have "conflict" of ZimPath (two urls leading
        # to the same ZimPath) and we prefer to use the first URL encountered, where
        # using self.items_to_download.update while override the key value, prefering
        # to use last URL encountered.
        for path, urls in url_rewriter.items_to_download.items():
            if path in self.items_to_download:
                self.items_to_download[path].asset_urls.update(urls)
                self.items_to_download[path].used_by.add(
                    context.current_thread_workitem
                )
            else:
                self.items_to_download[path] = AssetDetails(
                    asset_urls=urls,
                    used_by={context.current_thread_workitem},
                    always_fetch_online=True,
                )
        creator.add_item_for(f"content/{target_filename}", content=result)

    @backoff.on_exception(
        backoff.expo,
        RequestException,
        max_time=16,
        on_backoff=backoff_hdlr,
    )
    def _process_page(
        self, creator: Creator, page: LibraryPage, existing_zim_paths: set[ZimPath]
    ):
        """Process a given library page
        Download content, rewrite HTML and add JSON to ZIM
        """
        context.current_thread_workitem = f"page ID {page.id} ({page.encoded_url})"
        page_content = self.mindtouch_client.get_page_content(page)
        url_rewriter = HtmlUrlsRewriter(
            context.library_url,
            page,
            existing_zim_paths=existing_zim_paths,
        )
        rewriter = HtmlRewriter(
            url_rewriter=url_rewriter,
            pre_head_insert=None,
            post_head_insert=None,
            notify_js_module=None,
        )
        rewriten = None
        # Handle special rewriting of special libretexts.org pages
        if context.library_url.endswith(".libretexts.org"):
            # Let's try to guess back-matter special pages on libretexts.org based on
            # HTML content
            try:
                if (
                    "https://cdn.libretexts.net/github/LibreTextsMain/Leo "
                    "Jayachandran/DynamicIndex/dynamicIndexMaker.js"
                    in page_content.html_body
                ):
                    logger.debug(
                        f"Rewriting {context.current_thread_workitem} as libretexts.org"
                        " index"
                    )
                    rewriten = rewrite_index(
                        rewriter=rewriter,
                        jinja2_template=self.libretexts_index_template,
                        mindtouch_client=self.mindtouch_client,
                        page=page,
                    )
                elif "new LibreTextsGlossarizer()" in page_content.html_body:
                    logger.debug(
                        f"Rewriting {context.current_thread_workitem} as libretexts.org"
                        " glossary"
                    )
                    rewriten = rewrite_glossary(
                        jinja2_template=self.libretexts_glossary_template,
                        original_content=page_content.html_body,
                    )
                elif (
                    "https://cdn.libretexts.net/github/LibreTextsMain/DynamicLicensing/dist/dynamicLicensing.min.js"
                    in page_content.html_body
                ):
                    logger.debug(
                        f"Rewriting {context.current_thread_workitem} as libretexts.org"
                        " detailed licensing"
                    )
                    rewriten = rewrite_detailed_licensing(
                        rewriter=rewriter,
                        jinja2_template=self.libretexts_detailed_licensing_template,
                        mindtouch_client=self.mindtouch_client,
                        page=page,
                    )
                elif (
                    "https://cdn.libretexts.net/github/LibreTextsMain/DynamicTOC/dist/dynamicTOC.min.js"
                    in page_content.html_body
                ):
                    logger.debug(
                        f"Rewriting {context.current_thread_workitem} as libretexts.org"
                        " table of content"
                    )
                    rewriten = rewrite_table_of_content(
                        rewriter=rewriter,
                        jinja2_template=self.libretexts_table_of_content_template,
                        mindtouch_client=self.mindtouch_client,
                        page=page,
                    )
            except Exception as exc:
                # code has been tested to work "in-general", but many edge-case occurs
                # and since these pages are absolutely not essential, we just display a
                # warning and store an empty page
                logger.warning(
                    f"Problem processing special {context.current_thread_workitem}"
                    f", page is probably empty, storing empty page: {exc}"
                )
        if not rewriten:
            # Default rewriting for 'normal' pages
            rewriten = rewriter.rewrite(page_content.html_body).content
        for path, urls in url_rewriter.items_to_download.items():

            if path in self.items_to_download:
                self.items_to_download[path].asset_urls.update(urls)
                self.items_to_download[path].used_by.add(
                    context.current_thread_workitem
                )
            else:
                self.items_to_download[path] = AssetDetails(
                    asset_urls=urls,
                    used_by={context.current_thread_workitem},
                    always_fetch_online=False,
                )
        creator.add_item_for(
            f"content/page_content_{page.id}.json",
            content=PageContentModel(html_body=rewriten).model_dump_json(by_alias=True),
        )
        self._add_indexing_item_to_zim(
            creator=creator,
            title=page.title,
            content=get_text(rewriten),
            fname=f"page_{page.id}",
            zimui_redirect=page.path,
        )

    def _report_progress(self):
        """report progress to stats file"""

        logger.info(f"  Progress {self.stats_items_done} / {self.stats_items_total}")
        if not context.stats_filename:
            return
        progress = {
            "done": self.stats_items_done,
            "total": self.stats_items_total,
        }
        context.stats_filename.write_text(json.dumps(progress, indent=2))

    def _fetch_zim_illustration(self, home: MindtouchHome) -> BytesIO:
        """Fetch ZIM illustration, convert/resize and return it"""
        for icon_url in (
            [context.illustration_url] if context.illustration_url else home.icons_urls
        ):
            try:
                logger.debug(f"Downloading {icon_url} illustration")
                illustration_content = BytesIO()
                stream_file(
                    icon_url,
                    byte_stream=illustration_content,
                )
                illustration_format = format_for(
                    illustration_content, from_suffix=False
                )
                png_illustration = BytesIO()
                if illustration_format == "SVG":
                    logger.debug("Converting SVG illustration to PNG")
                    convert_svg2png(illustration_content, png_illustration, 48, 48)
                elif illustration_format == "PNG":
                    png_illustration = illustration_content
                else:
                    logger.debug(
                        f"Converting {illustration_format} illustration to PNG"
                    )
                    convert_image(illustration_content, png_illustration, fmt="PNG")
                logger.debug("Resizing ZIM illustration")
                resize_image(
                    src=png_illustration,
                    width=48,
                    height=48,
                    method="cover",
                )
                return png_illustration
            except Exception as exc:
                logger.warning(
                    f"Failed to retrieve illustration at {icon_url}", exc_info=exc
                )
        raise NoIllustrationFoundError("Failed to find a suitable illustration")

    def _fetch_favicon_from_illustration(self, illustration: BytesIO) -> BytesIO:
        """Return a converted version of the illustration into favicon"""
        favicon = BytesIO()
        convert_image(illustration, favicon, fmt="ICO")
        logger.debug("Resizing ZIM favicon")
        resize_image(
            src=favicon,
            width=32,
            height=32,
            method="cover",
        )
        return favicon

    def _add_indexing_item_to_zim(
        self,
        creator: Creator,
        title: str,
        content: str,
        fname: str,
        zimui_redirect: str,
    ):
        """Add a 'fake' item to the ZIM, with proper indexing data

        This is mandatory for suggestions and fulltext search to work properly, since
        we do not really have pages to search for.

        This item is a very basic HTML which automatically redirect to proper Vue.JS URL
        """

        redirect_url = f"../index.html#/{zimui_redirect}"
        html_content = (
            f"<html><head><title>{title}</title>"
            f'<meta http-equiv="refresh" content="0;URL=\'{redirect_url}\'" />'
            f"</head><body></body></html>"
        )

        logger.debug(f"Adding {fname} to ZIM index")
        creator.add_item_for(
            title=title,
            path="index/" + fname,
            content=html_content.encode("utf-8"),
            mimetype="text/html",
            index_data=IndexData(title=title, content=content),
        )


class CssUrlsRewriter(ArticleUrlRewriter):
    """A rewriter for CSS processing, storing items to download as URL as processed"""

    def __init__(
        self,
        *,
        article_url: HttpUrl,
        article_path: ZimPath,
    ):
        super().__init__(
            article_url=article_url,
            article_path=article_path,
        )
        self.items_to_download: dict[ZimPath, set[HttpUrl]] = {}

    def __call__(
        self,
        item_url: str,
        base_href: str | None,
        *,
        rewrite_all_url: bool = True,  # noqa: ARG002
    ) -> RewriteResult:
        result = super().__call__(item_url, base_href, rewrite_all_url=True)
        if result.zim_path is None:
            return result
        if result.zim_path in self.items_to_download:
            self.items_to_download[result.zim_path].add(HttpUrl(result.absolute_url))
        else:
            self.items_to_download[result.zim_path] = {HttpUrl(result.absolute_url)}
        return result
