import argparse
import os
import re
import threading
from pathlib import Path

from zimscraperlib.constants import (
    MAXIMUM_DESCRIPTION_METADATA_LENGTH,
    MAXIMUM_LONG_DESCRIPTION_METADATA_LENGTH,
    RECOMMENDED_MAX_TITLE_LENGTH,
)
from zimscraperlib.download import get_session

from mindtouch2zim.constants import (
    NAME,
    STANDARD_KNOWN_BAD_ASSETS_REGEX,
    VERSION,
)
from mindtouch2zim.context import Context


def prepare_context(raw_args: list[str], tmpdir: str) -> None:
    """Initialize scraper context from command line arguments"""

    parser = argparse.ArgumentParser(
        prog=NAME,
    )

    parser.register("type", "Path", lambda x: Path(x))

    parser.add_argument(
        "--creator",
        help="Name of content creator.",
        required=True,
    )

    parser.add_argument(
        "--publisher",
        help=f"Publisher name. Default: {Context.publisher!r}",
    )

    parser.add_argument(
        "--file-name",
        help="Custom file name format for individual ZIMs. "
        f"Default: {Context.file_name!r}",
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
    )

    # Due to https://github.com/python/cpython/issues/60603 defaulting an array in
    # argparse doesn't work so we expose the underlying semicolon delimited string.
    parser.add_argument(
        "--tags",
        help="A semicolon (;) delimited list of tags to add to the ZIM.",
        type=lambda x: [tag.strip() for tag in x.split(";")],
    )

    parser.add_argument(
        "--secondary-color",
        help="Secondary (background) color of ZIM UI. Default: "
        f"{Context.secondary_color!r}",
    )

    parser.add_argument(
        "--page-title-include",
        help="Includes only pages with title matching the given regular "
        "expression, and their parent pages for proper navigation, up to root (or "
        "subroot if --root-page-id is set). Can be combined with --page-id-include "
        "(pages with matching title or id will be included)",
        type=lambda x: re.compile(x, re.IGNORECASE),
    )

    parser.add_argument(
        "--page-id-include",
        help="CSV of page ids to include. Parent pages will be included as "
        "well for proper navigation, up to root (or subroot if --root-page-id is set). "
        "Can be combined with --page-title-include (pages with matching title or id "
        "will be included)",
        type=lambda x: [page_id.strip() for page_id in x.split(",")],
    )

    parser.add_argument(
        "--page-title-exclude",
        help="Excludes pages with title matching the given regular expression",
        type=lambda x: re.compile(x, re.IGNORECASE),
    )

    parser.add_argument(
        "--root-page-id",
        help="ID of the root page to include in ZIM. Only this page and its"
        " subpages will be included in the ZIM",
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
        dest="overwrite_existing_zim",
    )

    parser.add_argument(
        "--output",
        help="Output folder for ZIMs. Default: /output",
        type="Path",
        dest="output_folder",
    )

    parser.add_argument(
        "--tmp",
        help="Temporary folder for cache, intermediate files, ...",
        type="Path",
        dest="tmp_folder",
    )

    parser.add_argument("--debug", help="Enable verbose output", action="store_true")

    parser.add_argument(
        "--zimui-dist",
        type="Path",
        help=(
            "Dev option to customize directory containing Vite build output from the "
            "ZIM UI Vue.JS application"
        ),
    )

    parser.add_argument(
        "--stats-filename",
        type="Path",
        help="Path to store the progress JSON file to.",
    )

    parser.add_argument(
        "--illustration-url",
        help="URL to illustration to use for ZIM illustration and favicon",
    )

    parser.add_argument(
        "--optimization-cache",
        help="URL with credentials to S3 for using as optimization cache",
        dest="s3_url_with_credentials",
    )

    parser.add_argument(
        "--assets-workers",
        type=int,
        help="Number of parallel workers for asset processing",
    )

    parser.add_argument(
        "--bad-assets-regex",
        help="Regular expression of asset URLs known to not be available. "
        "Case insensitive.",
        type=lambda x: re.compile(
            f"{x}|{STANDARD_KNOWN_BAD_ASSETS_REGEX}", re.IGNORECASE
        ),
    )

    parser.add_argument(
        "--bad-assets-threshold",
        type=int,
        help="[dev] Number of assets allowed to fail to download before failing the"
        " scraper. Assets already excluded with --bad-assets-regex are not counted for"
        " this threshold.",
    )

    parser.add_argument(
        "--contact-info",
        help="Contact information to pass in User-Agent headers",
    )

    args = parser.parse_args(raw_args)

    # Ignore unset values so they do not override the default specified in Context
    args_dict = {key: value for key, value in args._get_kwargs() if value}

    # initialize some context properties that are "dynamic" (i.e. not constant
    # values like an int, a string, ...)
    if not args_dict.get("tmp_folder", None):
        if tmp_from_env := os.getenv("MINDTOUCH_TMP"):
            args_dict["tmp_folder"] = Path(tmp_from_env)
        else:
            args_dict["tmp_folder"] = Path(tmpdir)

    args_dict["cache_folder"] = args_dict["tmp_folder"] / "cache"
    args_dict["web_session"] = get_session()
    args_dict["_current_thread_workitem"] = threading.local()

    Context.setup(**args_dict)
