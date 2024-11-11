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
        "https://a.mtstatic.com/@public/production/site_4038/"
        "1486479235-apple-touch-icon.png",
        "https://a.mtstatic.com/@public/production/site_4038/1486479325-favicon.ico",
    ]


@pytest.fixture(scope="module")
def home_js_urls() -> list[str]:
    return [
        "https://a.mtstatic.com/deki/javascript/out/globals.jqueryv2.2.4.polyfill.js?"
        "_=73ece948eb3cf439a16b7a5ea85a12e58f792652:site_4038",
        "https://a.mtstatic.com/deki/javascript/out/deki.legacy.js?"
        "_=73ece948eb3cf439a16b7a5ea85a12e58f792652:site_4038",
        "https://a.mtstatic.com/deki/javascript/out/community.js?"
        "_=73ece948eb3cf439a16b7a5ea85a12e58f792652:site_4038",
        "https://a.mtstatic.com/deki/javascript/out/standalone/skin_elm.js?"
        "_=73ece948eb3cf439a16b7a5ea85a12e58f792652:site_4038",
        "https://a.mtstatic.com/deki/javascript/out/standalone/pageBootstrap.js?"
        "_=73ece948eb3cf439a16b7a5ea85a12e58f792652:site_4038",
        "https://cdn.libretexts.net/github/readerview/js-loading-overlay.min.js",
        "https://cdn.libretexts.net/github/readerview/vendor/"
        "jquery-accessibleMegaMenu.js",
        "https://cdn.libretexts.net/github/LibreTextsMain/Miscellaneous/reuse.js",
        "https://cdn.libretexts.net/github/LibreTextsMain/Miscellaneous/"
        "copyNavigation.js",
        "https://cdn.libretexts.net/github/Beeline/beeline.min.js",
        "https://cdnjs.cloudflare.com/ajax/libs/jquery.fancytree/2.30.0/"
        "jquery.fancytree-all-deps.min.js",
        "https://cdn.libretexts.net/github/LibreTextsMain/NavButtons/"
        "libreNavButtons.min.js",
        "https://cdn.libretexts.net/github/LibreTextsMain/ExportButtons/"
        "libreExportButtons.min.js",
        "https://cdn.libretexts.net/github/LibreTextsMain/Binh Nguyen/ReactSidebar/"
        "build/sidebar.min.js",
        "https://cdn.libretexts.net/github/LibreTextsMain/LicenseControl/"
        "licensecontrol.min.js",
        "https://cdn.libretexts.net/github/LibreTextsMain/Leo%20Jayachandran/"
        "Glossarizer/libretextsGlossarizer.js",
        "https://cdn.libretexts.net/github/LibreTextsMain/Henry%20Agnew/LibreLens.js",
        "https://cdn.libretexts.net/github/LibreTextsMain/Aryan Suri/Citation/"
        "citationjs.js",
        "https://cdn.libretexts.net/github/LibreTextsMain/Aryan Suri/Citation/"
        "citation.js",
        "https://cdn.libretexts.net/github/LibreTextsMain/Aryan Suri/Citation/"
        "attribution.js",
        "https://cdn.libretexts.net/github/LibreTextsMain/Miscellaneous/Molecules/"
        "GLmol/js/Three49custom.js",
        "https://cdn.libretexts.net/github/LibreTextsMain/Miscellaneous/Molecules/"
        "GLmol/js/GLmol.js",
        "https://cdn.libretexts.net/github/LibreTextsMain/Miscellaneous/Molecules/"
        "JSmol/JSmol.full.nojq.js",
        "https://use.fontawesome.com/84b10e0f37.js",
        "https://cdn.libretexts.net/github/ckeditor-binder-plugin/js/"
        "registerPlugin.min.js",
        "https://cdn.libretexts.net/github/ckeditor-query-plugin/queryPlugin.min.js",
        "https://cdn.libretexts.net/github/LibreTextsMain/EditorPlugins/dist/"
        "libreFormatPlugin.min.js",
        "https://cdn.libretexts.net/github/LibreTextsMain/EditorPlugins/dist/"
        "libreBoxesPlugin.min.js",
        "https://cdn.libretexts.net/github/LibreTextsMain/EditorPlugins/dist/"
        "libreQueryPlugin.min.js",
        "https://cdn.libretexts.net/github/ckeditor-a11ychecker-plugin/"
        "a11yPlugin.min.js",
        "https://geo.libretexts.org/@embed/f1.js",
        "https://a.mtstatic.com/deki/javascript/out/standalone/"
        "ui.widget.lsfOrderedSubpages.js?"
        "_=73ece948eb3cf439a16b7a5ea85a12e58f792652:site_4038",
        "https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.5/"
        "MathJax.js?config=TeX-AMS_HTML",
        "https://a.mtstatic.com/deki/javascript/out/standalone/"
        "serviceworker-unregister.js?"
        "_=73ece948eb3cf439a16b7a5ea85a12e58f792652:site_4038",
        "https://a.mtstatic.com/deki/javascript/out/standalone/"
        "pageLoaded.js?_=73ece948eb3cf439a16b7a5ea85a12e58f792652:site_4038",
    ]
