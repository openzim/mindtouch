import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest


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
