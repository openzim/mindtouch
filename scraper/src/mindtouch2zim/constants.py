import logging
import pathlib

from zimscraperlib.logging import DEFAULT_FORMAT_WITH_THREADS, getLogger

from mindtouch2zim.__about__ import __version__

NAME = "mindtouch2zim"
VERSION = __version__
ROOT_DIR = pathlib.Path(__file__).parent

# Loading the CSS leads to many bad assets at a.mtstatic.com/@cache or
# a.mtstatic.com/@style we just ignore them
# Multiple images are badly loaded from localhost (=> no need to retry these)
STANDARD_KNOWN_BAD_ASSETS_REGEX = (
    r"https?:\/\/(a\.mtstatic\.com\/@(cache|style)|localhost(:|\/))"
)

# logger to use everywhere (not part of Context class because we need it early, before
# Context has been initialized)
logger: logging.Logger = getLogger(
    NAME, level=logging.DEBUG, log_format=DEFAULT_FORMAT_WITH_THREADS
)
