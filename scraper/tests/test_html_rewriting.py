import pytest
from zimscraperlib.rewriting.html import HtmlRewriter
from zimscraperlib.rewriting.url_rewriting import (
    HttpUrl,
    ZimPath,
)

from mindtouch2zim.asset import AssetDetails, AssetManager
from mindtouch2zim.client import LibraryPage
from mindtouch2zim.html_rewriting import HtmlUrlsRewriter


@pytest.fixture()
def url_rewriter() -> HtmlUrlsRewriter:
    return HtmlUrlsRewriter(
        library_url="https://www.acme.com",
        page=LibraryPage(
            id="123",
            title="a page",
            path="A_Page",
            encoded_url="https://www.acme.com/A_Page",
        ),
        existing_zim_paths={
            ZimPath("www.acme.com/existing.html"),
            ZimPath("www.acme.com/existing.html?foo=bar"),
        },
        asset_manager=AssetManager(),
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
                ZimPath("www.foo.bar/image1.png"): AssetDetails(
                    asset_urls={HttpUrl("https://www.foo.bar/image1.png")},
                    used_by={"startup"},
                    always_fetch_online=False,
                    kind="img",
                )
            },
            id="simple",
        ),
        pytest.param(
            '<img src="https://www.foo.bar/image1.png" '
            'srcset="https://www.foo.bar/image2.png"></img>',
            '<img src="content/www.foo.bar/image2.png"></img>',
            {
                ZimPath("www.foo.bar/image2.png"): AssetDetails(
                    asset_urls={HttpUrl("https://www.foo.bar/image2.png")},
                    used_by={"startup"},
                    always_fetch_online=False,
                    kind="img",
                )
            },
            id="simple_srcset",
        ),
        pytest.param(
            '<img srcset="https://www.foo.bar/image2.png 1024w"></img>',
            '<img src="content/www.foo.bar/image2.png"></img>',
            {
                ZimPath("www.foo.bar/image2.png"): AssetDetails(
                    asset_urls={HttpUrl("https://www.foo.bar/image2.png")},
                    used_by={"startup"},
                    always_fetch_online=False,
                    kind="img",
                )
            },
            id="simple_srcset_no_src",
        ),
        pytest.param(
            '<img srcset="https://www.foo.bar/image1.png 640w, '
            'https://www.foo.bar/image2.png 1024w"></img>',
            '<img src="content/www.foo.bar/image2.png"></img>',
            {
                ZimPath("www.foo.bar/image2.png"): AssetDetails(
                    asset_urls={HttpUrl("https://www.foo.bar/image2.png")},
                    used_by={"startup"},
                    always_fetch_online=False,
                    kind="img",
                )
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
                ZimPath("www.foo.bar/ima ge2.png"): AssetDetails(
                    asset_urls={HttpUrl("https://www.foo.bar/ima ge2.png")},
                    used_by={"startup"},
                    always_fetch_online=False,
                    kind="img",
                )
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
    assert url_rewriter.asset_manager.assets == expected_items_to_download


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
                ): AssetDetails(
                    asset_urls={
                        HttpUrl("https://i.ytimg.com/vi/sQaEthBmZB0/hqdefault.jpg")
                    },
                    used_by={"startup"},
                    always_fetch_online=False,
                    kind="img",
                )
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
                ): AssetDetails(
                    asset_urls={
                        HttpUrl(
                            "https://i.vimeocdn.com/video/553546340-"
                            "35aa6d23b04e9bdaf254c3cfc4da56bcfd7ff3f75a517c485536082e"
                            "dbf547dd-d_640"
                        )
                    },
                    used_by={"startup"},
                    always_fetch_online=False,
                    kind="img",
                )
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
        pytest.param(
            '<iframe src="" srcdoc="Foo Bar"></iframe>',
            '<iframe src="" srcdoc="Foo Bar"></iframe>',
            {},
            id="empty_src",
        ),
        pytest.param(
            '<iframe srcdoc="Foo Bar"></iframe>',
            '<iframe srcdoc="Foo Bar"></iframe>',
            {},
            id="missing_src",
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
    assert url_rewriter.asset_manager.assets == expected_items_to_download


@pytest.mark.parametrize(
    "source_html, expected_html",
    [
        pytest.param("<script src='script.js'>", '<script src="">', id="script_src"),
        pytest.param(
            """<video class="mt-media" controls="controls" preload="auto">
  <source
    src="https://svs.gsfc.nasa.gov/vis/a000000/a003600/a003658/thermohaline_conveyor_30fps.mp4"
    type="video/mp4"
  />
  <embed
    class="mt-media"
    src="https://svs.gsfc.nasa.gov/vis/a000000/a003600/a003658/thermohaline_conveyor_30fps.mp4"
    autoplay="False"
    autostart="False"
    scale="tofit"
    wmode="opaque"
    allowfullscreen="true"
  />
</video>""",
            """<video class="mt-media" controls="controls" preload="auto">
  <source src="" type="video/mp4" />
  <embed class="mt-media" src="" autoplay="False" autostart="False" scale="tofit" """
            """wmode="opaque" allowfullscreen="true" />
</video>""",
            id="video_src",
        ),
        pytest.param(
            """<picture>
  <source srcset="/media/cc0-images/surfer-240-200.jpg" media="(orientation: xxx)" />
  <img src="/media/cc0-images/painted-hand-298-332.jpg" alt="" />
</picture>""",
            """<picture>
  <source srcset="" media="(orientation: xxx)" />
  <img alt="" src="content/www.acme.com/media/cc0-images/painted-hand-298-332.jpg"/>
</picture>""",
            id="picture_srcset",
        ),
        pytest.param(
            '<link href="/media/examples/link-element-example.css" rel="stylesheet" />',
            '<link href="" rel="stylesheet" />',
            id="link_href",
        ),
    ],
)
def test_html_unknown_src_href_rewriting(
    html_rewriter: HtmlRewriter, source_html: str, expected_html: str
):
    assert html_rewriter.rewrite(source_html).content == expected_html


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
        pytest.param(
            '<a href="https://www.acme.com/existing.html#67">Page 2</a>',
            '<a href="#/existing.html?anchor=67">Page 2</a>',
            {},
            id="internal_with_anchor",
        ),
        pytest.param(
            '<a href="https://www.acme.com/existing.html?foo=bar#67">Page 2</a>',
            '<a href="#/existing.html%3Ffoo%3Dbar?anchor=67">Page 2</a>',
            {},
            id="internal_with_anchor_and_query_string",
        ),
        pytest.param(
            '<a href="#67">Page 2</a>',
            '<a href="#/A_Page?anchor=67">Page 2</a>',
            {},
            id="anchor_only",
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
    assert url_rewriter.asset_manager.assets == expected_items_to_download
