import argparse
import logging
import os
from pathlib import Path

from zimscraperlib.constants import (
    MAXIMUM_DESCRIPTION_METADATA_LENGTH,
    MAXIMUM_LONG_DESCRIPTION_METADATA_LENGTH,
    RECOMMENDED_MAX_TITLE_LENGTH,
)
from zimscraperlib.zim.filesystem import validate_zimfile_creatable

from mindtouch2zim.client import MindtouchClient
from mindtouch2zim.constants import (
    NAME,
    VERSION,
    logger,
)
from mindtouch2zim.processor import ContentFilter, Processor
from mindtouch2zim.zimconfig import ZimConfig


def zim_defaults() -> ZimConfig:
    """Returns the default configuration for ZIM generation."""
    return ZimConfig(
        secondary_color="#FFFFFF",
        file_name="{name}_{period}",
        name="not_used",  # this is always replaced because arg is required",
        creator="not_used",  # this is always replaced because arg is required",
        publisher="openZIM",
        title="not_used",  # this is always replaced because arg is required",
        description="not_used",  # this is always replaced because arg is required",
        long_description=None,
        tags="",
    )


def add_zim_config_flags(parser: argparse.ArgumentParser, defaults: "ZimConfig"):
    """
    Adds flags related to zim configuration

    Flags are added to the given parser with given defaults.
    """

    parser.add_argument(
        "--creator",
        help="Name of content creator.",
        required=True,
    )

    parser.add_argument(
        "--publisher",
        help=f"Publisher name. Default: {defaults.publisher!r}",
        default=defaults.publisher,
    )

    parser.add_argument(
        "--file-name",
        help="Custom file name format for individual ZIMs. "
        f"Default: {defaults.file_name!r}",
        default=defaults.file_name,
    )

    parser.add_argument(
        "--name",
        help="Name of the ZIM.",
        required=True,
    )

    parser.add_argument(
        "--title",
        help=f"Title of the ZIM. Value must not be longer than "
        f"{RECOMMENDED_MAX_TITLE_LENGTH} chars.",
        required=True,
    )

    parser.add_argument(
        "--description",
        help="Description of the ZIM. Value must not be longer than "
        f"{MAXIMUM_DESCRIPTION_METADATA_LENGTH} chars.",
        required=True,
    )

    parser.add_argument(
        "--long-description",
        help="Long description of the ZIM. Value must not be longer than "
        f"{MAXIMUM_LONG_DESCRIPTION_METADATA_LENGTH} chars.",
        default=defaults.long_description,
    )

    # Due to https://github.com/python/cpython/issues/60603 defaulting an array in
    # argparse doesn't work so we expose the underlying semicolon delimited string.
    parser.add_argument(
        "--tags",
        help="A semicolon (;) delimited list of tags to add to the ZIM.",
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
        "--page-title-include",
        help="Includes only pages with title matching the given regular "
        "expression, and their parent pages for proper navigation, up to root (or "
        "subroot if --root-page-id is set). Can be combined with --page-id-include "
        "(pages with matching title or id will be included)",
        metavar="REGEX",
    )

    parser.add_argument(
        "--page-id-include",
        help="CSV of page ids to include. Parent pages will be included as "
        "well for proper navigation, up to root (or subroot if --root-page-id is set). "
        "Can be combined with --page-title-include (pages with matching title or id "
        "will be included)",
    )

    parser.add_argument(
        "--page-title-exclude",
        help="Excludes pages with title matching the given regular expression",
        metavar="REGEX",
    )

    parser.add_argument(
        "--root-page-id",
        help="ID of the root page to include in ZIM. Only this page and its"
        " subpages will be included in the ZIM",
    )


def main(tmpdir: str) -> None:
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
        "--library-url",
        help="URL of the Mindtouch / Nice CXone Expert instance (must NOT contain "
        "trailing slash), e.g. for LibreTexts Geosciences it is "
        "https://geo.libretexts.org",
        required=True,
    )

    parser.add_argument(
        "--overwrite",
        help="Do not fail if ZIM already exists, overwrite it",
        action="store_true",
        default=False,
    )

    # ZIM configuration flags
    add_zim_config_flags(parser, zim_defaults())

    # Document selection flags
    add_content_filter_flags(parser)

    parser.add_argument(
        "--output",
        help="Output folder for ZIMs. Default: /output",
        default=os.getenv("MINDTOUCH_OUTPUT", "/output"),
        dest="output_folder",
    )

    parser.add_argument(
        "--tmp",
        help="Temporary folder for cache, intermediate files, ... Default: tmp",
        default=os.getenv("MINDTOUCH_TMP", tmpdir),
        dest="tmp_folder",
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
        default=os.getenv("MINDTOUCH_ZIMUI_DIST", "../zimui/dist"),
    )

    parser.add_argument(
        "--keep-cache",
        help="Keep cache of website responses",
        action="store_true",
        default=False,
    )

    parser.add_argument(
        "--stats-filename",
        help="Path to store the progress JSON file to.",
        dest="stats_filename",
    )

    parser.add_argument(
        "--illustration-url",
        help="URL to illustration to use for ZIM illustration and favicon",
        dest="illustration_url",
    )

    args = parser.parse_args()

    logger.setLevel(level=logging.DEBUG if args.debug else logging.INFO)

    output_folder = Path(args.output_folder)
    output_folder.mkdir(exist_ok=True)
    validate_zimfile_creatable(output_folder, "test.txt")

    tmp_folder = Path(args.tmp_folder)
    tmp_folder.mkdir(exist_ok=True)
    validate_zimfile_creatable(tmp_folder, "test.txt")

    library_url = str(args.library_url).rstrip("/")

    try:
        zim_config = ZimConfig.of(args)
        doc_filter = ContentFilter.of(args)

        cache_folder = tmp_folder / "cache"
        cache_folder.mkdir(exist_ok=True)

        mindtouch_client = MindtouchClient(
            library_url=library_url,
            cache_folder=cache_folder,
        )

        Processor(
            mindtouch_client=mindtouch_client,
            zim_config=zim_config,
            output_folder=Path(args.output_folder),
            zimui_dist=Path(args.zimui_dist),
            content_filter=doc_filter,
            stats_file=Path(args.stats_filename) if args.stats_filename else None,
            overwrite_existing_zim=args.overwrite,
            illustration_url=args.illustration_url,
        ).run()
    except SystemExit:
        logger.error("Generation failed, exiting")
        raise
    except Exception as exc:
        logger.exception(exc)
        logger.error(f"Generation failed with the following error: {exc}")
        raise SystemExit(1) from exc
