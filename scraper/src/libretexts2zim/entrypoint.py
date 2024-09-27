import argparse
import logging
import os
from pathlib import Path

from zimscraperlib.constants import (
    MAXIMUM_DESCRIPTION_METADATA_LENGTH,
    MAXIMUM_LONG_DESCRIPTION_METADATA_LENGTH,
    RECOMMENDED_MAX_TITLE_LENGTH,
)

from libretexts2zim.client import LibreTextsClient
from libretexts2zim.constants import (
    NAME,
    VERSION,
    logger,
)
from libretexts2zim.processor import ContentFilter, Processor
from libretexts2zim.zimconfig import ZimConfig


def zim_defaults() -> ZimConfig:
    """Returns the default configuration for ZIM generation."""
    return ZimConfig(
        secondary_color="#FFFFFF",
        library_name="not_used",  # this is always replaced because arg is required
        file_name_format="libretexts_en_{clean_slug}_{period}",
        name_format="libretexts_en_{clean_slug}",
        creator="LibreTexts",
        publisher="openZIM",
        title_format="{name} courses",
        description_format="{name} courses by LibreTexts",
        long_description_format=None,
        tags="libretexts;{clean_slug}",
    )


def add_zim_config_flags(parser: argparse.ArgumentParser, defaults: "ZimConfig"):
    """
    Adds flags related to zim configuration

    Flags are added to the given parser with given defaults.
    """

    parser.add_argument(
        "--library-name",
        help="Display name for the library, e.g. Geosciences",
        required=True,
    )

    parser.add_argument(
        "--creator",
        help=f"Name of content creator. Default: {defaults.creator!r}",
        default=defaults.creator,
    )

    parser.add_argument(
        "--publisher",
        help=f"Custom publisher name. Default: {defaults.publisher!r}",
        default=defaults.publisher,
    )

    parser.add_argument(
        "--file-name-format",
        help="Custom file name format for individual ZIMs. "
        f"Default: {defaults.file_name_format!r}",
        default=defaults.file_name_format,
        metavar="FORMAT",
    )

    parser.add_argument(
        "--name-format",
        help="Custom name format for individual ZIMs. "
        f"Default: {defaults.name_format!r}",
        default=defaults.name_format,
        metavar="FORMAT",
    )

    parser.add_argument(
        "--title-format",
        help=f"Custom title format for individual ZIMs. Final value must not be "
        f"longer than {RECOMMENDED_MAX_TITLE_LENGTH} chars. "
        f"Default: {defaults.title_format!r}",
        default=defaults.title_format,
        metavar="FORMAT",
    )

    parser.add_argument(
        "--description-format",
        help="Custom description format for individual ZIMs. Final value must not "
        f"be longer than {MAXIMUM_DESCRIPTION_METADATA_LENGTH} chars. "
        f"Default: {defaults.title_format!r}",
        default=defaults.description_format,
        metavar="FORMAT",
    )

    parser.add_argument(
        "--long-description-format",
        help="Custom long description format for your ZIM. Final value must not be "
        f"longer than {MAXIMUM_LONG_DESCRIPTION_METADATA_LENGTH} chars. "
        f"Default: {defaults.long_description_format!r}",
        default=defaults.long_description_format,
        metavar="FORMAT",
    )

    # Due to https://github.com/python/cpython/issues/60603 defaulting an array in
    # argparse doesn't work so we expose the underlying semicolon delimited string.
    parser.add_argument(
        "--tags",
        help="A semicolon (;) delimited list of tags to add to the ZIM."
        "Formatting is supported. "
        f"Default: {defaults.tags!r}",
        default=defaults.tags,
    )

    parser.add_argument(
        "--secondary-color",
        help="Secondary (background) color of ZIM UI. Default: "
        f"{defaults.secondary_color!r}",
        default=defaults.secondary_color,
    )


def add_content_filter_flags(parser: argparse.ArgumentParser):
    """Adds flags related to content filtering to the given parser."""

    parser.add_argument(
        "--shelves-include",
        help="Includes only shelves matching the given regular expression.",
        metavar="REGEX",
    )

    parser.add_argument(
        "--shelves-exclude",
        help="Excludes shelves matching the given regular expression.",
        metavar="REGEX",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        prog=NAME,
    )

    parser.add_argument(
        "--version",
        help="Display scraper version and exit",
        action="version",
        version=VERSION,
    )

    # Client configuration flags
    parser.add_argument(
        "--library-slug",
        help="URL prefix for the library, e.g. for Geosciences which is at "
        "https://geo.libretexts.org/, the slug is `geo`",
        required=True,
    )

    # ZIM configuration flags
    add_zim_config_flags(parser, zim_defaults())

    # Document selection flags
    add_content_filter_flags(parser)

    parser.add_argument(
        "--output",
        help="Output folder for ZIMs. Default: /output",
        default="/output",
        dest="output_folder",
    )

    parser.add_argument(
        "--debug", help="Enable verbose output", action="store_true", default=False
    )

    parser.add_argument(
        "--zimui-dist",
        type=str,
        help=(
            "Dev option to customize directory containing Vite build output from the "
            "ZIM UI Vue.JS application"
        ),
        default=os.getenv("LIBRETEXTS_ZIMUI_DIST", "../zimui/dist"),
    )

    args = parser.parse_args()

    logger.setLevel(level=logging.DEBUG if args.debug else logging.INFO)

    try:
        zim_config = ZimConfig.of(args)
        doc_filter = ContentFilter.of(args)
        libretexts_client = LibreTextsClient(
            library_slug=args.library_slug,
        )

        Processor(
            libretexts_client=libretexts_client,
            zim_config=zim_config,
            output_folder=Path(args.output_folder),
            zimui_dist=Path(args.zimui_dist),
            content_filter=doc_filter,
        ).run()
    except SystemExit:
        logger.error("Generation failed, exiting")
        raise
    except Exception as exc:
        logger.exception(exc)
        logger.error(f"Generation failed with the following error: {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
