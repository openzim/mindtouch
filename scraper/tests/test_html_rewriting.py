import pytest
from zimscraperlib.rewriting.html import HtmlRewriter
from zimscraperlib.rewriting.url_rewriting import (
    HttpUrl,
    ZimPath,
)

from mindtouch2zim.client import LibraryPage
from mindtouch2zim.errors import UnsupportedHrefSrcError, UnsupportedTagError
from mindtouch2zim.html_rewriting import HtmlUrlsRewriter


@pytest.fixture()
def url_rewriter() -> HtmlUrlsRewriter:
    return HtmlUrlsRewriter(
        library_url="https://www.acme.com",
        page=LibraryPage(id="123", title="a page", path="A_Page"),
        existing_zim_paths={
            ZimPath("www.acme.com/existing.html"),
        },
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


@pytest.mark.parametrize(
    "source_html, expected_html, expected_items_to_download",
    [
        pytest.param(
            '<iframe src="https://www.youtube.com/embed/sQaEthBmZB0?vq=hd1080" '
            'frameborder="0" allowfullscreen="true" '
            'style="width: 100%; height: 100%; position: absolute"></iframe>',
            '<a href="https://www.youtube.com/embed/sQaEthBmZB0?vq=hd1080" '
            'target="_blank">'
            '<div class="zim-removed-video">'
            '<img src="content/i.ytimg.com.fuzzy.replayweb.page/'
            'vi/sQaEthBmZB0/thumbnail.jpg"></img>'
            "</div>"
            "</a>"
            '<iframe style="display: none;"></iframe>',
            {
                ZimPath(
                    "i.ytimg.com.fuzzy.replayweb.page/vi/sQaEthBmZB0/thumbnail.jpg"
                ): {HttpUrl("https://i.ytimg.com/vi/sQaEthBmZB0/hqdefault.jpg")}
            },
            id="youtube",
        ),
        pytest.param(
            '<iframe src="https://player.vimeo.com/video/153300296" '
            'frameborder="0" allowfullscreen="true" '
            'style="width: 100%; height: 100%; position: absolute"></iframe>',
            '<a href="https://player.vimeo.com/video/153300296" '
            'target="_blank">'
            '<div class="zim-removed-video">'
            '<img src="content/i.vimeocdn.com/video/553546340-'
            '35aa6d23b04e9bdaf254c3cfc4da56bcfd7ff3f75a517c485536082edbf547dd-d_640">'
            "</img>"
            "</div>"
            "</a>"
            '<iframe style="display: none;"></iframe>',
            {
                ZimPath(
                    "i.vimeocdn.com/video/553546340-"
                    "35aa6d23b04e9bdaf254c3cfc4da56bcfd7ff3f75a517c485536082edbf547dd-"
                    "d_640"
                ): {
                    HttpUrl(
                        "https://i.vimeocdn.com/video/553546340-"
                        "35aa6d23b04e9bdaf254c3cfc4da56bcfd7ff3f75a517c485536082e"
                        "dbf547dd-d_640"
                    )
                }
            },
            id="vimeo",
        ),
        pytest.param(
            '<iframe src="https://www.acme.com/embed/sQaEthBmZB0?vq=hd1080" '
            'frameborder="0" allowfullscreen="true" '
            'style="width: 100%; height: 100%; position: absolute"></iframe>',
            "This content is not inside the ZIM. View content online at "
            '<a href="https://www.acme.com/embed/sQaEthBmZB0?vq=hd1080" '
            'target="_blank">'
            "<div>https://www.acme.com/embed/sQaEthBmZB0?vq=hd1080</div>"
            "</a>"
            '<iframe style="display: none;"></iframe>',
            {},
            id="unhandled",
        ),
    ],
)
def test_html_iframe_rewriting(
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


def test_html_picture_rewriting(html_rewriter: HtmlRewriter):
    with pytest.raises(UnsupportedTagError):
        html_rewriter.rewrite("<picture>")


def test_html_script_rewriting(html_rewriter: HtmlRewriter):
    with pytest.raises(UnsupportedHrefSrcError):
        html_rewriter.rewrite("<script src='script.js'>")


@pytest.mark.parametrize(
    "source_html, expected_html, expected_items_to_download",
    [
        pytest.param(
            '<a href="https://www.acme.com/existing.html">Page</a>',
            '<a href="#/existing.html">Page</a>',
            {},
            id="internal_absolute",
        ),
        pytest.param(
            '<a href="/existing.html">Page 1</a>',
            '<a href="#/existing.html">Page 1</a>',
            {},
            id="internal_root",
        ),
        pytest.param(
            '<a href="../existing.html">Page 1</a>',
            '<a href="#/existing.html">Page 1</a>',
            {},
            id="internal_relative",
        ),
        pytest.param(
            '<a href="../outside.html">Page 1</a>',
            '<a href="https://www.acme.com/outside.html">Page 1</a>',
            {},
            id="external_relative",
        ),
        pytest.param(
            '<a href="https://www.foo.bar/index.html">Page 2</a>',
            '<a href="https://www.foo.bar/index.html">Page 2</a>',
            {},
            id="external",
        ),
    ],
)
def test_html_href_rewriting(
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
