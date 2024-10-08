from pathlib import Path

import pytest

from libretexts2zim.utils import get_asset_path_from_url


@pytest.mark.parametrize(
    "online_url, already_used_paths, expected_path",
    [
        pytest.param("style.css", [], "style.css", id="simple"),
        pytest.param("folder/style.css", [], "folder/style.css", id="folder"),
        pytest.param("style.css", ["style.css"], "style_1.css", id="conflict"),
        pytest.param(
            "folder/style.css",
            ["folder/style.css"],
            "folder/style_1.css",
            id="folder_conflict",
        ),
        pytest.param(
            "folder/style.css",
            ["style.css"],
            "folder/style.css",
            id="folder_noconflict",
        ),
        pytest.param(
            "../folder/style.css", [], "folder/style.css", id="relative_parent"
        ),
        pytest.param("./folder/style.css", [], "folder/style.css", id="relative_same"),
        pytest.param("/folder/style.css", [], "folder/style.css", id="absolute"),
        pytest.param(
            "/folder/style.css",
            ["folder/style.css"],
            "folder/style_1.css",
            id="conflict_absolute",
        ),
        pytest.param(
            "https://www.acme.com/folder/style.css", [], "folder/style.css", id="full"
        ),
        pytest.param(
            "//www.acme.com/folder/style.css",
            [],
            "folder/style.css",
            id="full_no_scheme",
        ),
        pytest.param(
            "style.css?q=value#fragment",
            [],
            "style.css",
            id="query_string_and_fragment",
        ),
    ],
)
def test_get_asset_path_from_url(
    online_url: str, already_used_paths: list[str], expected_path: str
):
    assert get_asset_path_from_url(
        online_url, [Path(path) for path in already_used_paths]
    ) == Path(expected_path)
