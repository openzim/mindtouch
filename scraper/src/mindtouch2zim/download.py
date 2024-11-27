import pathlib
import re
from typing import IO

import requests
import requests.structures
from zimscraperlib.download import stream_file as stream_file_orig

from mindtouch2zim.context import Context

context = Context.get()

URL_NEEDING_FAKE_UA_REGEX = re.compile(r"https?:\/\/[a-zA-Z0-9_]+\.ck12\.org")


def stream_file(
    url: str,
    fpath: pathlib.Path | None = None,
    byte_stream: IO[bytes] | None = None,
    block_size: int | None = 1024,
    proxies: dict[str, str] | None = None,
    max_retries: int | None = 5,
    headers: dict[str, str] | None = None,
    *,
    only_first_block: bool | None = False,
) -> tuple[int, requests.structures.CaseInsensitiveDict[str]]:
    """Customized version of zimscraperlib stream_file

    We customize the User-Agent header, the session and the timeout
    """
    if headers is None:
        headers = {}
    headers["User-Agent"] = (
        # Fake browser UA needed for some hosts
        "Mozilla/5.0 Gecko/20100101 Firefox/132.0"
        if URL_NEEDING_FAKE_UA_REGEX.match(url)
        # Our WM compliant and nice UA (to prefer by default since it is the "reality")
        else context.wm_user_agent
    )
    return stream_file_orig(
        url=url,
        fpath=fpath,
        byte_stream=byte_stream,
        block_size=block_size,
        proxies=proxies,
        max_retries=max_retries,
        headers=headers,
        session=context.web_session,
        only_first_block=only_first_block,
        timeout=context.http_timeout_normal_seconds,
    )
