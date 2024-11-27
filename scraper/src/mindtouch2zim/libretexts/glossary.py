from bs4 import BeautifulSoup
from jinja2 import Template
from pydantic import BaseModel

from mindtouch2zim.errors import GlossaryRewriteError


class GlossaryEntry(BaseModel):
    word: str
    definition: str


def rewrite_glossary(jinja2_template: Template, original_content: str) -> str | None:
    """Statically rewrite the glossary of libretexts.org

    Only word and description columns are supported.
    """

    soup = BeautifulSoup(
        original_content,
        "html.parser",  # prefer html.parser to not add <html><body> tags
    )

    glossary_table = None

    tables = soup.find_all("table")
    if len(tables) == 0:
        # looks like this glossary is not using default template ; let's rewrite as
        # a normal page
        return None
    glossary_table = tables[-1]

    tbody = glossary_table.find("tbody")
    if not tbody:
        raise GlossaryRewriteError("Glossary table body not found")

    glossary_table.insert_after(
        BeautifulSoup(
            jinja2_template.render(
                entries=[
                    GlossaryEntry(
                        word=row.find("td", attrs={"data-th": "Word(s)"}).text,
                        definition=row.find("td", attrs={"data-th": "Definition"}).text,
                    )
                    for row in tbody.find_all("tr")
                ]
            ),
            "html.parser",  # prefer html.parser to not add <html><body> tags
        )
    )

    # remove all tables and scripts
    for item in soup.find_all("table") + soup.find_all("script"):
        item.decompose()
    return soup.prettify()
