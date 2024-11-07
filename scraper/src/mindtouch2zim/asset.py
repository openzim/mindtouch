from io import BytesIO
from typing import NamedTuple

from kiwixstorage import KiwixStorage, NotFoundError
from PIL import Image
from zimscraperlib.download import stream_file
from zimscraperlib.image.optimization import optimize_webp
from zimscraperlib.image.presets import WebpMedium
from zimscraperlib.image.transformation import resize_image
from zimscraperlib.rewriting.url_rewriting import HttpUrl, ZimPath

from mindtouch2zim.constants import logger, web_session

SUPPORTED_IMAGE_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/bmp",
    "image/tiff",
    "image/webp",
    "image/x-portable-pixmap",
    "image/x-portable-graymap",
    "image/x-portable-bitmap",
    "image/x-portable-anymap",
    "image/vnd.microsoft.icon",
    "image/vnd.ms-dds",
    "application/postscript",  # for EPS files
}

WEBP_OPTIONS = WebpMedium().options

MAX_IMAGE_SIZE = 640


class HeaderData(NamedTuple):
    ident: str  # ~version~ of the URL data to use for comparisons
    content_type: str | None


class AssetProcessor:

    def __init__(
        self, s3_url_with_credentials: str | None, *, resize_images: bool
    ) -> None:
        self.s3_url_with_credentials = s3_url_with_credentials
        self.s3_storage = KiwixStorage(s3_url_with_credentials)
        self.resize_images = resize_images

    def _get_header_data_for(self, url: HttpUrl) -> HeaderData:
        """Get details from headers for a given url

        - get response headers with GET and streaming (retrieveing only 1 byte)
          - we do not HEAD because it is not possible to follow redirects directly
            with a HEAD request, and this method is not always implemented / might lie
        - extract HeaderData from these response headers and return it
        """
        _, headers = stream_file(
            url=url.value,
            byte_stream=BytesIO(),
            block_size=1,
            only_first_block=True,
        )

        content_type = headers.get("Content-Type", None)

        for header in ("ETag", "Last-Modified", "Content-Length"):
            if header := headers.get(header):
                return HeaderData(ident=header, content_type=content_type)

        return HeaderData(ident="-1", content_type=content_type)

    def _get_image_content(
        self, asset_path: ZimPath, asset_url: HttpUrl, header_data: HeaderData
    ) -> BytesIO:
        """Get image content for a given url

        - download from S3 cache if configured and available
        - otherwise:
        - download from online
        - convert to webp
        - optimize webp
        - upload to S3 cache if configured
        """
        meta = {"ident": header_data.ident, "version": str(WebpMedium.VERSION)}
        s3_key = f"medium/{asset_path.value}"

        if self.s3_url_with_credentials:
            if s3_data := self._download_from_s3_cache(s3_key=s3_key, meta=meta):
                logger.debug("Fetching directly from S3 cache")
                return s3_data  # found in cache

        logger.debug("Fetching from online")
        unoptimized = self._download_from_online(asset_url=asset_url)

        logger.debug("Optimizing")
        optimized = BytesIO()
        with Image.open(unoptimized) as img:
            img.save(optimized, format="WEBP")
            img_width = img.width
            img_height = img.height
            del unoptimized

        if self.resize_images:  # probably not worth it, tbc with real measurements
            if img_width >= img_height and img_width > MAX_IMAGE_SIZE:
                # image is in landscape
                resize_image(src=optimized, width=MAX_IMAGE_SIZE, allow_upscaling=False)
            elif img_height > MAX_IMAGE_SIZE:
                # image is in portrait
                resize_image(
                    src=optimized,
                    width=int(img_width / img_height * MAX_IMAGE_SIZE),
                    allow_upscaling=False,
                )

        optimize_webp(
            src=optimized,
            quality=WEBP_OPTIONS.get("quality"),  # pyright: ignore[reportArgumentType]
            method=WEBP_OPTIONS.get("method"),  # pyright: ignore[reportArgumentType]
            lossless=WEBP_OPTIONS.get(
                "lossless"
            ),  # pyright: ignore[reportArgumentType]
        )

        if self.s3_url_with_credentials:
            # upload optimized to S3
            logger.debug("Uploading to S3")
            self._upload_to_s3_cache(
                s3_key=s3_key, meta=meta, asset_content=BytesIO(optimized.getvalue())
            )

        return optimized

    def _download_from_s3_cache(
        self, s3_key: str, meta: dict[str, str]
    ) -> BytesIO | None:
        try:
            asset_content = BytesIO()
            self.s3_storage.download_matching_fileobj(  # pyright: ignore[reportUnknownMemberType]
                s3_key, asset_content, meta=meta
            )
            return asset_content
        except NotFoundError:
            return None
        except Exception as exc:
            raise Exception(f"Failed to download {s3_key} from S3 cache") from exc

    def _upload_to_s3_cache(
        self, s3_key: str, meta: dict[str, str], asset_content: BytesIO
    ):
        try:
            self.s3_storage.upload_fileobj(  # pyright: ignore[reportUnknownMemberType]
                key=s3_key, fileobj=asset_content, meta=meta
            )
        except Exception as exc:
            raise Exception(f"Failed to upload {s3_key} to S3 cache") from exc

    def _download_from_online(self, asset_url: HttpUrl) -> BytesIO:
        """Download whole content from online server with retry from scraperlib"""

        asset_content = BytesIO()
        stream_file(
            asset_url.value,
            byte_stream=asset_content,
            session=web_session,
        )
        return asset_content

    def get_asset_content(
        self, asset_path: ZimPath, asset_url: HttpUrl, *, always_fetch_online: bool
    ) -> BytesIO:
        """Download of a given asset, optimize if needed, or download from S3 cache"""

        if not always_fetch_online:
            header_data = self._get_header_data_for(asset_url)
            if header_data.content_type:
                mime_type = header_data.content_type.split(";")[0].strip()
                if mime_type in SUPPORTED_IMAGE_MIME_TYPES:
                    return self._get_image_content(
                        asset_path=asset_path,
                        asset_url=asset_url,
                        header_data=header_data,
                    )
                else:
                    logger.debug(f"Not optimizing, unsupported mime type: {mime_type}")

        return self._download_from_online(asset_url=asset_url)
