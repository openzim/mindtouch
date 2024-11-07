from pathlib import Path
from urllib.parse import urlparse

from zimscraperlib.zim import Creator
from zimscraperlib.zim.indexing import IndexData


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


def is_better_srcset_descriptor(
    new_descriptor: str | None, current_best_descriptor: str | None
) -> bool:
    """Compares two HTML images srcset descriptors

    In srcset="PtolemyWorldMap-1024x701.jpg 1024w", the descriptor is 1024w.

    Descriptors can be None, meaning that they are not set in the srcset.

    This implementation is a bit naive because it supposes the srcset is valid (i.e.
    no mix of width descriptor and pixel density descriptor), otherwise it assumes that
    new descriptor is not better than current one if both are set.
    """
    if new_descriptor is None:
        return False
    if current_best_descriptor is None:
        return True
    current_best_descriptor = current_best_descriptor.strip()
    new_descriptor = new_descriptor.strip()
    if current_best_descriptor[-1:] != new_descriptor[-1:]:
        return False
    return int(new_descriptor[:-1]) > int(current_best_descriptor[:-1])


def add_item_for(
    creator: Creator,
    path: str,
    title: str | None = None,
    *,
    fpath: Path | None = None,
    content: bytes | str | None = None,
    mimetype: str | None = None,
    is_front: bool | None = None,
    should_compress: bool | None = None,
    delete_fpath: bool | None = False,
    duplicate_ok: bool | None = None,
    index_data: IndexData | None = None,
    auto_index: bool = True,
):
    """
    Boilerplate to avoid repeating pyright ignore

    To be removed, once upstream issue is solved, see
    https://github.com/openzim/libretexts/issues/26
    """
    creator.add_item_for(  # pyright: ignore[reportUnknownMemberType]
        path=path,
        title=title,
        fpath=fpath,
        content=content,
        mimetype=mimetype,
        is_front=is_front,
        should_compress=should_compress,
        delete_fpath=delete_fpath,
        duplicate_ok=duplicate_ok,
        index_data=index_data,
        auto_index=auto_index,
    )
