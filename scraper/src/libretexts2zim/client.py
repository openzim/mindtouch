import datetime
import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

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

    def __init__(self, library_slug: str, cache_folder: Path) -> None:
        """Initializes LibreTextsClient.

        Paremters:
            library_url: Scheme, hostname, and port for the Libretext library
                e.g. `https://geo.libretexts.org/`.
        """
        self.library_slug = library_slug
        self.deki_token = None
        self.cache_folder = cache_folder

    @property
    def library_url(self) -> str:
        return f"https://{self.library_slug}.libretexts.org"

    @property
    def api_url(self) -> str:
        return f"{self.library_url}/@api/deki"

    def _get_cache_file(self, url_subpath_and_query: str) -> Path:
        """Get location where HTTP result should be cached"""
        if url_subpath_and_query.startswith("/"):
            url_subpath_and_query = url_subpath_and_query[1:]
        if url_subpath_and_query.endswith("/"):
            url_subpath_and_query += "index"
        return self.cache_folder / url_subpath_and_query

    def _get_text(self, url_subpath_and_query: str) -> str:
        """Perform a GET request and return the response as decoded text."""

        cache_file = self._get_cache_file(f"text{url_subpath_and_query}")
        if cache_file.exists():
            return cache_file.read_text()
        cache_file.parent.mkdir(parents=True, exist_ok=True)

        full_url = f"{self.library_url}{url_subpath_and_query}"
        logger.debug(f"Fetching {full_url}")

        resp = requests.get(
            url=full_url,
            allow_redirects=True,
            timeout=HTTP_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()

        cache_file.write_text(resp.text)
        return resp.text

    def _get_api_resp(
        self, api_sub_path_and_query: str, timeout: float
    ) -> requests.Response:
        api_url = f"{self.api_url}{api_sub_path_and_query}"
        logger.debug(f"Calling API at {api_url}")
        resp = requests.get(
            url=api_url,
            headers={"x-deki-token": self.deki_token},
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp

    def _get_api_json(
        self, api_sub_path: str, timeout: float = HTTP_TIMEOUT_SECONDS
    ) -> Any:
        cache_file = self._get_cache_file(f"api_json{api_sub_path}")
        if cache_file.exists():
            return json.loads(cache_file.read_text())
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        resp = self._get_api_resp(
            f"{api_sub_path}?dream.out.format=json", timeout=timeout
        )
        result = resp.json()
        cache_file.write_text(json.dumps(result))
        return result

    def _get_api_content(
        self, api_sub_path: str, timeout: float = HTTP_TIMEOUT_SECONDS
    ) -> bytes | Any:
        cache_file = self._get_cache_file(f"api_content{api_sub_path}")
        if cache_file.exists():
            return json.loads(cache_file.read_text())
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        resp = self._get_api_resp(api_sub_path, timeout=timeout)
        result = resp.content
        cache_file.write_bytes(result)
        return result

    def get_home(self) -> LibreTextsHome:
        """Retrieves data about home page by crawling home page"""
        home_content = self._get_text("/")

        soup = _get_soup(home_content)
        self.deki_token = _get_deki_token_from_home(soup)
        return LibreTextsHome(
            welcome_text_paragraphs=_get_welcome_text_from_home(soup),
            welcome_image_url=_get_welcome_image_url_from_home(soup),
        )

    def get_deki_token(self) -> str:
        """Retrieves the API token to use to query the website API"""
        if self.deki_token:
            return self.deki_token

        home_content = self._get_text("/")

        soup = _get_soup(home_content)
        self.deki_token = _get_deki_token_from_home(soup)
        return self.deki_token

    def get_all_pages_ids(self):
        """Returns the IDs of all pages on current website, exploring the whole tree"""

        tree = self._get_api_json("/pages/home/tree", timeout=HTTP_TIMEOUT_SECONDS * 2)

        page_ids: list[str] = []

        def _get_page_ids(page_node: Any) -> None:
            page_ids.append(page_node["@id"])
            if not page_node["subpages"]:
                return
            if "@id" in page_node["subpages"]["page"]:
                _get_page_ids(page_node["subpages"]["page"])
            else:
                for page in page_node["subpages"]["page"]:
                    _get_page_ids(page)

        _get_page_ids(tree["page"])

        return page_ids

    def get_root_page_id(self) -> str:
        """Returns the ID the root of the tree of pages"""

        tree = self._get_api_json("/pages/home/tree", timeout=HTTP_TIMEOUT_SECONDS * 2)
        return tree["page"]["@id"]


def _get_soup(content: str) -> BeautifulSoup:
    """Return a BeautifulSoup soup from textual content

    This is a utility function to ensure same parser is used in the whole codebase
    """
    return BeautifulSoup(content, "lxml")

def _get_welcome_image_url_from_home(soup: BeautifulSoup) -> str:
    """Return the URL of the image found on home header"""
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
    """Returns the text found on home page"""
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


def _get_deki_token_from_home(soup: BeautifulSoup) -> str:
    global_settings = soup.find("script", id="mt-global-settings")
    if not global_settings:
        logger.debug("home content:")
        logger.debug(soup)
        raise Exception(
            "Failed to retrieve API token to query website API, missing "
            "mt-global-settings script"
        )
    x_deki_token = json.loads(global_settings.text).get("apiToken", None)
    if not x_deki_token:
        logger.debug("mt-global-settings script content:")
        logger.debug(global_settings.text)
        raise Exception(
            "Failed to retrieve API token to query website API, missing apiToken."
        )
    return x_deki_token
