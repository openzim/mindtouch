from jinja2 import Template
from zimscraperlib.rewriting.html import HtmlRewriter

from mindtouch2zim.client import LibraryPage, MindtouchClient
from mindtouch2zim.libretexts.errors import BadBookPageError

"""
Logic here and in the Jinja2 template comes from
https://cdn.libretexts.net/github/LibreTextsMain/DynamicTOC/dist/dynamicTOC.min.js

Probably coming from
https://github.com/LibreTexts/Libretext/blob/master/public/DynamicTOC/dynamicTOC.js and
https://github.com/LibreTexts/Libretext/blob/master/public/DynamicTOC/dynamicTOC.css
"""


def _render_html_from_data(jinja2_template: Template, cover_page: LibraryPage) -> str:
    return jinja2_template.render(cover_page=cover_page)


def rewrite_table_of_content(
    rewriter: HtmlRewriter,
    jinja2_template: Template,
    mindtouch_client: MindtouchClient,
    page: LibraryPage,
) -> str:
    """
    Get and statically rewrite the table of content of libretexts.org

    """

    cover_page = mindtouch_client.get_cover_page(page)
    if cover_page is None:
        raise BadBookPageError()
    return rewriter.rewrite(
        _render_html_from_data(jinja2_template=jinja2_template, cover_page=cover_page)
    ).content
