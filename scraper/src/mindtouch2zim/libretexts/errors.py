class BadBookPageError(Exception):
    """Raised when we are processing a special book page but we are not inside a book"""

    pass
