import pathlib
from typing import IO

import requests
import requests.structures
import urllib3
import zimscraperlib.__about__
import zimscraperlib.constants
from zimscraperlib.download import stream_file as stream_file_orig

from mindtouch2zim.constants import CONTACT_INFO, NAME, VERSION


def get_user_agent() -> str:
    return (
        f"{NAME}/{VERSION} ({CONTACT_INFO}) "
        f"{zimscraperlib.constants.NAME}/{zimscraperlib.__about__.__version__} "
        f"requests/{requests.__version__} "
        f"urllib3/{urllib3._version.__version__}"
    )


def stream_file(
    url: str,
    fpath: pathlib.Path | None = None,
    byte_stream: IO[bytes] | None = None,
    block_size: int | None = 1024,
    proxies: dict[str, str] | None = None,
    max_retries: int | None = 5,
    headers: dict[str, str] | None = None,
    session: requests.Session | None = None,
    *,
    only_first_block: bool | None = False,
) -> tuple[int, requests.structures.CaseInsensitiveDict[str]]:
    if headers:
        headers["User-Agent"] = get_user_agent()
    else:
        headers = {"User-Agent": get_user_agent()}
    return stream_file_orig(
        url=url,
        fpath=fpath,
        byte_stream=byte_stream,
        block_size=block_size,
        proxies=proxies,
        max_retries=max_retries,
        headers=headers,
        session=session,
        only_first_block=only_first_block,
    )
