from pathlib import Path

import pytest

from libretexts2zim.css import CssProcessor


@pytest.mark.parametrize(
    "css_document_content, css_document_url, expected_assets, expected_css_rewritten",
    [
        pytest.param(
            """
body {
    background-image: url('https://example.com/image.jpg');
}
""",
            "https://www.acme.com/styles/main.css",
            {"https://example.com/image.jpg": Path("/content/css_assets/image.jpg")},
            """
body {
    background-image: url("css_assets/image.jpg");
}
""",
            id="basic_full",
        ),
        pytest.param(
            """
body {
    background-image: url('/assets/image.jpg');
}
""",
            "https://www.acme.com/styles/main.css",
            {
                "https://www.acme.com/assets/image.jpg": Path(
                    "/content/css_assets/assets/image.jpg"
                )
            },
            """
body {
    background-image: url("css_assets/assets/image.jpg");
}
""",
            id="basic_absolute",
        ),
        pytest.param(
            """
body {
    background-image: url('../image.jpg');
}
""",
            "https://www.acme.com/styles/main.css",
            {"https://www.acme.com/image.jpg": Path("/content/css_assets/image.jpg")},
            """
body {
    background-image: url("css_assets/image.jpg");
}
""",
            id="basic_relative1",
        ),
        pytest.param(
            """
body {
    background-image: url('./image.jpg');
}
""",
            "https://www.acme.com/styles/main.css",
            {
                "https://www.acme.com/styles/image.jpg": Path(
                    "/content/css_assets/styles/image.jpg"
                )
            },
            """
body {
    background-image: url("css_assets/styles/image.jpg");
}
""",
            id="basic_relative2",
        ),
        pytest.param(
            """
@import url("print.css")
""",
            "https://www.acme.com/styles/main.css",
            {
                "https://www.acme.com/styles/print.css": Path(
                    "/content/css_assets/styles/print.css"
                )
            },
            """
@import url("css_assets/styles/print.css")
;""",
            id="import",
        ),
        pytest.param(
            """
body {
    background-image: url('https://example.com/image.jpg'), url('/assets/image.jpg');
}
""",
            "https://www.acme.com/styles/main.css",
            {
                "https://example.com/image.jpg": Path("/content/css_assets/image.jpg"),
                "https://www.acme.com/assets/image.jpg": Path(
                    "/content/css_assets/assets/image.jpg"
                ),
            },
            """
body {
    background-image: url("css_assets/image.jpg"), url("css_assets/assets/image.jpg");
}
""",
            id="two_backgrounds",
        ),
        pytest.param(
            """
.ui-widget-content {
    background: #fff url("https://example.com/banner2.png") 50% 50% repeat-x;
    color: #222;
}
""",
            "https://www.acme.com/styles/main.css",
            {
                "https://example.com/banner2.png": Path(
                    "/content/css_assets/banner2.png"
                ),
            },
            """
.ui-widget-content {
    background: #fff url("css_assets/banner2.png") 50% 50% repeat-x;
    color: #222;
}
""",
            id="complex_1",
        ),
        pytest.param(
            """
@font-face {
    font-display: swap;
    font-family: icomoon;
    font-style: normal;
    font-weight: 400;
    src: url(/@style/icons/icomoon.eot?_=ae123bc);
    src: url(/@style/icons/icomoon.eot?_=ae123bc#iefix)
        format("embedded-opentype"),
        url(/@style/icons/icomoon.woff?_=ae123bc)
        format("woff"),
        url(/@style/icons/icomoon.ttf?_=ae123bc)
        format("truetype"),
        url(/@style/icons/icomoon.svg?_=ae123bc#icomoon)
        format("svg");
}
""",
            "https://www.acme.com/styles/main.css",
            {
                "https://www.acme.com/@style/icons/icomoon.eot?_=ae123bc": Path(
                    "/content/css_assets/@style/icons/icomoon.eot"
                ),
                "https://www.acme.com/@style/icons/icomoon.eot?_=ae123bc#iefix": Path(
                    "/content/css_assets/@style/icons/icomoon_1.eot"
                ),
                "https://www.acme.com/@style/icons/icomoon.woff?_=ae123bc": Path(
                    "/content/css_assets/@style/icons/icomoon.woff"
                ),
                "https://www.acme.com/@style/icons/icomoon.ttf?_=ae123bc": Path(
                    "/content/css_assets/@style/icons/icomoon.ttf"
                ),
                "https://www.acme.com/@style/icons/icomoon.svg?_=ae123bc#icomoon": Path(
                    "/content/css_assets/@style/icons/icomoon.svg"
                ),
            },
            """
@font-face {
    font-display: swap;
    font-family: icomoon;
    font-style: normal;
    font-weight: 400;
    src: url(css_assets/@style/icons/icomoon.eot);
    src: url(css_assets/@style/icons/icomoon_1.eot)
        format("embedded-opentype"),
        url(css_assets/@style/icons/icomoon.woff)
        format("woff"),
        url(css_assets/@style/icons/icomoon.ttf)
        format("truetype"),
        url(css_assets/@style/icons/icomoon.svg)
        format("svg");
}
""",
            id="complex_2",
        ),
        pytest.param(
            """
body {
    background-image: url('https://example.com/image.jpg');
}
div {
    background-image: url('https://example.com/image.jpg');
}
""",
            "https://www.acme.com/styles/main.css",
            {"https://example.com/image.jpg": Path("/content/css_assets/image.jpg")},
            """
body {
    background-image: url("css_assets/image.jpg");
}
div {
    background-image: url("css_assets/image.jpg");
}
""",
            id="duplicate",
        ),
        pytest.param(
            """
.magicBg {
background-image: url(data:image/gif;base64,R0lGODlhAQBkAPcAAAAAAAEBAQICAgMDAwQEBAUFBQ)
}
""",
            "https://www.acme.com/styles/main.css",
            {},
            """
.magicBg {
background-image: url(data:image/gif;base64,R0lGODlhAQBkAPcAAAAAAAEBAQICAgMDAwQEBAUFBQ)
}
""",
            id="ignore_data",
        ),
        pytest.param(
            """
div {
    background-image: url('https://example.com/image.jpg');
}
}/*]]>*/
""",
            "https://www.acme.com/styles/main.css",
            {"https://example.com/image.jpg": Path("/content/css_assets/image.jpg")},
            """
div {
    background-image: url("css_assets/image.jpg");
}
""",
            id="ignore_parsing_error",
        ),
    ],
)
def test_css_processor_single_doc(
    css_document_content: str,
    css_document_url: str,
    expected_assets: dict[str, Path],
    expected_css_rewritten: str,
):
    processor = CssProcessor()
    result = processor.process(css_document_url, css_document_content.encode())
    assert processor.css_assets == expected_assets
    assert result == expected_css_rewritten


def test_css_processor_multiple_docs():
    doc1 = """
body {
    background-image: url('https://example.com/image.jpg'), url('https://example.com/image.jpg?_=test1');
}
"""
    doc2 = """
div {
    background-image: url('https://example.com/image.jpg'), url('https://example.com/image.jpg?_=test2');
}
"""
    css_1_url = "https://www.acme.com/styles/main1.css"
    css_2_url = "https://www.acme.com/styles/main2.css"
    processor = CssProcessor()

    # process a first document
    result1 = processor.process(css_original_url=css_1_url, css_content=doc1.encode())

    assert processor.css_assets == {
        "https://example.com/image.jpg": Path("/content/css_assets/image.jpg"),
        "https://example.com/image.jpg?_=test1": Path(
            "/content/css_assets/image_1.jpg"
        ),
    }

    assert (
        result1
        == """
body {
    background-image: url("css_assets/image.jpg"), url("css_assets/image_1.jpg");
}
"""
    )

    # process a second document
    result2 = processor.process(css_original_url=css_2_url, css_content=doc2.encode())

    assert processor.css_assets == {
        "https://example.com/image.jpg": Path("/content/css_assets/image.jpg"),
        "https://example.com/image.jpg?_=test1": Path(
            "/content/css_assets/image_1.jpg"
        ),
        "https://example.com/image.jpg?_=test2": Path(
            "/content/css_assets/image_2.jpg"
        ),
    }

    assert (
        result2
        == """
div {
    background-image: url("css_assets/image.jpg"), url("css_assets/image_2.jpg");
}
"""
    )
