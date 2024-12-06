import tempfile
import threading
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from zimscraperlib.download import get_session

from mindtouch2zim.context import Context

CONTEXT_DEFAULTS = {
    "web_session": get_session(),
    "tmp_folder": None,
    "cache_folder": None,
    "_current_thread_workitem": threading.local(),
    "library_url": None,
    "creator": None,
    "name": None,
    "title": None,
    "description": None,
}


# initialize a context since it is a requirement for most modules to load
Context.setup(**CONTEXT_DEFAULTS)

context = Context.get()

# import client late so that context is already initialized
from mindtouch2zim.client import MindtouchClient  # noqa: E402


@pytest.fixture(scope="module")
def libretexts_slug() -> str:
    return "geo"


@pytest.fixture(scope="module")
def cache_folder() -> Generator[Path, Any, Any]:
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture(scope="module")
def libretexts_url(libretexts_slug: str) -> str:
    return f"https://{libretexts_slug}.libretexts.org"


@pytest.fixture(scope="module")
def home_png_size() -> int:
    return 13461


@pytest.fixture(scope="module")
def home_welcome_text_paragraphs() -> list[str]:
    return [
        "Welcome to the Geosciences Library. This Living Library is a principal hub of "
        "the LibreTexts project, which is a multi-institutional collaborative venture "
        "to develop the next generation of open-access texts to improve postsecondary "
        "education at all levels of higher learning. The LibreTexts approach is highly "
        "collaborative where an Open Access textbook environment is under constant "
        "revision by students, faculty, and outside experts to supplant conventional "
        "paper-based books."
    ]


@pytest.fixture(scope="module")
def home_icons_urls() -> list[str]:
    return [
        "https://a.mtstatic.com/@public/production/site_4038/1486479235-apple-touch-icon.png",
        "https://a.mtstatic.com/@public/production/site_4038/1486479325-favicon.ico",
    ]


@pytest.fixture(scope="module")
def raw_client(libretexts_url: str, cache_folder: Path) -> MindtouchClient:
    context.library_url = libretexts_url
    context.cache_folder = cache_folder
    return MindtouchClient()


@pytest.fixture(scope="module")
def client(
    raw_client: MindtouchClient,
    deki_token: str,  # noqa: ARG001
) -> MindtouchClient:
    """already authenticated client (avoid having to fetch deki_token in tests)"""
    return raw_client


@pytest.fixture(scope="module")
def deki_token(raw_client: MindtouchClient) -> str:
    return raw_client.get_deki_token()
