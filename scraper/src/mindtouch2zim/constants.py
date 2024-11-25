import logging
import pathlib

from zimscraperlib.download import get_session
from zimscraperlib.logging import DEFAULT_FORMAT_WITH_THREADS, getLogger

from mindtouch2zim.__about__ import __version__

NAME = "mindtouch2zim"
VERSION = __version__
ROOT_DIR = pathlib.Path(__file__).parent

# As of 2024-09-24, all libraries appears to be in English.
LANGUAGE_ISO_639_3 = "eng"

HTTP_TIMEOUT_NORMAL_SECONDS = 15
HTTP_TIMEOUT_LONG_SECONDS = 30

# Loading the CSS leads to many bad assets at these URLs, we just ignore them
KNOWN_BAD_ASSETS_REGEX = r"https?:\/\/a\.mtstatic\.com/@(cache|style)"

logger = getLogger(NAME, level=logging.DEBUG, log_format=DEFAULT_FORMAT_WITH_THREADS)

web_session = get_session()
