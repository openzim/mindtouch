class InvalidFormatError(Exception):
    """Raised when a user supplied template has an invalid parameter."""

    pass


class UnsupportedTagError(Exception):
    """An exception raised when an HTML tag is not expected to be encountered"""

    pass


class UnsupportedHrefSrcError(Exception):
    """An exception raised when an href or src is not expected to be encountered"""

    pass


class NoIllustrationFoundError(Exception):
    """An exception raised when no suitable illustration has been found"""

    pass
