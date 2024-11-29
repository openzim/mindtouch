import os
import re
import tempfile
from pathlib import Path
from typing import Any

import pytest

from mindtouch2zim.context import Context
from mindtouch2zim.entrypoint import prepare_context

context = Context.get()


@pytest.fixture(scope="module")
def tmpdir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture(scope="module")
def good_cli_args() -> list[str]:
    return [
        "--name",
        "tests_en_library",
        "--creator",
        "bob",
        "--title",
        "a title",
        "--description",
        "a description",
        "--library-url",
        "http://geo.libretexts.org",
    ]


def test_entrypoint_valid(good_cli_args: list[str], tmpdir: str):
    """Parsing good args doesn't raise an error."""
    prepare_context(good_cli_args, tmpdir)
    assert context.name == "tests_en_library"
    assert context.creator == "bob"
    assert context.title == "a title"
    assert context.description == "a description"
    assert context.library_url == "http://geo.libretexts.org"
    assert context.tmp_folder == Path(tmpdir)


@pytest.mark.parametrize(
    "missing_input",
    [
        pytest.param("name", id="name"),
        pytest.param("creator", id="creator"),
        pytest.param("name", id="name"),
        pytest.param("description", id="description"),
        pytest.param("title", id="title"),
        pytest.param("library-url", id="library url"),
    ],
)
def test_entrypoint_missing(good_cli_args: list[str], missing_input: str, tmpdir: str):
    """Parsing bad args (built by removing one value from good args) raises an error."""
    missing_arg_index = good_cli_args.index(f"--{missing_input}")
    bad_cli_args = (
        good_cli_args[:missing_arg_index] + good_cli_args[missing_arg_index + 2 :]
    )
    with pytest.raises(SystemExit):
        prepare_context(bad_cli_args, tmpdir)


@pytest.mark.parametrize(
    "context_name, expected_context_value",
    [
        pytest.param("publisher", "openZIM", id="publisher"),
        pytest.param("file_name", "{name}_{period}", id="file_name"),
        pytest.param("long_description", None, id="long_description"),
        pytest.param("tags", None, id="tags"),
        pytest.param("secondary_color", "#FFFFFF", id="secondary_color"),
        pytest.param("page_title_include", None, id="page_id_include"),
        pytest.param("page_id_include", None, id="page_id_include"),
        pytest.param("page_title_exclude", None, id="page_id_include"),
        pytest.param("root_page_id", None, id="root_page_id"),
        pytest.param("overwrite_existing_zim", False, id="overwrite"),
        pytest.param("debug", False, id="debug"),
        pytest.param("output_folder", Path("/output"), id="output_folder"),
        pytest.param("zimui_dist", Path("../zimui/dist"), id="zimui_dist"),
        pytest.param("stats_filename", None, id="stats_filename"),
        pytest.param("illustration_url", None, id="illustration_url"),
        pytest.param("s3_url_with_credentials", None, id="s3_url_with_credentials"),
        pytest.param("assets_workers", 10, id="assets_workers"),
        pytest.param("bad_assets_threshold", 10, id="bad_assets_threshold"),
        pytest.param("contact_info", "https://www.kiwix.org", id="contact_info"),
    ],
)
def test_entrypoint_defaults(
    good_cli_args: list[str],
    tmpdir: str,
    context_name: str,
    expected_context_value: Any,
):
    """Not passing optional args still has a proper default in Context."""
    prepare_context(good_cli_args, tmpdir)
    assert context.__getattribute__(context_name) == expected_context_value


@pytest.mark.parametrize(
    "env_var_name, env_var_value, context_name, expected_context_value",
    [
        pytest.param(
            "MINDTOUCH_TMP",
            "../foo/bar",
            "tmp_folder",
            Path("../foo/bar"),
            id="tmp_folder",
        ),
    ],
)
def test_entrypoint_defaults_env_var(
    good_cli_args: list[str],
    tmpdir: str,
    env_var_name: str,
    env_var_value: str,
    context_name: str,
    expected_context_value: Any,
):
    """Not passing optional args sources Context default in environement variable."""
    try:
        os.environ[env_var_name] = env_var_value
        prepare_context(good_cli_args, tmpdir)
        assert context.__getattribute__(context_name) == expected_context_value
    finally:
        os.environ.pop(env_var_name)


@pytest.mark.parametrize(
    "arg_name, arg_value, context_name, expected_context_value",
    [
        pytest.param("--publisher", "Someone", "publisher", "Someone", id="publisher"),
        pytest.param(
            "--file-name",
            "{name}-aaa_{period}",
            "file_name",
            "{name}-aaa_{period}",
            id="file_name",
        ),
        pytest.param(
            "--long-description",
            "A long description",
            "long_description",
            "A long description",
            id="long_description",
        ),
        pytest.param(
            "--tags",
            "tag1:val1,val2 ;tag2",
            "tags",
            ["tag1:val1,val2", "tag2"],
            id="tags",
        ),
        pytest.param(
            "--secondary-color",
            "#EEEEEE",
            "secondary_color",
            "#EEEEEE",
            id="secondary_color",
        ),
        pytest.param(
            "--page-id-include",
            " 123 , 45",
            "page_id_include",
            ["123", "45"],
            id="page_title_include",
        ),
        pytest.param(
            "--root-page-id",
            "123",
            "root_page_id",
            "123",
            id="root_page_id",
        ),
        pytest.param(
            "--overwrite",
            "",
            "overwrite_existing_zim",
            True,
            id="overwrite",
        ),
        pytest.param(
            "--tmp",
            "foo/bar",
            "tmp_folder",
            Path("foo/bar"),
            id="tmp_folder",
        ),
        pytest.param(
            "--output",
            "foo/bar",
            "output_folder",
            Path("foo/bar"),
            id="output_folder",
        ),
        pytest.param(
            "--debug",
            "",
            "debug",
            True,
            id="debug",
        ),
        pytest.param(
            "--zimui-dist",
            "foo/bar",
            "zimui_dist",
            Path("foo/bar"),
            id="zimui_dist",
        ),
        pytest.param(
            "--stats-filename",
            "foo/bar.json",
            "stats_filename",
            Path("foo/bar.json"),
            id="stats_filename",
        ),
        pytest.param(
            "--illustration-url",
            "https://www.acme.com/logo.png",
            "illustration_url",
            "https://www.acme.com/logo.png",
            id="illustration_url",
        ),
        pytest.param(
            "--optimization-cache",
            "https://s3.acme.com/?keyId=xxx&secretAccessKey=xxx&bucketName=foo",
            "s3_url_with_credentials",
            "https://s3.acme.com/?keyId=xxx&secretAccessKey=xxx&bucketName=foo",
            id="s3_url_with_credentials",
        ),
        pytest.param(
            "--assets-workers",
            "123",
            "assets_workers",
            123,
            id="assets_workers",
        ),
        pytest.param(
            "--bad-assets-threshold",
            "123",
            "bad_assets_threshold",
            123,
            id="bad_assets_threshold",
        ),
        pytest.param(
            "--contact-info",
            "mindtouch2zim/0.1.0-dev0 (https://www.kiwix.org) zimscraperlib/5.0.0-dev0",
            "contact_info",
            "mindtouch2zim/0.1.0-dev0 (https://www.kiwix.org) zimscraperlib/5.0.0-dev0",
            id="contact_info",
        ),
    ],
)
def test_entrypoint_optional_args(
    good_cli_args: list[str],
    tmpdir: str,
    arg_name: str,
    arg_value: str,
    context_name: str,
    expected_context_value: Any,
):
    """Passing optional args does set the value in context."""
    prepare_context(
        (
            [*good_cli_args, arg_name, arg_value]
            if arg_value
            else [*good_cli_args, arg_name]
        ),
        tmpdir,
    )
    assert context.__getattribute__(context_name) == expected_context_value


@pytest.mark.parametrize(
    "arg_name, arg_value, context_name, expected_match, expected_no_match",
    [
        pytest.param(
            "--page-title-include",
            "title1|title2",
            "page_title_include",
            ["a title1 page", "a TITLE2 page", "title1"],
            ["a title3 page"],
            id="page_title_include",
        ),
        pytest.param(
            "--page-title-exclude",
            "title1|title2",
            "page_title_exclude",
            ["a title1 page", "a TITLE2 page", "title1"],
            ["a title3 page"],
            id="page_title_exclude",
        ),
        pytest.param(
            "--bad-assets-regex",
            r"https?:\/\/acme\.com/",
            "bad_assets_regex",
            [
                "https://acme.com/asset1.png",
                "https://a.mtstatic.com/@cache/asset1.png",
                "http://a.mtstatic.com/@style/asset2.css",
            ],
            ["https://www.acme.com/asset1.png"],
            id="bad_assets_regex",
        ),
        pytest.param(
            "",
            "",
            "bad_assets_regex",
            [
                "https://a.mtstatic.com/@cache/asset1.png",
                "http://a.mtstatic.com/@style/asset2.css",
            ],
            ["https://acme.com/asset1.png", "https://www.acme.com/asset1.png"],
            id="bad_assets_regex_default",
        ),
    ],
)
def test_entrypoint_regex_args(
    good_cli_args: list[str],
    tmpdir: str,
    arg_name: str,
    arg_value: str,
    context_name: str,
    expected_match: list[str],
    expected_no_match: list[str],
):
    """Passing optional args does set the value in context."""
    prepare_context(
        ([*good_cli_args, arg_name, arg_value] if arg_name else good_cli_args), tmpdir
    )
    regex: re.Pattern = context.__getattribute__(context_name)
    for match in expected_match:
        assert regex.findall(match)
    for match in expected_no_match:
        assert not regex.findall(match)
