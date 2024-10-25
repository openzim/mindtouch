import logging
import pathlib

from zimscraperlib.logging import (
    getLogger,
)

from mindtouch2zim.__about__ import __version__

NAME = "mindtouch2zim"
VERSION = __version__
ROOT_DIR = pathlib.Path(__file__).parent

# As of 2024-09-24, all libraries appears to be in English.
LANGUAGE_ISO_639_3 = "eng"

HTTP_TIMEOUT_NORMAL_SECONDS = 15
HTTP_TIMEOUT_LONG_SECONDS = 30

logger = getLogger(NAME, level=logging.DEBUG)
