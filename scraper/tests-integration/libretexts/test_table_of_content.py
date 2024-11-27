import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape

from mindtouch2zim.client import LibraryPage, MindtouchClient
from mindtouch2zim.constants import ROOT_DIR
from mindtouch2zim.libretexts.table_of_content import _render_html_from_data


@pytest.fixture(scope="module")
def page_data(client: MindtouchClient) -> LibraryPage:
    cover_page = client.get_cover_page_id("15839")
    assert cover_page
    return client.get_page_tree(cover_page).root


def test_render_table_of_content_template(page_data: LibraryPage):
    jinja2_env = Environment(
        loader=FileSystemLoader(ROOT_DIR.joinpath("templates")),
        autoescape=select_autoescape(),
    )
    template = jinja2_env.get_template("libretexts.table-of-content.html")
    assert _render_html_from_data(template, page_data)
