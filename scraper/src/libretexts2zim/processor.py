import argparse
import datetime
from io import BytesIO
from pathlib import Path

from pydantic import BaseModel
from zimscraperlib.download import (
    stream_file,  # pyright: ignore[reportUnknownVariableType]
)
from zimscraperlib.image import resize_image
from zimscraperlib.zim import Creator
from zimscraperlib.zim.indexing import IndexData

from libretexts2zim.client import LibreTextsClient, LibreTextsMetadata
from libretexts2zim.constants import LANGUAGE_ISO_639_3, NAME, ROOT_DIR, VERSION, logger
from libretexts2zim.ui import ConfigModel, HomeModel, SharedModel
from libretexts2zim.zimconfig import ZimConfig


class InvalidFormatError(Exception):
    """Raised when a user supplied template has an invalid parameter."""

    pass


class MissingDocumentError(Exception):
    """Raised when the user specified a slug that doesn't exist."""

    pass


class ContentFilter(BaseModel):
    """Supports filtering documents by user provided attributes."""

    # If specified, only shelves matching the regex are included.
    shelves_include: str | None
    # If specified, shelves matching the regex are excluded.
    shelves_exclude: str | None

    @staticmethod
    def of(namespace: argparse.Namespace) -> "ContentFilter":
        """Parses a namespace to create a new DocFilter."""
        return ContentFilter.model_validate(namespace, from_attributes=True)

    # TODO: implement filtering of shelves based on configured regex
    # def filter(self, shelves: list[LibretextsShelve]) -> list[LibretextsShelve]:
    #     """Filters docs based on the user's choices."""
    #     selected: list[LibretextsShelve] = []
    #     for shelve in shelves:
    #       ....
    #     return selected


def add_item_for(
    creator: Creator,
    path: str,
    title: str | None = None,
    *,
    fpath: Path | None = None,
    content: bytes | str | None = None,
    mimetype: str | None = None,
    is_front: bool | None = None,
    should_compress: bool | None = None,
    delete_fpath: bool | None = False,
    duplicate_ok: bool | None = None,
    index_data: IndexData | None = None,
    auto_index: bool = True,
):
    """
    Boilerplate to avoid repeating pyright ignore

    To be removed, once upstream issue is solved, see
    https://github.com/openzim/libretexts/issues/26
    """
    creator.add_item_for(  # pyright: ignore[reportUnknownMemberType]
        path=path,
        title=title,
        fpath=fpath,
        content=content,
        mimetype=mimetype,
        is_front=is_front,
        should_compress=should_compress,
        delete_fpath=delete_fpath,
        duplicate_ok=duplicate_ok,
        index_data=index_data,
        auto_index=auto_index,
    )


class Processor:
    """Generates ZIMs based on the user's configuration."""

    def __init__(
        self,
        libretexts_client: LibreTextsClient,
        zim_config: ZimConfig,
        content_filter: ContentFilter,
        output_folder: Path,
        zimui_dist: Path,
    ) -> None:
        """Initializes Processor.

        Parameters:
            libretexts_client: Client that connects with Libretexts website
            zim_config: Configuration for ZIM metadata.
            content_filter: User supplied filter selecting with content to convert.
            output_folder: Directory to write ZIMs into.
        """
        self.libretexts_client = libretexts_client
        self.zim_config = zim_config
        self.doc_filter = content_filter
        self.output_folder = output_folder
        self.zimui_dist = zimui_dist

        self.output_folder.mkdir(exist_ok=True)

        self.zim_illustration_path = self.libretexts_newsite_path(
            "header_logo_mini.png"
        )

    @staticmethod
    def libretexts_newsite_path(name: str) -> Path:
        """Returns the path to name in the third_party/libretexts_newsite folder.

        Raises ValueError if the resource doesn't exist.
        """
        path = ROOT_DIR.joinpath("third_party", "libretexts_newsite", name)
        if not path.exists():
            raise ValueError(f"File not found at {path}")
        return path

    def run(self) -> Path:
        """Generates a zim for a single document.

        Returns the path to the gernated ZIM.
        """
        logger.info("Generating ZIM")

        metadata = LibreTextsMetadata(
            name=self.zim_config.library_name, slug=self.libretexts_client.library_slug
        )
        formatted_config = self.zim_config.format(metadata.placeholders())
        zim_path = Path(self.output_folder, f"{formatted_config.file_name_format}.zim")

        if zim_path.exists():
            logger.error(f"  {zim_path} already exists, aborting.")
            raise SystemExit(2)

        logger.info(f"  Writing to: {zim_path}")

        creator = Creator(zim_path, "index.html")

        logger.debug("Resizing ZIM illustration")
        zim_illustration = BytesIO()
        resize_image(
            src=self.zim_illustration_path,
            dst=zim_illustration,
            width=48,
            height=48,
            method="cover",
        )

        logger.debug("Configuring metadata")
        creator.config_metadata(
            Name=formatted_config.name_format,
            Title=formatted_config.title_format,
            Publisher=formatted_config.publisher,
            Date=datetime.datetime.now(tz=datetime.UTC).date(),
            Creator=formatted_config.creator,
            Description=formatted_config.description_format,
            LongDescription=formatted_config.long_description_format,
            # As of 2024-09-4 all documentation is in English.
            Language=LANGUAGE_ISO_639_3,
            Tags=formatted_config.tags,
            Scraper=f"{NAME} v{VERSION}",
            Illustration_48x48_at_1=zim_illustration.getvalue(),
        )
        del zim_illustration

        # Start creator early to detect problems early.
        with creator as creator:

            logger.info("  Storing configuration...")
            add_item_for(
                creator,
                "content/config.json",
                content=ConfigModel(
                    secondary_color=self.zim_config.secondary_color
                ).model_dump_json(by_alias=True),
            )

            logger.info("  Storing the ZIM UI")

            logger.info("  Fetching and storing home page...")
            home = self.libretexts_client.get_home()
            welcome_image = BytesIO()
            stream_file(home.welcome_image_url, byte_stream=welcome_image)
            add_item_for(creator, "content/logo.png", content=welcome_image.getvalue())
            del welcome_image
            add_item_for(
                creator,
                "content/shared.json",
                content=SharedModel(logo_path="content/logo.png").model_dump_json(
                    by_alias=True
                ),
            )
            add_item_for(
                creator,
                "content/home.json",
                content=HomeModel(
                    welcome_text_paragraphs=home.welcome_text_paragraphs
                ).model_dump_json(by_alias=True),
            )

            logger.info(f"Adding files in {self.zimui_dist}")
            for file in self.zimui_dist.rglob("*"):
                if file.is_dir():
                    continue
                path = str(Path(file).relative_to(self.zimui_dist))
                logger.debug(f"Adding {path} to ZIM")
                if path == "index.html":  # Change index.html title and add to ZIM
                    index_html_path = self.zimui_dist / path
                    add_item_for(
                        creator=creator,
                        path=path,
                        content=index_html_path.read_text(encoding="utf-8").replace(
                            "<title>Vite App</title>", formatted_config.title_format
                        ),
                        mimetype="text/html",
                        is_front=True,
                    )
                else:
                    add_item_for(
                        creator=creator,
                        path=path,
                        fpath=file,
                        is_front=False,
                    )

        return zim_path
