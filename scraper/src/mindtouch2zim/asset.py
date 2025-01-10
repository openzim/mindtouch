import math
import mimetypes
import threading
from functools import partial
from io import BytesIO
from typing import NamedTuple
from urllib.parse import urlsplit

import backoff
from kiwixstorage import (  # pyright: ignore[reportMissingTypeStubs]
    KiwixStorage,
    NotFoundError,
)
from pif import (  # pyright: ignore[reportMissingTypeStubs]
    get_public_ip,  # pyright: ignore[reportUnknownVariableType]
)
from PIL import Image
from requests.exceptions import RequestException
from resizeimage import resizeimage  # pyright: ignore[reportMissingTypeStubs]
from zimscraperlib.image.optimization import optimize_webp
from zimscraperlib.image.presets import WebpMedium
from zimscraperlib.rewriting.url_rewriting import HttpUrl, ZimPath
from zimscraperlib.zim import Creator

from mindtouch2zim.context import Context
from mindtouch2zim.download import stream_file
from mindtouch2zim.errors import (
    KnownBadAssetFailedError,
    S3CacheError,
    S3InvalidCredentialsError,
)
from mindtouch2zim.utils import backoff_hdlr

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

context = Context.get()
logger = context.logger


class HeaderData(NamedTuple):
    ident: str  # ~version~ of the URL data to use for comparisons
    content_type: str | None


class AssetDetails(NamedTuple):
    asset_urls: set[HttpUrl]
    used_by: set[str]
    always_fetch_online: bool
    kind: str | None

    @property
    def get_usage_repr(self) -> str:
        """Returns a representation of asset usage, typically for logs"""
        if len(self.used_by) == 0:
            return ""
        return f' used by {", ".join(self.used_by)}'


class AssetManager:
    """Class responsible to manage a list of assets to download"""

    def __init__(self) -> None:
        self.assets: dict[ZimPath, AssetDetails] = {}

    def add_asset(
        self,
        asset_path: ZimPath,
        asset_url: HttpUrl,
        used_by: str,
        kind: str | None,
        *,
        always_fetch_online: bool,
    ):
        """Add a new asset to download

        asset_path: target path inside the ZIM
        asset_url: URL where the asset can be downloaded
        used_by: string explaining (mostly for debug purposes) where the asset is used
          (typically on which page)
        kind: kind of asset if we know it ; for instance "img" is used to not rely only
          on returned mime type to decide if we should optimize it or not
        always_fetch_online: if False, the asset may be cached on S3 ; if True, it is
          always fetch online
        """
        if asset_path not in self.assets:
            self.assets[asset_path] = AssetDetails(
                asset_urls={asset_url},
                used_by={used_by},
                kind=kind,
                always_fetch_online=always_fetch_online,
            )
            return
        current_asset = self.assets[asset_path]
        if current_asset.kind != kind:
            logger.warning(
                f"Conflicting kind found for asset at {asset_path} already used by "
                f"{current_asset.get_usage_repr}; current kind is "
                f"'{current_asset.kind}';new kind '{kind}' from {asset_url} used by "
                f"{used_by} will be ignored"
            )
        if current_asset.always_fetch_online != always_fetch_online:
            logger.warning(
                f"Conflicting always_fetch_online found for asset at {asset_path} "
                f"already used by {current_asset.get_usage_repr}; current "
                f"always_fetch_online is '{current_asset.always_fetch_online}';"
                f"new always_fetch_online '{always_fetch_online}' from {asset_url} used"
                f" by {used_by} will be ignored"
            )
        current_asset.used_by.add(used_by)
        current_asset.asset_urls.add(asset_url)


class AssetProcessor:

    def __init__(
        self,
    ) -> None:
        self._setup_s3()
        self.bad_assets_count = 0
        self.lock = threading.Lock()

    def process_asset(
        self,
        asset_path: ZimPath,
        asset_details: AssetDetails,
        creator: Creator,
    ):
        """Download and add to the ZIM a given asset (image, ...)"""
        for asset_url in asset_details.asset_urls:
            try:
                context.current_thread_workitem = (
                    f"asset from {asset_url.value}{asset_details.get_usage_repr}"
                )
                asset_content = self.get_asset_content(
                    asset_path=asset_path,
                    asset_url=asset_url,
                    always_fetch_online=asset_details.always_fetch_online,
                    kind=asset_details.kind,
                )
                logger.debug(f"Adding asset to {asset_path.value} in the ZIM")
                creator.add_item_for(
                    path="content/" + asset_path.value,
                    content=asset_content.getvalue(),
                )
                break  # file found and added
            except RuntimeError:
                # RuntimeError exceptions comes from the libzim usually and they must be
                # fatal errors
                raise
            except KnownBadAssetFailedError as exc:
                logger.debug(f"Ignoring known bad asset: {exc}")
            except Exception as exc:
                # all other exceptions (not only RequestsException) lead to an increase
                # of bad_assets_count, because we have no idea what could go wrong here
                # and limit and bad assets threshold should be correct in production,
                # or ignored at own user risk
                with self.lock:
                    self.bad_assets_count += 1
                    log_message = (
                        "Exception while processing "
                        f"{context.current_thread_workitem}: {exc}"
                    )
                    if (
                        context.bad_assets_threshold >= 0
                        and self.bad_assets_count > context.bad_assets_threshold
                    ):
                        logger.error(log_message)
                        raise OSError(  # noqa: B904
                            f"Asset failure threshold ({context.bad_assets_threshold}) "
                            "reached, stopping execution"
                        )
                    else:
                        logger.warning(log_message)

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

        if context.s3_url_with_credentials:
            if s3_data := self._download_from_s3_cache(s3_key=s3_key, meta=meta):
                if len(s3_data.getvalue()) > 0:
                    logger.debug("Fetched directly from S3 cache")
                    return s3_data  # found in cache

        logger.debug("Fetching from online")
        unoptimized = self._download_from_online(asset_url=asset_url)

        logger.debug("Optimizing")
        optimized = BytesIO()
        with Image.open(unoptimized) as image:
            if image.width * image.height <= context.maximum_image_pixels:
                image.save(optimized, format="WEBP")
            else:
                resizeimage.resize_width(  # pyright: ignore[reportUnknownMemberType]
                    image,
                    int(
                        math.sqrt(
                            context.maximum_image_pixels * image.width / image.height
                        )
                    ),
                ).save(optimized, format="WEBP")
        del unoptimized

        optimize_webp(src=optimized, options=WEBP_OPTIONS)

        if context.s3_url_with_credentials:
            # upload optimized to S3
            logger.debug("Uploading to S3")
            self._upload_to_s3_cache(
                s3_key=s3_key,
                meta=meta,
                asset_content=BytesIO(
                    optimized.getvalue()
                ),  # use a copy because it will be "consumed" by botocore
            )

        return optimized

    def _download_from_s3_cache(
        self, s3_key: str, meta: dict[str, str]
    ) -> BytesIO | None:
        if not self.s3_storage:
            raise AttributeError("s3 storage must be set")
        try:
            asset_content = BytesIO()
            self.s3_storage.download_matching_fileobj(  # pyright: ignore[reportUnknownMemberType]
                s3_key, asset_content, meta=meta
            )
            return asset_content
        except NotFoundError:
            return None
        except Exception as exc:
            raise S3CacheError(f"Failed to download {s3_key} from S3 cache") from exc

    def _upload_to_s3_cache(
        self, s3_key: str, meta: dict[str, str], asset_content: BytesIO
    ):
        if not self.s3_storage:
            raise AttributeError("s3 storage must be set")
        try:
            self.s3_storage.upload_fileobj(  # pyright: ignore[reportUnknownMemberType]
                key=s3_key, fileobj=asset_content, meta=meta
            )
        except Exception as exc:
            raise S3CacheError(f"Failed to upload {s3_key} to S3 cache") from exc

    def _download_from_online(self, asset_url: HttpUrl) -> BytesIO:
        """Download whole content from online server with retry from scraperlib"""

        asset_content = BytesIO()
        stream_file(
            asset_url.value,
            byte_stream=asset_content,
        )
        return asset_content

    def _get_mime_type(
        self,
        header_data: HeaderData,
        asset_url: HttpUrl,
        kind: str | None,
    ) -> str | None:
        if header_data.content_type:
            mime_type = header_data.content_type.split(";")[0].strip()
        else:
            mime_type = None
        if (
            mime_type is None or mime_type == "application/octet-stream"
        ) and kind == "img":
            # try to source mime_type from file extension
            mime_type, _ = mimetypes.guess_type(urlsplit(asset_url.value).path)
        return mime_type

    @backoff.on_exception(
        partial(backoff.expo, base=3, factor=2),
        RequestException,
        max_time=30,  # secs
        on_backoff=backoff_hdlr,
    )
    def get_asset_content(
        self,
        asset_path: ZimPath,
        asset_url: HttpUrl,
        kind: str | None,
        *,
        always_fetch_online: bool,
    ) -> BytesIO:
        """Download of a given asset, optimize if needed, or download from S3 cache"""

        try:
            if not always_fetch_online:
                header_data = self._get_header_data_for(asset_url)
                mime_type = self._get_mime_type(
                    header_data=header_data, asset_url=asset_url, kind=kind
                )
                if mime_type and mime_type in SUPPORTED_IMAGE_MIME_TYPES:
                    return self._get_image_content(
                        asset_path=asset_path,
                        asset_url=asset_url,
                        header_data=header_data,
                    )
                else:
                    logger.debug(
                        f"Not optimizing, unsupported mime type: {mime_type} for "
                        f"{context.current_thread_workitem}"
                    )

            return self._download_from_online(asset_url=asset_url)
        except RequestException as exc:
            # check if the failing download match known bad assets regex early, and if
            # so raise a custom exception to escape backoff (always important to try
            # once even if asset is expected to not work, but no need to loose time on
            # retrying assets which are expected to be bad)
            if context.bad_assets_regex and context.bad_assets_regex.findall(
                asset_url.value
            ):
                raise KnownBadAssetFailedError(exc) from exc
            raise

    def _setup_s3(self):
        if not context.s3_url_with_credentials:
            return
        logger.info("testing S3 Optimization Cache credentials")
        self.s3_storage = KiwixStorage(context.s3_url_with_credentials)
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
            raise S3InvalidCredentialsError("Invalid S3 credentials")
