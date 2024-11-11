import argparse
import datetime
import json
import re
from http import HTTPStatus
from io import BytesIO
from pathlib import Path

import backoff
from joblib import Parallel, delayed
from pydantic import BaseModel
from requests import RequestException
from requests.exceptions import HTTPError
from schedule import every, run_pending
from zimscraperlib.download import stream_file
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
from zimscraperlib.zim.filesystem import validate_file_creatable
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
    LANGUAGE_ISO_639_3,
    NAME,
    VERSION,
    logger,
    web_session,
)
from mindtouch2zim.errors import NoIllustrationFoundError
from mindtouch2zim.html import get_text
from mindtouch2zim.html_rewriting import HtmlUrlsRewriter
from mindtouch2zim.ui import (
    ConfigModel,
    PageContentModel,
    PageModel,
    SharedModel,
)
from mindtouch2zim.utils import backoff_hdlr
from mindtouch2zim.zimconfig import ZimConfig


class ContentFilter(BaseModel):
    """Supports filtering documents by user provided attributes."""

    # If specified, only pages with title matching the regex are included.
    page_title_include: str | None
    # If specified, only page with matching ids are included.
    page_id_include: str | None
    # If specified, page with title matching the regex are excluded.
    page_title_exclude: str | None
    # If specified, only this page and its subpages will be included.
    root_page_id: str | None

    @staticmethod
    def of(namespace: argparse.Namespace) -> "ContentFilter":
        """Parses a namespace to create a new DocFilter."""
        return ContentFilter.model_validate(namespace, from_attributes=True)

    def filter(self, page_tree: LibraryTree) -> list[LibraryPage]:
        """Filters pages based on the user's choices."""

        if self.root_page_id:
            page_tree = page_tree.sub_tree(self.root_page_id)

        title_include_re = (
            re.compile(self.page_title_include, re.IGNORECASE)
            if self.page_title_include
            else None
        )
        title_exclude_re = (
            re.compile(self.page_title_exclude, re.IGNORECASE)
            if self.page_title_exclude
            else None
        )
        id_include = (
            [page_id.strip() for page_id in self.page_id_include.split(",")]
            if self.page_id_include
            else None
        )

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
            if is_selected(title_include_re, title_exclude_re, id_include, page)
        }

        # Then transform set of ids into list of pages
        return [page for page in page_tree.pages.values() if page.id in selected_ids]


class Processor:
    """Generates ZIMs based on the user's configuration."""

    def __init__(
        self,
        mindtouch_client: MindtouchClient,
        zim_config: ZimConfig,
        content_filter: ContentFilter,
        output_folder: Path,
        zimui_dist: Path,
        stats_file: Path | None,
        illustration_url: str | None,
        s3_url_with_credentials: str | None,
        assets_workers: int,
        *,
        overwrite_existing_zim: bool,
    ) -> None:
        """Initializes Processor.

        Parameters:
            libretexts_client: Client that connects with Libretexts website
            zim_config: Configuration for ZIM metadata.
            content_filter: User supplied filter selecting with content to convert.
            output_folder: Directory to write ZIMs into.
            zimui_dist: Build directory where Vite placed compiled Vue.JS frontend.
            stats_file: Path where JSON task progress while be saved.
            overwrite_existing_zim: Do not fail if ZIM already exists, overwrite it.
        """
        self.mindtouch_client = mindtouch_client
        self.zim_config = zim_config
        self.content_filter = content_filter
        self.output_folder = output_folder
        self.zimui_dist = zimui_dist
        self.stats_file = stats_file
        self.overwrite_existing_zim = overwrite_existing_zim
        self.illustration_url = illustration_url
        self.asset_processor = AssetProcessor(
            s3_url_with_credentials=s3_url_with_credentials
        )
        self.asset_executor = Parallel(
            n_jobs=assets_workers, return_as="generator_unordered", backend="threading"
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
        logger.info("Generating ZIM")

        # create first progress report and and a timer to update every 10 seconds
        self._report_progress()
        every(10).seconds.do(  # pyright: ignore[reportUnknownMemberType]
            self._report_progress
        )

        formatted_config = self.zim_config.format(
            {
                "name": self.zim_config.name,
                "period": datetime.date.today().strftime("%Y-%m"),
            }
        )
        zim_file_name = f"{formatted_config.file_name}.zim"
        zim_path = self.output_folder / zim_file_name

        if zim_path.exists():
            if self.overwrite_existing_zim:
                zim_path.unlink()
            else:
                logger.error(f"  {zim_path} already exists, aborting.")
                raise SystemExit(2)

        validate_file_creatable(self.output_folder, zim_file_name)

        logger.info(f"  Writing to: {zim_path}")

        creator = Creator(zim_path, "index.html")

        logger.info("  Fetching and storing home page...")
        home = self.mindtouch_client.get_home()

        logger.info("  Fetching ZIM illustration...")
        zim_illustration = self._fetch_zim_illustration(home)

        logger.debug("Configuring metadata")
        creator.config_metadata(
            Name=formatted_config.name,
            Title=formatted_config.title,
            Publisher=formatted_config.publisher,
            Date=datetime.datetime.now(tz=datetime.UTC).date(),
            Creator=formatted_config.creator,
            Description=formatted_config.description,
            LongDescription=formatted_config.long_description,
            # As of 2024-09-4 all documentation is in English.
            Language=LANGUAGE_ISO_639_3,
            Tags=formatted_config.tags,
            Scraper=f"{NAME} v{VERSION}",
            Illustration_48x48_at_1=zim_illustration.getvalue(),
        )

        # Start creator early to detect problems early.
        with creator as creator:

            creator.add_item_for(
                "favicon.ico",
                content=self._fetch_favicon_from_illustration(
                    zim_illustration
                ).getvalue(),
            )
            del zim_illustration

            logger.info("  Storing configuration...")
            creator.add_item_for(
                "content/config.json",
                content=ConfigModel(
                    secondary_color=self.zim_config.secondary_color
                ).model_dump_json(by_alias=True),
            )

            count_zimui_files = len(list(self.zimui_dist.rglob("*")))
            logger.info(
                f"Adding {count_zimui_files} Vue.JS UI files in {self.zimui_dist}"
            )
            self.stats_items_total += count_zimui_files
            for file in self.zimui_dist.rglob("*"):
                self.stats_items_done += 1
                run_pending()
                if file.is_dir():
                    continue
                path = str(Path(file).relative_to(self.zimui_dist))
                logger.debug(f"Adding {path} to ZIM")
                if path == "index.html":  # Change index.html title and add to ZIM
                    index_html_path = self.zimui_dist / path
                    creator.add_item_for(
                        path=path,
                        content=index_html_path.read_text(encoding="utf-8").replace(
                            "<title>Vite App</title>",
                            f"<title>{formatted_config.title}</title>",
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
                home.welcome_image_url, byte_stream=welcome_image, session=web_session
            )
            creator.add_item_for("content/logo.png", content=welcome_image.getvalue())
            del welcome_image

            self.items_to_download: dict[ZimPath, AssetDetails] = {}
            self._process_css(
                css_location=home.screen_css_url,
                target_filename="screen.css",
                creator=creator,
            )
            self._process_css(
                css_location=home.print_css_url,
                target_filename="print.css",
                creator=creator,
            )
            self._process_css(
                css_location=home.home_url,
                css_content="\n".join(home.inline_css),
                target_filename="inline.css",
                creator=creator,
            )

            logger.info("Fetching pages tree")
            pages_tree = self.mindtouch_client.get_page_tree()
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
                    pages=[
                        PageModel(id=page.id, title=page.title, path=page.path)
                        for page in selected_pages
                    ],
                ).model_dump_json(by_alias=True),
            )

            logger.info("Fetching pages content")
            # compute the list of existing pages to properly rewrite links leading
            # in-ZIM / out-of-ZIM
            self.stats_items_total += len(selected_pages)
            existing_html_pages = {
                ArticleUrlRewriter.normalize(
                    HttpUrl(f"{self.mindtouch_client.library_url}/{page.path}")
                )
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
                            raise Exception(
                                "Root page is private, we cannot ZIM it, stopping"
                            ) from None
                        logger.debug(f"Ignoring page {page.id} (private page)")
                        private_pages.append(page)
                        continue
            logger.info(f"{len(private_pages)} private pages have been ignored")
            if len(private_pages) == len(selected_pages):
                # we should never get here since we already check fail early if root
                # page is private, but we are better safe than sorry
                raise Exception(
                    "All pages have been ignored, not creating an empty ZIM"
                )
            del private_pages

            logger.info(f"  Retrieving {len(self.items_to_download)} assets...")
            self.stats_items_total += len(self.items_to_download)

            try:
                res = self.asset_executor(
                    delayed(self.asset_processor.process_asset)(
                        asset_path, asset_details, creator
                    )
                    for asset_path, asset_details in self.items_to_download.items()
                )
                for _ in res:
                    self.stats_items_done += 1
                    run_pending()
            except Exception as exc:
                logger.error(
                    "Exception occured during assets processing, aborting ZIM creation",
                    exc_info=exc,
                )
                creator.can_finish = False

        logger.info(f"ZIM creation completed, ZIM is at {zim_path}")

        # same reason than self.stats_items_done = 1 at the beginning, we need to add
        # a final item to complete the progress
        self.stats_items_done += 1
        self._report_progress()

        return zim_path

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
        if not css_location:
            raise ValueError(f"Cannot process empty css_location for {target_filename}")
        if not css_content:
            css_buffer = BytesIO()
            stream_file(css_location, byte_stream=css_buffer, session=web_session)
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
                self.items_to_download[path].urls.update(urls)
            else:
                self.items_to_download[path] = AssetDetails(
                    urls=urls, always_fetch_online=True
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
        logger.debug(f"  Fetching {page.id}")
        page_content = self.mindtouch_client.get_page_content(page)
        url_rewriter = HtmlUrlsRewriter(
            self.mindtouch_client.library_url,
            page,
            existing_zim_paths=existing_zim_paths,
        )
        rewriter = HtmlRewriter(
            url_rewriter=url_rewriter,
            pre_head_insert=None,
            post_head_insert=None,
            notify_js_module=None,
        )
        rewriten = rewriter.rewrite(page_content.html_body)
        for path, urls in url_rewriter.items_to_download.items():
            if path in self.items_to_download:
                self.items_to_download[path].urls.update(urls)
            else:
                self.items_to_download[path] = AssetDetails(
                    urls=urls, always_fetch_online=False
                )
        creator.add_item_for(
            f"content/page_content_{page.id}.json",
            content=PageContentModel(html_body=rewriten.content).model_dump_json(
                by_alias=True
            ),
        )
        self._add_indexing_item_to_zim(
            creator=creator,
            title=page.title,
            content=get_text(rewriten.content),
            fname=f"page_{page.id}",
            zimui_redirect=page.path,
        )

    def _report_progress(self):
        """report progress to stats file"""

        logger.info(f"  Progress {self.stats_items_done} / {self.stats_items_total}")
        if not self.stats_file:
            return
        progress = {
            "done": self.stats_items_done,
            "total": self.stats_items_total,
        }
        self.stats_file.write_text(json.dumps(progress, indent=2))

    def _fetch_zim_illustration(self, home: MindtouchHome) -> BytesIO:
        """Fetch ZIM illustration, convert/resize and return it"""
        for icon_url in (
            [self.illustration_url] if self.illustration_url else home.icons_urls
        ):
            try:
                logger.debug(f"Downloading {icon_url} illustration")
                illustration_content = BytesIO()
                stream_file(
                    icon_url, byte_stream=illustration_content, session=web_session
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
