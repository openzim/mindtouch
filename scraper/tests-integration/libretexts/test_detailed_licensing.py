from typing import Any

import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape

from mindtouch2zim.constants import ROOT_DIR
from mindtouch2zim.libretexts.detailed_licensing import (
    _get_licensing_report_data,
    _render_html_from_data,
)


@pytest.fixture(scope="module")
def licensing_report_data() -> Any:
    return _get_licensing_report_data(
        "https://geo.libretexts.org/Courses/California_State_University_Los_Angeles/"
        "Book%3A_An_Introduction_to_Geology_(Johnson_Affolter_Inkenbrandt_and_Mosher)"
    )


def test_get_licensing_report_data(licensing_report_data: Any):
    """Check we can still get licensing report data"""

    assert licensing_report_data

    # statistics properties
    assert "meta" in licensing_report_data
    assert "specialRestrictions" in licensing_report_data["meta"]
    assert "licenses" in licensing_report_data["meta"]
    assert isinstance(licensing_report_data["meta"]["licenses"], list)
    assert "label" in licensing_report_data["meta"]["licenses"][0]
    assert "link" in licensing_report_data["meta"]["licenses"][0]
    assert "version" in licensing_report_data["meta"]["licenses"][0]
    assert "count" in licensing_report_data["meta"]["licenses"][0]
    assert int(licensing_report_data["meta"]["licenses"][0]["count"])
    assert "percent" in licensing_report_data["meta"]["licenses"][0]
    assert float(licensing_report_data["meta"]["licenses"][0]["percent"])
    assert "text" in licensing_report_data
    assert "totalPages" in licensing_report_data["text"]

    # details properties
    def check_item(data: Any):
        assert "license" in data
        assert "label" in data["license"]
        assert "link" in data["license"]
        # optional property, not set at least for "Undeclared" license
        if data["license"]["label"] != "Undeclared":
            assert "version" in data["license"]
        assert "url" in data
        assert "title" in data
        assert "children" in data
        assert isinstance(data["children"], list)
        for child in data["children"]:
            check_item(child)

    check_item(licensing_report_data["text"])


def test_render_licensing_template(licensing_report_data: Any):
    jinja2_env = Environment(
        loader=FileSystemLoader(ROOT_DIR.joinpath("templates")),
        autoescape=select_autoescape(),
    )
    template = jinja2_env.get_template("libretexts.detailed-licensing.html")
    assert _render_html_from_data(template, licensing_report_data)
