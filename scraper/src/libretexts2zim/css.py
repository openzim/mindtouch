from collections.abc import Iterable
from pathlib import Path
from urllib.parse import urljoin, urlparse

from tinycss2 import ast, parse_stylesheet_bytes, serialize  # pyright: ignore
from tinycss2.serializer import serialize_url  # pyright: ignore

from libretexts2zim.utils import get_asset_path_from_url

OriginalUrl = str
FullZimPath = Path
RelativeCssPath = Path


class CssProcessor:
    """Utility to to process CSS, extract assets and rewrite URLs

    This utility can process multiple CSS documents that will be stored in a ZIM
    It extracts the list of assets (images, fonts) that are used in the CSS documents
    and compute appropriate ZIM paths for each of them.

    Arguments:
      css_target_path: "folder" where the CSS documents that will be processed will be
        stored in the ZIM
      css_assets_root_path: "folder" where the CSS assets referenced in the CSS
        documents will be stored in the ZIM
    """

    def __init__(
        self,
        css_target_path: Path = Path("/content"),
        css_assets_root_path: Path = Path("/content/css_assets"),
    ) -> None:
        self.css_target_path = css_target_path
        self.css_assets_root_path = css_assets_root_path
        self.css_assets: dict[OriginalUrl, FullZimPath] = {}
        self.used_paths: list[RelativeCssPath] = []

    def process(self, css_original_url: str, css_content: bytes) -> str:
        """Rewrite CSS rules and update list of assets to fetch

        This function updates the CSS rules to target assets path inside the ZIM
        It also updates the list of `css_assets` which is the list of online resources
        referenced inside the ZIM and which should be fetched and stored inside the ZIM
        for proper CSS operation.
        """
        rules, _ = parse_stylesheet_bytes(  # pyright: ignore[reportUnknownVariableType]
            css_content
        )
        self._process_list(
            css_original_url,
            rules,  # pyright: ignore[reportUnknownArgumentType]
        )
        return serialize(
            [
                rule
                for rule in rules  # pyright: ignore[reportUnknownVariableType]
                if not isinstance(rule, ast.ParseError)
            ]
        )

    def _process_url(
        self, css_original_url: str, css_url: str
    ) -> RelativeCssPath | None:
        """Process a URL which has been found in CSS rules

        - Transforms the URL into a ZIM path
        - Updates the list of assets to retrieve
        """
        original_url = urljoin(css_original_url, css_url)
        original_url_parsed = urlparse(original_url)
        if original_url_parsed.scheme.lower() not in ["http", "https"]:
            return None
        if original_url in self.css_assets:
            return self.css_assets[original_url].relative_to(self.css_target_path)
        relative_path = get_asset_path_from_url(original_url, self.used_paths)
        self.used_paths.append(relative_path)
        target_path = self.css_assets_root_path / relative_path
        self.css_assets[original_url] = target_path
        return target_path.relative_to(self.css_target_path)

    def _process_node(self, css_original_url: str, node: ast.Node):
        """Process one single CSS node"""
        if isinstance(
            node,
            ast.QualifiedRule
            | ast.SquareBracketsBlock
            | ast.ParenthesesBlock
            | ast.CurlyBracketsBlock,
        ):
            self._process_list(
                css_original_url,
                node.content,  # pyright: ignore[reportUnknownArgumentType, reportUnknownMemberType]
            )
        elif isinstance(node, ast.FunctionBlock):
            if node.lower_name == "url":  # pyright: ignore[reportUnknownMemberType]
                url_node: ast.Node = node.arguments[0]  # pyright: ignore
                relative_css_path = self._process_url(
                    css_original_url,
                    url_node.value,  # pyright: ignore
                )
                if not relative_css_path:
                    return
                url_node.value = str(relative_css_path)  # pyright: ignore
                url_node.representation = (  # pyright: ignore
                    f'"{serialize_url(str(relative_css_path))}"'
                )

            else:
                self._process_list(
                    css_original_url,
                    node.arguments,  # pyright: ignore
                )
        elif isinstance(node, ast.AtRule):
            self._process_list(
                css_original_url,
                node.prelude,  # pyright: ignore
            )
            self._process_list(
                css_original_url,
                node.content,  # pyright: ignore
            )
        elif isinstance(node, ast.Declaration):
            self._process_list(
                css_original_url,
                node.value,  # pyright: ignore
            )
        elif isinstance(node, ast.URLToken):
            relative_css_path = self._process_url(
                css_original_url,
                node.value,  # pyright: ignore
            )
            if not relative_css_path:
                return
            node.value = str(relative_css_path)
            node.representation = f"url({serialize_url(str(relative_css_path))})"

    def _process_list(self, css_original_url: str, nodes: Iterable[ast.Node] | None):
        """Process a list of CSS nodes"""
        if not nodes:
            return
        for node in nodes:
            self._process_node(css_original_url, node)
