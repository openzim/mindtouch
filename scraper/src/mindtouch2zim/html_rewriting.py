from zimscraperlib.rewriting.html import (
    AttrsList,
    format_attr,
    get_attr_value_from,
)
from zimscraperlib.rewriting.html import rules as html_rules
from zimscraperlib.rewriting.url_rewriting import ArticleUrlRewriter

from mindtouch2zim.processor import HtmlUrlsRewriter
from mindtouch2zim.utils import is_better_srcset_descriptor


@html_rules.rewrite_tag()
def rewrite_img_tags(
    tag: str,
    attrs: AttrsList,
    base_href: str | None,
    url_rewriter: ArticleUrlRewriter,
    *,
    auto_close: bool,
):

    if tag != "img":
        return
    if not isinstance(url_rewriter, HtmlUrlsRewriter):
        raise Exception("Expecting HtmlUrlsRewriter")
    if not (srcset_value := get_attr_value_from(attrs, "srcset")):
        # simple case, just need to rewrite the src
        src_value = get_attr_value_from(attrs, "src")
        if src_value is None:
            return  # no need to rewrite this img without src
    else:
        scrset_values = [value.strip() for value in srcset_value.split(",")]
        best_src_value = None
        best_descriptor = None
        for src_value in scrset_values:
            # Ignore RUF005 which prefer to avoid concatenation, because I didn't found
            # another way to wwite this which still please pyright type checker, which
            # is not capable to properly infer types of results with other syntaxes
            url, descriptor = (src_value.rsplit(" ", 1) + [None])[:2]  # noqa: RUF005
            if best_src_value is None:
                best_src_value = url
                best_descriptor = descriptor
                continue
            if is_better_srcset_descriptor(
                new_descriptor=descriptor, current_best_descriptor=best_descriptor
            ):
                best_src_value = url
                best_descriptor = descriptor

        src_value = best_src_value

    rewrite_result = url_rewriter(src_value, base_href=base_href, rewrite_all_url=True)
    # add 'content/' to the URL since all assets will be stored in the sub.-path
    new_attr_value = f"content/{rewrite_result.rewriten_url}"
    url_rewriter.add_item_to_download(rewrite_result)

    values = " ".join(
        format_attr(*attr)
        for attr in [
            (attr_name, attr_value)
            for (attr_name, attr_value) in attrs
            if attr_name not in ["src", "srcset", "sizes"]
        ]
        + [("src", new_attr_value)]
    )
    return f"<img {values}{'/>' if auto_close else '>'}"
