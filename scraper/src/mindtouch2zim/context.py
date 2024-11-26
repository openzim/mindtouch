import argparse
import logging
import os
import re
import threading
from pathlib import Path

import requests
from zimscraperlib.__about__ import __version__ as SCRAPERLIB_VERSION  # noqa: N812
from zimscraperlib.constants import NAME as SCRAPERLIB_NAME
from zimscraperlib.download import get_session

from mindtouch2zim.constants import (
    NAME,
    STANDARD_KNOWN_BAD_ASSETS_REGEX,
    VERSION,
    logger,
)


class Context:
    """Class holding every contextual / configuration bits which can be moved

    Used to easily pass information around in the scraper. One singleton instance is
    always available.
    """

    # info passed in User-Agent header of web requests
    contact_info: str = "https://www.kiwix.org"

    # web session to use everywhere
    web_session: requests.Session = get_session()

    # temporary folder to store temporary assets (e.g. cached API response)
    tmp_folder: Path

    # temporary folder to store cached API response
    cache_folder: Path

    # folder where the ZIM will be built
    output_folder: Path = Path(os.getenv("MINDTOUCH_OUTPUT", "/output"))

    # folder where Vue.JS UI has been built
    zimui_dist: Path = Path(os.getenv("MINDTOUCH_ZIMUI_DIST", "../zimui/dist"))

    # Path to store the progress JSON file to
    stats_filename: Path | None = None

    # URL to illustration to use for ZIM illustration and favicon
    illustration_url: str | None = None

    # Do not fail if ZIM already exists, overwrite it
    overwrite_existing_zim: bool = False

    # number of assets processed in parallel
    assets_workers: int = 10

    # known bad assets
    bad_assets_regex: re.Pattern | None = re.compile(STANDARD_KNOWN_BAD_ASSETS_REGEX)

    # maximum amount of bad assets
    bad_assets_threshold: int = 10

    # current processing info to use for debug message / exception
    _processing_step: threading.local = threading.local()

    # As of 2024-09-24, all libraries appears to be in English.
    language_iso_639_3: str = "eng"

    # normal and long timeouts to use in HTTP calls
    http_timeout_normal_seconds: int = 15
    http_timeout_long_seconds: int = 30

    # S3 cache URL
    s3_url_with_credentials: str | None = None

    # URL to Mindtouch instance
    library_url: str

    def __init__(self) -> None:
        if path := os.getenv("MINDTOUCH_TMP"):
            self.tmp_folder = Path(path)

    @property
    def processing_step(self) -> str:
        return getattr(self._processing_step, "value", "startup")

    @processing_step.setter
    def processing_step(self, value: str):
        self._processing_step.value = value

    @property
    def wm_user_agent(self) -> str:
        """User-Agent header compliant with Wikimedia requirements"""
        return (
            f"{NAME}/{VERSION} ({self.contact_info}) "
            f"{SCRAPERLIB_NAME}/{SCRAPERLIB_VERSION} "
        )


# Singleton instance holding current scraper context
CONTEXT = Context()


def init_context_from_args(args: argparse.Namespace, tmpdir: str):
    """Initialize context from argparse parsed args"""

    logger.setLevel(level=logging.DEBUG if args.debug else logging.INFO)

    if args.optimization_cache:
        CONTEXT.s3_url_with_credentials = args.optimization_cache

    if args.assets_workers:
        CONTEXT.assets_workers = args.assets_workers

    if args.bad_assets_regex:
        CONTEXT.bad_assets_regex = re.compile(
            f"{args.bad_assets_regex}|{STANDARD_KNOWN_BAD_ASSETS_REGEX}", re.IGNORECASE
        )

    if args.bad_assets_threshold:
        CONTEXT.bad_assets_threshold = args.bad_assets_threshold

    if args.contact_info:
        CONTEXT.contact_info = args.contact_info

    if args.output:
        CONTEXT.output_folder = Path(args.output)

    CONTEXT.tmp_folder = Path(args.tmp if args.tmp else tmpdir)

    if args.zimui_dist:
        CONTEXT.zimui_dist = Path(args.zimui_dist)

    if args.stats_filename:
        CONTEXT.stats_filename = Path(args.stats_filename)

    if args.overwrite:
        CONTEXT.overwrite_existing_zim = args.overwrite

    if args.illustration_url:
        CONTEXT.illustration_url = args.illustration_url

    CONTEXT.library_url = str(args.library_url)
