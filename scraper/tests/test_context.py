import pytest

from mindtouch2zim.context import Context
from mindtouch2zim.processor import context as processor_context

from . import CONTEXT_DEFAULTS


@pytest.fixture()
def context_defaults():
    return CONTEXT_DEFAULTS


def test_context_defaults():
    context = Context.get()
    assert context == processor_context  # check both objects are same
    assert context.assets_workers == 10
    assert (  # check getter logic
        context.wm_user_agent
        == "mindtouch2zim/0.1.0-dev0 (https://www.kiwix.org) zimscraperlib/5.0.0-dev0"
    )
    context.current_thread_workitem = "context 123"
    assert context.current_thread_workitem == "context 123"


def test_context_setup_again(context_defaults):
    settings = context_defaults.copy()
    settings["title"] = "A title"
    Context.setup(**settings)
    context = Context.get()
    assert context.title == "A title"
    assert context == processor_context  # check both objects are same


@pytest.mark.parametrize(
    "url, matching",
    [
        pytest.param("http://localhost:9999/foo", True, id="localhost1"),
        pytest.param("https://localhost/foo/bar.html", True, id="localhost2"),
        pytest.param("http://a.mtstatic.com/@cache/bar", True, id="mtstatic_cache"),
        pytest.param("https://a.mtstatic.com/@style/bar", True, id="mtstatic_style"),
        pytest.param("https://a.mtstatic.com/@stule/bar", False, id="mtstatic_stule"),
        pytest.param("https://aamtstaticacom/@style/bar", False, id="replace_dots"),
    ],
)
def test_context_bad_assets(url: str, *, matching: bool):
    matches = Context.bad_assets_regex.findall(url)
    assert matches if matching else not matches
