from mindtouch2zim.context import Context
from mindtouch2zim.errors import VimeoThumbnailError

context = Context.get()
logger = context.logger


def get_vimeo_thumbnail_url(video_url: str) -> str:
    """From a vimeo URL - player or normal - retrieve corresponding thumbnail URL"""
    resp = context.web_session.get(
        f"https://vimeo.com/api/oembed.json?url={video_url}",
        timeout=context.http_timeout_normal_seconds,
    )
    resp.raise_for_status()
    json_doc = resp.json()
    if "thumbnail_url" not in json_doc:
        logger.warning(f"Failed to find thumbnail_url in response:\n{resp.text}")
        raise VimeoThumbnailError("API response misses the thumbnail_url")
    thumbnail_url = json_doc["thumbnail_url"]
    if not thumbnail_url:
        logger.warning(f"Emtpy thumbnail_url in response:\n{resp.text}")
        raise VimeoThumbnailError("API response has empty thumbnail_url")
    return thumbnail_url
