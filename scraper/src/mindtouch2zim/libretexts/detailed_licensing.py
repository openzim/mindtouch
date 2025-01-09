from typing import Any

from jinja2 import Template
from zimscraperlib.rewriting.html import HtmlRewriter

from mindtouch2zim.client import LibraryPage, MindtouchClient
from mindtouch2zim.context import Context
from mindtouch2zim.libretexts.errors import BadBookPageError

context = Context.get()
logger = context.logger


def _get_licensing_report_data(cover_url: str) -> Any:
    """
    Get licensing report from libretexts.org

    Logic to get the data has been adapted from `buildLicensingReport` function
    at https://cdn.libretexts.net/github/LibreTextsMain/DynamicLicensing/dist/dynamicLicensing.min.js

    Probably coming from
    https://github.com/LibreTexts/Libretext/blob/master/public/DynamicLicensing/dynamicLicensing.js
    """
    api_url = f"https://api.libretexts.org/endpoint/licensereport/{cover_url}"
    logger.debug(f"Calling API at {api_url}")
    resp = context.web_session.get(
        url=api_url,
        headers={"Origin": "https://www.libretexts.org"},  # kinda authorization header
        timeout=context.http_timeout_long_seconds,
    )
    resp.raise_for_status()
    return resp.json()


def _render_html_from_data(jinja2_template: Template, licensing_data: Any) -> str:
    if not licensing_data.get("meta", {}).get("specialRestrictions", None):
        special_restrictions = None
    else:

        def get_restriction_label(restriction_key: str):
            return {
                "noncommercial": "Noncommercial",
                "noderivatives": "No Derivatives",
                "fairuse": "Fair Use",
            }.get(restriction_key, restriction_key)

        special_restrictions = ", ".join(
            [
                get_restriction_label(restriction)
                for restriction in licensing_data["meta"]["specialRestrictions"]
            ]
        )
    return jinja2_template.render(
        data=licensing_data, special_restrictions=special_restrictions
    )


def rewrite_detailed_licensing(
    rewriter: HtmlRewriter,
    jinja2_template: Template,
    mindtouch_client: MindtouchClient,
    page: LibraryPage,
) -> str:
    """
    Get and statically rewrite the detailed licensing info of libretexts.org

    """

    cover_page_url = mindtouch_client.get_cover_page_encoded_url(page)
    if cover_page_url is None:
        raise BadBookPageError()
    return rewriter.rewrite(
        _render_html_from_data(
            jinja2_template=jinja2_template,
            licensing_data=_get_licensing_report_data(cover_page_url),
        )
    ).content
