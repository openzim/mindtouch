import pytest

from mindtouch2zim.client import (
    _get_soup,  # pyright: ignore[reportPrivateUsage]
    _get_welcome_text_from_home,  # pyright: ignore[reportPrivateUsage]
)


@pytest.mark.parametrize(
    "content,expected",
    [
        pytest.param(
            (
                r"""<section class="mt-content-container"><p>Welcome to the """
                r"""Geosciences Library</p></section>"""
            ),
            ["Welcome to the Geosciences Library"],
            id="simplest",
        ),
        pytest.param(
            (
                r"""<section class="mt-content-container"><p></p><p>Welcome to the """
                r"""Geosciences Library</p><p></p></section>"""
            ),
            ["Welcome to the Geosciences Library"],
            id="simple_with_empty",
        ),
        pytest.param(
            (
                r"""<section class="mt-content-container"><p>Welcome to the """
                r"""Geosciences Library</p><p>This is a second paragraph</p>"""
                r"""</section>"""
            ),
            ["Welcome to the Geosciences Library", "This is a second paragraph"],
            id="two_paragraphs",
        ),
        pytest.param(
            (
                r"""<section class="mt-content-container"><p>Welcome to the """
                r"""<a href="#">Geosciences</a> Library</p></section>"""
            ),
            ["Welcome to the Geosciences Library"],
            id="simply_with_link",
        ),
        pytest.param(
            (
                r"""<section class="mt-content-container"><p>Welcome to the """
                r"""Geosciences Library</p><div>Hello</div>"""
                r"""<span>Hello</span></section>"""
            ),
            ["Welcome to the Geosciences Library"],
            id="simple_with_other_tags",
        ),
    ],
)
def test_get_welcome_text_from_home(content: str, expected: str):
    assert _get_welcome_text_from_home(_get_soup(content)) == expected
