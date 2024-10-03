import datetime
import re
from collections.abc import Callable

import requests
from bs4 import BeautifulSoup, NavigableString
from pydantic import BaseModel

from libretexts2zim.constants import logger

HTTP_TIMEOUT_SECONDS = 15


class LibreTextsParsingError(Exception):
    pass


class LibreTextsHome(BaseModel):
    welcome_text_paragraphs: list[str]
    welcome_image_url: str


class LibreTextsMetadata(BaseModel):
    """Metadata about a library."""

    # Human readable name for the library.
    name: str

    # URL prefix for the library, e.g. for Geosciences which is at
    # https://geo.libretexts.org/, the slug is `geo`
    slug: str

    def placeholders(
        self, clock: Callable[[], datetime.date] = datetime.date.today
    ) -> dict[str, str]:
        """Gets placeholders for filenames.

        Arguments:
          clock: Override the default clock to use for producing the "period".
        """

        return {
            "name": self.name,
            "slug": self.slug,
            "clean_slug": re.sub(r"[^.a-zA-Z0-9]", "-", self.slug),
            "period": clock().strftime("%Y-%m"),
        }


class LibreTextsClient:
    """Utility functions to read data from libretexts."""

    def __init__(self, library_slug: str) -> None:
        """Initializes LibreTextsClient.

        Paremters:
            library_url: Scheme, hostname, and port for the Libretext library
                e.g. `https://geo.libretexts.org/`.
        """
        self.library_slug = library_slug

    @property
    def library_url(self) -> str:
        return f"https://{self.library_slug}.libretexts.org/"

    def _get_text(self, url: str) -> str:
        """Perform a GET request and return the response as decoded text."""

        logger.debug(f"Fetching {url}")

        resp = requests.get(
            url=url,
            allow_redirects=True,
            timeout=HTTP_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()

        return resp.text

    def get_home(self) -> LibreTextsHome:
        home_content = self._get_text(self.library_url)

        soup = _get_soup(home_content)
        return LibreTextsHome(
            welcome_text_paragraphs=_get_welcome_text_from_home(soup),
            welcome_image_url=_get_welcome_image_url_from_home(soup),
        )


def _get_soup(content: str) -> BeautifulSoup:
    return BeautifulSoup(content, "lxml")


def _get_welcome_image_url_from_home(soup: BeautifulSoup) -> str:
    branding_div = soup.find("div", class_="LTBranding")
    if not branding_div:
        raise LibreTextsParsingError("<div> with class 'LTBranding' not found")
    img_tag = branding_div.find("img")
    if not img_tag or isinstance(img_tag, int) or isinstance(img_tag, NavigableString):
        raise LibreTextsParsingError("<img> not found in <div> with class 'LTBranding'")
    img_src = img_tag["src"]
    if not img_src:
        raise LibreTextsParsingError(
            "<img> in <div> with class 'LTBranding' has no src attribute"
        )
    if isinstance(img_src, list):
        raise LibreTextsParsingError(
            "<img> in <div> with class 'LTBranding' has too many src attribute"
        )
    return img_src


def _get_welcome_text_from_home(soup: BeautifulSoup) -> list[str]:
    content_section = soup.find("section", class_="mt-content-container")
    if not content_section or isinstance(content_section, NavigableString):
        raise LibreTextsParsingError(
            "<section> with class 'mt-content-container' not found"
        )
    welcome_text: list[str] = []
    for paragraph in content_section.find_all("p", recursive=False):
        if paragraph_text := paragraph.text:
            welcome_text.append(paragraph_text)
    return welcome_text
