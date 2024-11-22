class InvalidFormatError(Exception):
    """Raised when a user supplied template has an invalid parameter."""

    pass


class NoIllustrationFoundError(Exception):
    """An exception raised when no suitable illustration has been found"""

    pass


class KnownBadAssetFailedError(Exception):
    """An exception raised when an asset known to be failing, failed as expected"""

    pass
