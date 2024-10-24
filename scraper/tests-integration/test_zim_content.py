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

    assert "mindtouch2zim " in zim_fh.get_text_metadata("Scraper")
    assert zim_fh.get_text_metadata("Title") == "LibreTexts Geosciences"
    assert (
        zim_fh.get_text_metadata("Description")
        == "Geosciences courses from libretexts.org"
    )
    assert zim_fh.get_text_metadata("Language") == "eng"
    assert zim_fh.get_text_metadata("Publisher") == "openZIM"
    assert zim_fh.get_text_metadata("Creator") == "LibreTexts"


@pytest.mark.parametrize(
    "item_path,expected_mimetype",
    [
        pytest.param("content/logo.png", "image/png", id="logo"),
        pytest.param("content/screen.css", "text/css", id="screen.css"),
        pytest.param("content/print.css", "text/css", id="print.css"),
        pytest.param("content/inline.css", "text/css", id="inline.css"),
        pytest.param(
            "mathjax/es5/tex-svg.js", "application/javascript", id="mathjax-tex-svg.js"
        ),
    ],
)
def test_zim_content_expected_files(
    zim_fh: Archive, item_path: str, expected_mimetype: str
):
    """Ensure proper content at content/logo.png"""

    expected_file = zim_fh.get_item(item_path)
    assert expected_file
    assert expected_file.mimetype == expected_mimetype
    assert len(expected_file.content) > 0


def test_zim_content_shared_json(zim_fh: Archive):
    """Ensure proper content at content/shared.json"""

    shared_json = zim_fh.get_item("content/shared.json")
    assert shared_json.mimetype == "application/json"
    shared_content = json.loads(bytes(shared_json.content))
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
    assert config_json.mimetype == "application/json"
    assert json.loads(bytes(config_json.content)) == {"secondaryColor": "#FFFFFF"}


@pytest.mark.parametrize("page_id", [28207, 28208, 28209, 28212])
def test_zim_content_page_content_json(page_id: str, zim_fh: Archive):
    """Ensure proper content at content/config.json"""

    config_json = zim_fh.get_item(f"content/page_content_{page_id}.json")
    assert config_json.mimetype == "application/json"
    page_content_keys = json.loads(bytes(config_json.content)).keys()
    assert "htmlBody" in page_content_keys
