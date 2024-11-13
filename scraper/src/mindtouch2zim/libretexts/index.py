from bs4 import BeautifulSoup
from pydantic import BaseModel
from zimscraperlib.rewriting.html import HtmlRewriter

from mindtouch2zim.client import LibraryPage, MindtouchClient


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
    rewriter: HtmlRewriter, mindtouch_client: MindtouchClient, page: LibraryPage
) -> str:
    """Get and rewrite index HTML"""
    return get_libretexts_transformed_html(
        rewriter.rewrite(
            mindtouch_client.get_template_content(
                page_id=mindtouch_client.get_page_parent_book_id(page.id),
                template="=Template%253AMindTouch%252FIDF3%252FViews%252FTag_directory",
            )
        ).content
    )


def get_libretexts_transformed_html(template_content: str) -> str:
    """Transform HTML from Mindtouch template into Libretexts HTML

    - sort by first letter
    - ignore special tags
    """
    soup = BeautifulSoup(
        template_content,
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
        if letter in letters:
            letters[letter].items.append(index_item)
        else:
            letters[letter] = IndexLetter(letter=letter, items=[index_item])

    def _get_pages_tags(item_pages: list[IndexPage]):
        return "".join(
            [
                f'<a title="{page.title}" href="{page.href}" class="indexPages">'
                f"{page.title}</a><br>"
                for page in item_pages
            ]
        )

    def _get_letter_tags(letter: IndexLetter):
        return "".join(
            [
                f'<div class="termDiv"><p>{item.term}</p><div class="pagesTextDiv">'
                f"{_get_pages_tags(item.pages)}"
                "</div></div>"
                for item in letter.items
            ]
        )

    return BeautifulSoup(
        "\n".join(
            [
                '<p id="indexLetterList">',
                "\n • \n".join(
                    [
                        f'<a href="#indexHeadRow{letter}">{letter}</a>'
                        for letter in letters
                    ]
                ),
                "</p>",
                '<div id="indexTable">',
                "".join(
                    [
                        f'<div class="letterDiv" id="letterDiv{letter_char}">'
                        f'<div class="indexBodyRows" id="indexRow{letter_char}">'
                        f'<h2 class="indexRowHeadCells" id="indexHeadRow{letter_char}">'
                        f"{letter_char}</h2>"
                        f"{_get_letter_tags(letter_obj)}"
                        "</div>"
                        "</div>"
                        for letter_char, letter_obj in letters.items()
                    ]
                ),
                "</div>",
            ]
        ),
        "html.parser",  # prefer html.parser to not add <html><body> tags
    ).prettify()
