import threading
from typing import Any

from zimscraperlib.download import get_session

from mindtouch2zim.context import Context

CONTEXT_DEFAULTS: dict[str, Any] = {
    "web_session": get_session(),
    "tmp_folder": None,
    "cache_folder": None,
    "_current_thread_workitem": threading.local(),
    "library_url": None,
    "creator": None,
    "name": None,
    "title": None,
    "description": None,
}


# initialize a context since it is a requirement for most modules to load
Context.setup(**CONTEXT_DEFAULTS)
