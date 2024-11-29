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
