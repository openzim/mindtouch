import io
from pathlib import Path

import pytest
from zimscraperlib.download import (
    stream_file,  # pyright: ignore[reportUnknownVariableType]
)
from zimscraperlib.image.probing import format_for

from libretexts2zim.client import LibreTextsClient, LibreTextsHome


@pytest.fixture(scope="module")
def client(libretexts_slug: str, cache_folder: Path) -> LibreTextsClient:
    return LibreTextsClient(library_slug=libretexts_slug, cache_folder=cache_folder)


@pytest.fixture(scope="module")
def home(client: LibreTextsClient) -> LibreTextsHome:
    return client.get_home()


@pytest.fixture(scope="module")
def deki_token(client: LibreTextsClient) -> str:
    return client.get_deki_token()


@pytest.fixture(scope="module")
def minimum_number_of_pages() -> int:
    return 8000


@pytest.fixture(scope="module")
def root_page_id() -> str:
    return "34"


def test_get_deki_token(deki_token: str):
    """Ensures we achieve to get a deki_token"""
    assert deki_token


def test_get_all_pages_ids(
    client: LibreTextsClient,
    minimum_number_of_pages: int,
    deki_token: str,  # noqa: ARG001
):
    pages_ids = client.get_all_pages_ids()
    assert len(pages_ids) > minimum_number_of_pages


def test_get_root_page_id(
    client: LibreTextsClient,
    root_page_id: str,
    deki_token: str,  # noqa: ARG001
):
    assert client.get_root_page_id() == root_page_id


def test_get_home_image_url(home: LibreTextsHome):
    """Ensures proper image url is retrieved"""
    assert home.welcome_image_url == "https://cdn.libretexts.net/Logos/geo_full.png"


def test_get_home_image_size(home: LibreTextsHome, home_png_size: int):
    """Ensures image url is retrievable"""
    dst = io.BytesIO()
    stream_file(home.welcome_image_url, byte_stream=dst)
    assert format_for(dst, from_suffix=False) == "PNG"
    assert len(dst.getvalue()) == home_png_size


def test_get_home_welcome_text_paragraphs(
    home: LibreTextsHome, home_welcome_text_paragraphs: list[str]
):
    """Ensures proper data is retrieved from home of libretexts"""

    assert home.welcome_text_paragraphs == home_welcome_text_paragraphs
