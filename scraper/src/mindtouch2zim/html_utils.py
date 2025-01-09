from bs4 import BeautifulSoup


def get_soup(content: str) -> BeautifulSoup:
    """Return a BeautifulSoup soup from HTML content

    This is a utility function to ensure same parser is used in the whole codebase
    """
    return BeautifulSoup(content, "lxml")


def get_text(content: str) -> str:
    """Return text data from HTML content

    This is typically meant to extract content to index in the ZIM
    """
    return get_soup(content).getText("\n", strip=True)
