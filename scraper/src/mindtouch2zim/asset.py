from io import BytesIO

from zimscraperlib.download import (
    stream_file,  # pyright: ignore[reportUnknownVariableType]
)
from zimscraperlib.rewriting.url_rewriting import HttpUrl

from mindtouch2zim.constants import web_session


def download_asset(asset_url: HttpUrl) -> BytesIO:
    """Download of a given asset, optimize if needed, or download from S3 cache"""
    asset_content = BytesIO()
    stream_file(
        asset_url.value,
        byte_stream=asset_content,
        session=web_session,
    )
    return asset_content
