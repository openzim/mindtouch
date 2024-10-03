import pytest

from libretexts2zim.client import LibraryPage, LibraryTree
from libretexts2zim.processor import ContentFilter


@pytest.fixture(scope="module")
def library_tree() -> LibraryTree:
    root = LibraryPage(id="24", title="Home page", path="")
    topic1 = LibraryPage(
        id="25", title="1: First topic", path="1_First_Topic", parent=root
    )
    root.children.append(topic1)
    topic1_1 = LibraryPage(id="26", title="1.1: Cloud", path="1.1_Cloud", parent=topic1)
    topic1.children.append(topic1_1)
    topic1_2 = LibraryPage(id="27", title="1.2: Tree", path="1.2_Tree", parent=topic1)
    topic1.children.append(topic1_2)
    topic1_3 = LibraryPage(id="28", title="1.3: Bees", path="1.3_Bees", parent=topic1)
    topic1.children.append(topic1_3)
    topic2 = LibraryPage(
        id="29", title="2: Second topic", path="2_Second_Topic", parent=root
    )
    root.children.append(topic2)
    topic2_1 = LibraryPage(
        id="30", title="2.1: Underground", path="2.1_Underground", parent=topic2
    )
    topic2.children.append(topic2_1)
    topic2_2 = LibraryPage(id="31", title="2.2: Lava", path="2.2_Lava", parent=topic2)
    topic2.children.append(topic2_2)
    topic2_3 = LibraryPage(
        id="32", title="2.3: Volcano", path="2.3_Volcano", parent=topic2
    )
    topic2.children.append(topic2_3)
    topic3 = LibraryPage(
        id="33", title="3: Third topic", path="3_Third_Topic", parent=root
    )
    root.children.append(topic3)
    topic3_1 = LibraryPage(
        id="34", title="3.1: Ground", path="3.1_Ground", parent=topic3
    )
    topic3.children.append(topic3_1)
    topic3_2 = LibraryPage(id="35", title="3.2: Earth", path="3.2_Earth", parent=topic3)
    topic3.children.append(topic3_2)
    topic3_3 = LibraryPage(id="36", title="3.3: Sky", path="3.3_Sky", parent=topic3)
    topic3.children.append(topic3_3)
    return LibraryTree(
        root=root,
        pages={
            root.id: root,
            topic1.id: topic1,
            topic1_1.id: topic1_1,
            topic1_2.id: topic1_2,
            topic1_3.id: topic1_3,
            topic2.id: topic2,
            topic2_1.id: topic2_1,
            topic2_2.id: topic2_2,
            topic2_3.id: topic2_3,
            topic3.id: topic3,
            topic3_1.id: topic3_1,
            topic3_2.id: topic3_2,
            topic3_3.id: topic3_3,
        },
    )


@pytest.mark.parametrize(
    "content_filter,expected_ids",
    [
        pytest.param(
            ContentFilter(
                page_title_include=r"^1\..*",
                page_title_exclude=None,
                page_id_include=None,
                root_page_id=None,
            ),
            ["24", "25", "26", "27", "28"],
            id="include_1",
        ),
        pytest.param(
            ContentFilter(
                page_title_include=r"^2\..*",
                page_title_exclude=None,
                page_id_include=None,
                root_page_id=None,
            ),
            ["24", "29", "30", "31", "32"],
            id="include_2",
        ),
        pytest.param(
            ContentFilter(
                page_title_include=None,
                page_title_exclude=None,
                page_id_include="26,27,28",
                root_page_id=None,
            ),
            ["24", "25", "26", "27", "28"],
            id="include_3",
        ),
        pytest.param(
            ContentFilter(
                page_title_include="ground",
                page_title_exclude=None,
                page_id_include=None,
                root_page_id=None,
            ),
            ["24", "29", "30", "33", "34"],
            id="include_4",
        ),
        pytest.param(
            ContentFilter(
                page_title_include=r"^1\..*",
                page_title_exclude="Tree",
                page_id_include=None,
                root_page_id=None,
            ),
            ["24", "25", "26", "28"],
            id="include_exclude_1",
        ),
        pytest.param(
            ContentFilter(
                page_title_include=None,
                page_title_exclude="Tree",
                page_id_include="26,27,28",
                root_page_id=None,
            ),
            ["24", "25", "26", "28"],
            id="include_exclude_2",
        ),
        pytest.param(
            ContentFilter(
                page_title_include="ground",
                page_title_exclude="^2",
                page_id_include=None,
                root_page_id=None,
            ),
            ["24", "33", "34"],
            id="include_exclude_3",
        ),
        pytest.param(
            ContentFilter(
                page_title_include=r"^1\..*",
                page_title_exclude="tree",
                page_id_include=None,
                root_page_id=None,
            ),
            ["24", "25", "26", "28"],
            id="include_exclude_case_insensitive",
        ),
        pytest.param(
            ContentFilter(
                page_title_include="tree",
                page_title_exclude=None,
                page_id_include=None,
                root_page_id=None,
            ),
            ["24", "25", "27"],
            id="include_case_insensitive",
        ),
        pytest.param(
            ContentFilter(
                page_title_include="^tree",
                page_title_exclude=None,
                page_id_include=None,
                root_page_id=None,
            ),
            [],
            id="include_no_match",
        ),
        pytest.param(
            ContentFilter(
                page_title_include=None,
                page_title_exclude=None,
                page_id_include=None,
                root_page_id="25",
            ),
            ["25", "26", "27", "28"],
            id="root_page_id",
        ),
        pytest.param(
            ContentFilter(
                page_title_include=r"^1\.1.*",
                page_title_exclude=None,
                page_id_include=None,
                root_page_id="25",
            ),
            ["25", "26"],
            id="root_page_id_and_include",
        ),
    ],
)
def test_content_filter(
    content_filter: ContentFilter, expected_ids: list[str], library_tree: LibraryTree
):
    assert [page.id for page in content_filter.filter(library_tree)] == expected_ids
