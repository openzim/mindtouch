from bs4 import BeautifulSoup
from jinja2 import Template
from pydantic import BaseModel
from zimscraperlib.rewriting.html import HtmlRewriter

from mindtouch2zim.client import LibraryPage, MindtouchClient
from mindtouch2zim.libretexts.errors import BadBookPageError


class IndexPage(BaseModel):
    href: str
    title: str


class IndexItem(BaseModel):
    term: str
    pages: list[IndexPage]


class IndexLetter(BaseModel):
    letter: str
    items: list[IndexItem]


def rewrite_index(
    rewriter: HtmlRewriter,
    jinja2_template: Template,
    mindtouch_client: MindtouchClient,
    page: LibraryPage,
) -> str:
    """Get and rewrite index HTML"""
    cover_page_id = mindtouch_client.get_cover_page_id(page)
    if cover_page_id is None:
        raise BadBookPageError()
    return get_libretexts_transformed_html(
        jinja2_template=jinja2_template,
        libretexts_template_content=rewriter.rewrite(
            mindtouch_client.get_template_content(
                page_id=cover_page_id,
                template="=Template%253AMindTouch%252FIDF3%252FViews%252FTag_directory",
            )
        ).content,
    )


def get_libretexts_transformed_html(
    jinja2_template: Template, libretexts_template_content: str
) -> str:
    """Transform HTML from Mindtouch template into Libretexts HTML

    - sort by first letter
    - ignore special tags
    """
    soup = BeautifulSoup(
        libretexts_template_content,
        "html.parser",  # prefer html.parser to not add <html><body> tags
    )
    letters: dict[str, IndexLetter] = {}
    ul = soup.find_all("ul")[0]
    for item in ul.children:
        term = str(item.find("h5").text.strip())
        if term.startswith("source["):
            # special tags, to ignore
            continue
        index_item = IndexItem(
            term=term,
            pages=[
                IndexPage(
                    href=child_item.find("a")["href"], title=child_item.text.strip()
                )
                for child_item in item.find_all("li")
            ],
        )
        letter = index_item.term[0].upper()
        if letter not in letters:
            letters[letter] = IndexLetter(letter=letter, items=[])
        letters[letter].items.append(index_item)

    return jinja2_template.render(letters=letters)
