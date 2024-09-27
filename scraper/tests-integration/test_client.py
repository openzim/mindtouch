import io

import pytest
from zimscraperlib.download import (
    stream_file,  # pyright: ignore[reportUnknownVariableType]
)
from zimscraperlib.image.probing import format_for

from libretexts2zim.client import LibreTextsClient, LibreTextsHome


@pytest.fixture(scope="module")
def client(libretexts_slug: str) -> LibreTextsClient:
    return LibreTextsClient(library_slug=libretexts_slug)


@pytest.fixture(scope="module")
def home(client: LibreTextsClient) -> LibreTextsHome:
    return client.get_home()


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
