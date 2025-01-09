import pytest
from zimscraperlib.rewriting.url_rewriting import HttpUrl, ZimPath

from mindtouch2zim.asset import AssetManager, AssetProcessor, HeaderData


@pytest.fixture()
def manager() -> AssetManager:
    manager = AssetManager()
    manager.add_asset(
        asset_path=ZimPath("some/asset"),
        asset_url=HttpUrl("https://www.acme.com/some/asset"),
        used_by="page somewhere",
        kind="some",
        always_fetch_online=True,
    )  # add an already present asset
    return manager


@pytest.fixture()
def processor() -> AssetProcessor:
    return AssetProcessor()


@pytest.mark.parametrize(
    "asset_path, asset_url, used_by, kind, always_fetch_online, expected_assets_len, "
    "expected_asset_path, expected_asset_urls, expected_used_bys, expected_kind, "
    "expected_always_fetch_online",
    [
        pytest.param(
            None,
            None,
            None,
            None,
            False,
            1,
            ZimPath("some/asset"),
            {HttpUrl("https://www.acme.com/some/asset")},
            {"page somewhere"},
            "some",
            True,
            id="case1",  # test default content
        ),
        pytest.param(
            ZimPath("foo/bar"),
            HttpUrl("https://www.acme.com/foo/bar"),
            "page foo at bar",
            "some",
            True,
            2,
            ZimPath("foo/bar"),
            {HttpUrl("https://www.acme.com/foo/bar")},
            {"page foo at bar"},
            "some",
            True,
            id="case2",  # add another different asset
        ),
        pytest.param(
            ZimPath("some/asset"),
            HttpUrl("https://www.acme.com/some/asset"),
            "page somewhere else",
            "some",
            False,
            1,
            ZimPath("some/asset"),
            {HttpUrl("https://www.acme.com/some/asset")},
            {"page somewhere", "page somewhere else"},
            "some",
            True,
            id="case3",  # add same asset at same URL used by different used_by
        ),
        pytest.param(
            ZimPath("some/asset"),
            HttpUrl("https://www.acme.com/some/asset?foo"),
            "page somewhere else",
            "some",
            True,
            1,
            ZimPath("some/asset"),
            {
                HttpUrl("https://www.acme.com/some/asset"),
                HttpUrl("https://www.acme.com/some/asset?foo"),
            },
            {"page somewhere", "page somewhere else"},
            "some",
            True,
            id="case4",  # add same asset at same URL used by different used_by and url
        ),
        pytest.param(
            ZimPath("some/asset"),
            HttpUrl("https://www.acme.com/some/asset"),
            "page somewhere else",
            "other",
            True,
            1,
            ZimPath("some/asset"),
            {HttpUrl("https://www.acme.com/some/asset")},
            {"page somewhere", "page somewhere else"},
            "some",
            True,
            id="case5",  # add same asset with different kind and fetch_online
        ),
    ],
)
def test_asset_manager(
    manager: AssetManager,
    asset_path: ZimPath | None,
    asset_url: HttpUrl | None,
    used_by: str | None,
    kind: str | None,
    *,
    always_fetch_online: bool,
    expected_assets_len: int,
    expected_asset_path: ZimPath | None,
    expected_asset_urls: set[HttpUrl],
    expected_used_bys: set[str],
    expected_kind: str | None,
    expected_always_fetch_online: bool,
):
    if asset_path and asset_url and used_by:
        manager.add_asset(
            asset_path=asset_path,
            asset_url=asset_url,
            used_by=used_by,
            kind=kind,
            always_fetch_online=always_fetch_online,
        )
    assert len(manager.assets) == expected_assets_len
    if expected_asset_path:
        assert expected_asset_path in manager.assets
        asset = manager.assets[expected_asset_path]
        assert asset.asset_urls == expected_asset_urls
        assert asset.used_by == expected_used_bys
        assert asset.kind == expected_kind
        assert asset.always_fetch_online == expected_always_fetch_online


@pytest.mark.parametrize(
    "header_content_type, kind, expected_mime_type",
    [
        pytest.param(
            " image/jpeg ;  fooo",
            "img",
            "image/jpeg",
            id="mimetype_in_content_type",
        ),
        pytest.param(
            "application/octet-stream",
            "img",
            "image/jpeg",
            id="bad_upstream_mimetype_but_img",
        ),
        pytest.param(
            "application/octet-stream",
            None,
            "application/octet-stream",
            id="bad_upstream_mimetype_not_img",
        ),
        pytest.param(
            None,
            "img",
            "image/jpeg",
            id="no_content_type_but_img",
        ),
        pytest.param(
            None,
            None,
            None,
            id="no_content_type_not_img",
        ),
    ],
)
def test_get_mime_type(
    header_content_type: str | None,
    expected_mime_type: str | None,
    kind: str | None,
    processor: AssetProcessor,
):

    assert (
        processor._get_mime_type(  # pyright: ignore[reportPrivateUsage]
            header_data=HeaderData(ident="foo", content_type=header_content_type),
            asset_url=HttpUrl(
                "https://www.acme.com/xenolith-of-diorite.jpg?revision=1"
            ),
            kind=kind,
        )
        == expected_mime_type
    )
