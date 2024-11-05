from pathlib import Path

import pytest

from mindtouch2zim.utils import get_asset_path_from_url, is_better_srcset_descriptor


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


@pytest.mark.parametrize(
    "new_descriptor, current_best_descriptor, expected_result",
    [
        pytest.param(None, None, False, id="all_none"),
        pytest.param(None, "1024w", False, id="new_none"),
        pytest.param("1024w", None, True, id="current_none"),
        pytest.param("1024w", "640w", True, id="w_current_better"),
        pytest.param("640w", "1024w", False, id="w_current_worse"),
        pytest.param("1024w", "1024w", False, id="w_equal"),
        pytest.param("3x", "2x", True, id="x_current_better"),
        pytest.param("2x", "3x", False, id="x_current_worse"),
        pytest.param("3x", "3x", False, id="x_equal"),
        pytest.param("3x", "3x", False, id="x_w_mixed1"),
        pytest.param("1024w", "3x", False, id="x_w_mixed1"),
        pytest.param("3x", "1024w", False, id="x_w_mixed2"),
        pytest.param("3w", "1024x", False, id="x_w_mixed3"),
        pytest.param("1024x", "3w", False, id="x_w_mixed4"),
    ],
)
def test_is_better_srcset_descriptor(
    new_descriptor: str | None,
    current_best_descriptor: str | None,
    *,
    expected_result: bool,
):
    assert (
        is_better_srcset_descriptor(
            new_descriptor=new_descriptor,
            current_best_descriptor=current_best_descriptor,
        )
        == expected_result
    )
