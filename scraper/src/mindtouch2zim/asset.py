from io import BytesIO
from typing import NamedTuple

import backoff
from kiwixstorage import KiwixStorage, NotFoundError
from pif import get_public_ip
from PIL import Image
from requests import HTTPError
from requests.exceptions import RequestException
from zimscraperlib.download import stream_file
from zimscraperlib.image.optimization import optimize_webp
from zimscraperlib.image.presets import WebpMedium
from zimscraperlib.image.transformation import resize_image
from zimscraperlib.rewriting.url_rewriting import HttpUrl, ZimPath
from zimscraperlib.zim import Creator

from mindtouch2zim.constants import logger, web_session
from mindtouch2zim.utils import add_item_for, backoff_hdlr

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


class AssetDetails(NamedTuple):
    urls: set[HttpUrl]
    always_fetch_online: bool


class AssetProcessor:

    def __init__(
        self, s3_url_with_credentials: str | None, *, resize_images: bool
    ) -> None:
        self.s3_url_with_credentials = s3_url_with_credentials
        self._setup_s3()
        self.resize_images = resize_images

    def process_asset(
        self,
        asset_path: ZimPath,
        asset_details: AssetDetails,
        creator: Creator,
    ):
        logger.debug(f"Processing asset for {asset_path}")
        try:
            self._process_asset_internal(
                asset_path=asset_path, asset_details=asset_details, creator=creator
            )
        except Exception as exc:
            logger.exception("Error occured", exc)
            raise

    @backoff.on_exception(
        backoff.expo,
        RequestException,
        max_time=16,
        on_backoff=backoff_hdlr,
    )
    def _process_asset_internal(
        self,
        asset_path: ZimPath,
        asset_details: AssetDetails,
        creator: Creator,
    ):
        for asset_url in asset_details.urls:
            try:
                asset_content = self.get_asset_content(
                    asset_path=asset_path,
                    asset_url=asset_url,
                    always_fetch_online=asset_details.always_fetch_online,
                )
                logger.debug(
                    f"Adding {asset_url.value} to {asset_path.value} in the ZIM"
                )
                add_item_for(
                    creator=creator,
                    path="content/" + asset_path.value,
                    content=asset_content.getvalue(),
                )
                break  # file found and added
            except HTTPError as exc:
                # would make more sense to be a warning, but this is just too
                # verbose, at least on geo.libretexts.org many assets are just
                # missing
                logger.debug(f"Ignoring {asset_path.value} due to {exc}")

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
        if not self.s3_storage:
            raise Exception("s3 storage must be set")
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
        if not self.s3_storage:
            raise Exception("s3 storage must be set")
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

    def _setup_s3(self):
        if not self.s3_url_with_credentials:
            return
        logger.info("testing S3 Optimization Cache credentials")
        self.s3_storage = KiwixStorage(self.s3_url_with_credentials)
        if not self.s3_storage.check_credentials(  # pyright: ignore[reportUnknownMemberType]
            list_buckets=True, bucket=True, write=True, read=True, failsafe=True
        ):
            logger.error("S3 cache connection error testing permissions.")
            logger.error(
                f"  Server: {self.s3_storage.url.netloc}"  # pyright: ignore[reportUnknownMemberType]
            )
            logger.error(
                f"  Bucket: {self.s3_storage.bucket_name}"  # pyright: ignore[reportUnknownMemberType]
            )
            logger.error(
                f"  Key ID: {self.s3_storage.params.get('keyid')}"  # pyright: ignore[reportUnknownMemberType]
            )
            logger.error(f"  Public IP: {get_public_ip()}")
            raise Exception("Invalid S3 credentials")