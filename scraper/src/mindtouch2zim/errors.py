class InvalidFormatError(Exception):
    """Raised when a user supplied template has an invalid parameter."""

    pass


class NoIllustrationFoundError(Exception):
    """An exception raised when no suitable illustration has been found"""

    pass


class KnownBadAssetFailedError(Exception):
    """An exception raised when an asset known to be failing, failed as expected"""

    pass


class VimeoThumbnailError(Exception):
    """Error raised when there is a problem with a vimeo video"""

    pass


class GlossaryRewriteError(Exception):
    """Exception indicating a problem during glossary rewrite"""

    pass


class S3InvalidCredentialsError(Exception):
    """Raised when S3 credentials are invalid"""

    pass


class S3CacheError(Exception):
    """Raised when there is a problem with the S3 cache"""

    pass


class MindtouchParsingError(Exception):
    pass


class APITokenRetrievalError(Exception):
    """Exception raised when failing to retrieve API token to query website API"""

    pass
