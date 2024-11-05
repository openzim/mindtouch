import pytest
from zimscraperlib.rewriting.html import HtmlRewriter
from zimscraperlib.rewriting.url_rewriting import (
    HttpUrl,
    ZimPath,
)

from mindtouch2zim.client import LibraryPage
from mindtouch2zim.html_rewriting import HtmlUrlsRewriter


@pytest.fixture()
def url_rewriter() -> HtmlUrlsRewriter:
    return HtmlUrlsRewriter(
        library_url="https://www.acme.com",
        page=LibraryPage(id="123", title="a page", path="A_Page"),
        existing_zim_paths=set(),
    )


@pytest.fixture()
def html_rewriter(url_rewriter: HtmlUrlsRewriter) -> HtmlRewriter:
    return HtmlRewriter(
        url_rewriter, pre_head_insert=None, post_head_insert=None, notify_js_module=None
    )


@pytest.mark.parametrize(
    "source_html, expected_html, expected_items_to_download",
    [
        pytest.param(
            '<img src="https://www.foo.bar/image1.png"></img>',
            '<img src="content/www.foo.bar/image1.png"></img>',
            {
                ZimPath("www.foo.bar/image1.png"): {
                    HttpUrl("https://www.foo.bar/image1.png")
                }
            },
            id="simple",
        ),
        pytest.param(
            '<img src="https://www.foo.bar/image1.png" '
            'srcset="https://www.foo.bar/image2.png"></img>',
            '<img src="content/www.foo.bar/image2.png"></img>',
            {
                ZimPath("www.foo.bar/image2.png"): {
                    HttpUrl("https://www.foo.bar/image2.png")
                }
            },
            id="simple_srcset",
        ),
        pytest.param(
            '<img srcset="https://www.foo.bar/image2.png 1024w"></img>',
            '<img src="content/www.foo.bar/image2.png"></img>',
            {
                ZimPath("www.foo.bar/image2.png"): {
                    HttpUrl("https://www.foo.bar/image2.png")
                }
            },
            id="simple_srcset_no_src",
        ),
        pytest.param(
            '<img srcset="https://www.foo.bar/image1.png 640w, '
            'https://www.foo.bar/image2.png 1024w"></img>',
            '<img src="content/www.foo.bar/image2.png"></img>',
            {
                ZimPath("www.foo.bar/image2.png"): {
                    HttpUrl("https://www.foo.bar/image2.png")
                }
            },
            id="simple_srcset_2_no_src",
        ),
        pytest.param(
            '<img src="https://www.foo.bar/image3.png" '
            'srcset="https://www.foo.bar/image1.png 640w, '
            'https://www.foo.bar/ima ge2.png 1024w" '
            'sizes="(max-width: 300px) 85vw, 300px" '
            'alt="Image"></img>',
            '<img alt="Image" src="content/www.foo.bar/ima%20ge2.png"></img>',
            {
                ZimPath("www.foo.bar/ima ge2.png"): {
                    HttpUrl("https://www.foo.bar/ima ge2.png")
                }
            },
            id="simple_srcset_2",
        ),
    ],
)
def test_html_img_rewriting(
    url_rewriter: HtmlUrlsRewriter,
    html_rewriter: HtmlRewriter,
    source_html: str,
    expected_html: str,
    expected_items_to_download: dict[ZimPath, set[HttpUrl]],
):
    rewritten = html_rewriter.rewrite(source_html)
    assert rewritten.content == expected_html
    assert rewritten.title == ""
    assert url_rewriter.items_to_download == expected_items_to_download
