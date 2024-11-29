import logging
import pathlib

from zimscraperlib.logging import DEFAULT_FORMAT_WITH_THREADS, getLogger

from mindtouch2zim.__about__ import __version__

NAME = "mindtouch2zim"
VERSION = __version__
ROOT_DIR = pathlib.Path(__file__).parent

# Loading the CSS leads to many bad assets at these URLs, we just ignore them
STANDARD_KNOWN_BAD_ASSETS_REGEX = r"https?:\/\/a\.mtstatic\.com/@(cache|style)"

# logger to use everywhere (not part of Context class because we need it early, before
# Context has been initialized)
logger: logging.Logger = getLogger(
    NAME, level=logging.DEBUG, log_format=DEFAULT_FORMAT_WITH_THREADS
)
