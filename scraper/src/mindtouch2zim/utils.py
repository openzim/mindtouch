from pathlib import Path
from urllib.parse import urlparse


def get_asset_path_from_url(online_url: str, already_used_paths: list[Path]) -> Path:
    """Computes the path where one should store its asset based on its online URL

    This function try to:
    - preserve as much the online path as possible
    - simplify filename (e.g. dropping querystring) to simply ZimPath
    """
    original_path = Path(urlparse(online_url).path)
    target_parent = Path(
        *[
            parent.name
            for parent in reversed(original_path.parents)
            if parent.name and parent.name != ".."
        ]
    )

    index = 0
    while True:
        relative_path = (
            target_parent / f"{original_path.stem}{'_' + str(index) if index else ''}"
            f"{original_path.suffix}"
        )
        if relative_path not in already_used_paths:
            break
        index += 1
    return relative_path
