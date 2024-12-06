from io import BytesIO

import pytest

from mindtouch2zim.download import stream_file


@pytest.mark.parametrize(
    "url",
    [
        pytest.param(
            "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0a/ContrAA_series.jpg/512px-ContrAA_series.jpg",
            id="upload_wikimedia",
        ),
        pytest.param(
            "https://flexbooks.ck12.org/flx/show/THUMB_POSTCARD/image/user%3AY2sxMnNjaWVuY2VAY2sxMi5vcmc./98045-1359163835-22-2-IntPhysC-05-03-Weather-satellite.jpg",
            id="flexbooks",
        ),
    ],
)
def test_download(url: str):
    image = BytesIO()
    total_downloaded, _ = stream_file(url=url, byte_stream=image)
    assert total_downloaded > 0
    assert total_downloaded == len(image.getvalue())
