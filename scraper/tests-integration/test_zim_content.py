import json
import os
from pathlib import Path

import pytest
from zimscraperlib.zim import Archive

ZIM_FILE_PATH = Path(os.environ["ZIM_FILE_PATH"])


@pytest.fixture(scope="module")
def zim_file_path() -> Path:
    return ZIM_FILE_PATH


@pytest.fixture(scope="module")
def zim_fh() -> Archive:
    return Archive(ZIM_FILE_PATH)


def test_is_file(zim_file_path: Path):
    """Ensure ZIM file exists"""
    assert zim_file_path.exists()
    assert zim_file_path.is_file()


def test_zim_main_page(zim_fh: Archive):
    """Ensure main page is a redirect to index.html"""

    main_entry = zim_fh.main_entry
    assert main_entry.is_redirect
    assert main_entry.get_redirect_entry().path == "index.html"


def test_zim_metadata(zim_fh: Archive):
    """Ensure scraper and zim title are present in metadata"""

    assert "libretexts2zim " in zim_fh.get_text_metadata("Scraper")
    assert zim_fh.get_text_metadata("Title") == "Geosciences courses"
    assert (
        zim_fh.get_text_metadata("Description") == "Geosciences courses by LibreTexts"
    )
    assert zim_fh.get_text_metadata("Language") == "eng"
    assert zim_fh.get_text_metadata("Publisher") == "openZIM"
    assert zim_fh.get_text_metadata("Creator") == "LibreTexts"

    # assert zim_fh.get_item("favicon.png").get_mimetype() == "image/png"
    # assert zim_fh.get_item("index.html").get_mimetype() == "text/html"


def test_zim_content_logo_png(zim_fh: Archive, home_png_size: int):
    """Ensure proper content at content/logo.png"""

    logo_png = zim_fh.get_item("content/logo.png")
    assert logo_png.mimetype == "image/png"  # pyright: ignore
    assert len(logo_png.content) == home_png_size  # pyright: ignore


def test_zim_content_shared_json(zim_fh: Archive):
    """Ensure proper content at content/shared.json"""

    shared_json = zim_fh.get_item("content/shared.json")
    assert shared_json.mimetype == "application/json"  # pyright: ignore
    shared_content = json.loads(bytes(shared_json.content))  # pyright: ignore
    shared_content_keys = shared_content.keys()
    assert "logoPath" in shared_content_keys
    assert "rootPagePath" in shared_content_keys
    assert "pages" in shared_content_keys
    assert len(shared_content["pages"]) == 4
    for page in shared_content["pages"]:
        shared_content_page_keys = page.keys()
        assert "id" in shared_content_page_keys
        assert "title" in shared_content_page_keys
        assert "path" in shared_content_page_keys


def test_zim_content_config_json(zim_fh: Archive):
    """Ensure proper content at content/config.json"""

    config_json = zim_fh.get_item("content/config.json")
    assert config_json.mimetype == "application/json"  # pyright: ignore
    assert json.loads(bytes(config_json.content)) == {  # pyright: ignore
        "secondaryColor": "#FFFFFF"
    }


@pytest.mark.parametrize("page_id", [28207, 28208, 28209, 28212])
def test_zim_content_page_content_json(page_id: str, zim_fh: Archive):
    """Ensure proper content at content/config.json"""

    config_json = zim_fh.get_item(f"content/page_content_{page_id}.json")
    assert config_json.mimetype == "application/json"  # pyright: ignore
    page_content_keys = json.loads(bytes(config_json.content)).keys()  # pyright: ignore
    assert "htmlBody" in page_content_keys
