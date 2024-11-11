from bs4 import BeautifulSoup


class GlossaryRewriteError(Exception):
    """Exception indicating a problem during glossary rewrite"""

    pass


def _get_formatted_glossary_row(row) -> str:
    """Format one row as HTML"""
    word = row.find("td", attrs={"data-th": "Word(s)"}).text
    definition = row.find("td", attrs={"data-th": "Definition"}).text
    return (
        '<p class="glossaryElement">\n'
        f'  <span class="glossaryTerm">{word}</span>\n'
        "  |\n"
        f'  <span class="glossaryDefinition">{definition}</span>\n'
        "</p>\n"
    )


def rewrite_glossary(original_content: str) -> str:
    """Statically rewrite the glossary of libretexts.org

    Only word and description columns are supported.
    """

    soup = BeautifulSoup(
        original_content,
        "html.parser",  # prefer html.parser to not add <html><body> tags
    )

    glossary_table = None

    for table in soup.find_all("table"):
        if not table.caption:
            continue
        if table.caption and table.caption.text.strip() == "Example and Directions":
            continue
        if glossary_table:
            raise GlossaryRewriteError("Too many glossary tables")
        glossary_table = table

    if not glossary_table:
        raise GlossaryRewriteError("Glossary table not found")

    tbody = glossary_table.find("tbody")
    if not tbody:
        raise GlossaryRewriteError("Glossary table body not found")

    glossary_table.insert_after(
        BeautifulSoup(
            "".join([_get_formatted_glossary_row(row) for row in tbody.find_all("tr")]),
            "html.parser",  # prefer html.parser to not add <html><body> tags
        )
    )

    # remove all tables and scripts
    for item in soup.find_all("table") + soup.find_all("script"):
        item.decompose()
    return soup.prettify()
