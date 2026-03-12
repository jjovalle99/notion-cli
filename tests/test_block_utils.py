import asyncio
from typing import Any
from unittest.mock import AsyncMock

import pytest

from notion_cli._block_utils import clean_block, fetch_children, fetch_recursive

BLOCK_ID = "aabbccdd-1122-3344-5566-778899001122"


class TestFetchChildren:
    @pytest.fixture
    def client(self) -> AsyncMock:
        return AsyncMock()

    def test_single_page(self, client: AsyncMock) -> None:
        client.blocks.children.list.return_value = {
            "results": [{"id": "b1"}, {"id": "b2"}],
            "has_more": False,
        }

        blocks, envelope = asyncio.run(fetch_children(client, BLOCK_ID, timeout=None))

        assert len(blocks) == 2
        assert blocks[0]["id"] == "b1"
        assert "results" not in envelope

    def test_paginates(self, client: AsyncMock) -> None:
        page1 = {"results": [{"id": "b1"}], "has_more": True, "next_cursor": "cur1"}
        page2 = {"results": [{"id": "b2"}], "has_more": False}
        client.blocks.children.list.side_effect = [page1, page2]

        blocks, _envelope = asyncio.run(fetch_children(client, BLOCK_ID, timeout=None))

        assert len(blocks) == 2
        assert client.blocks.children.list.call_count == 2

    def test_with_limit(self, client: AsyncMock) -> None:
        client.blocks.children.list.return_value = {
            "results": [{"id": f"b{i}"} for i in range(5)],
            "has_more": False,
        }

        blocks, _envelope = asyncio.run(fetch_children(client, BLOCK_ID, timeout=None, limit=3))

        assert len(blocks) == 3


class TestFetchRecursive:
    @pytest.fixture
    def client(self) -> AsyncMock:
        return AsyncMock()

    def test_flat_no_children(self, client: AsyncMock) -> None:
        client.blocks.children.list.return_value = {
            "results": [
                {"id": "b1", "type": "paragraph", "has_children": False},
                {"id": "b2", "type": "paragraph", "has_children": False},
            ],
            "has_more": False,
        }

        blocks = asyncio.run(fetch_recursive(client, BLOCK_ID, timeout=None))

        assert len(blocks) == 2
        assert "children" not in blocks[0]

    def test_recurses_into_has_children(self, client: AsyncMock) -> None:
        top_level = {
            "results": [
                {"id": "parent-1", "type": "toggle", "has_children": True},
            ],
            "has_more": False,
        }
        nested = {
            "results": [
                {"id": "child-1", "type": "paragraph", "has_children": False},
            ],
            "has_more": False,
        }
        client.blocks.children.list.side_effect = [top_level, nested]

        blocks = asyncio.run(fetch_recursive(client, BLOCK_ID, timeout=None))

        assert len(blocks) == 1
        assert blocks[0]["children"][0]["id"] == "child-1"

    def test_skips_child_page(self, client: AsyncMock) -> None:
        client.blocks.children.list.return_value = {
            "results": [
                {"id": "cp", "type": "child_page", "has_children": True},
            ],
            "has_more": False,
        }

        blocks = asyncio.run(fetch_recursive(client, BLOCK_ID, timeout=None))

        assert "children" not in blocks[0]
        assert client.blocks.children.list.call_count == 1

    def test_skips_synced_block(self, client: AsyncMock) -> None:
        client.blocks.children.list.return_value = {
            "results": [
                {"id": "sb", "type": "synced_block", "has_children": True},
            ],
            "has_more": False,
        }

        blocks = asyncio.run(fetch_recursive(client, BLOCK_ID, timeout=None))

        assert "children" not in blocks[0]
        assert client.blocks.children.list.call_count == 1

    def test_skips_child_database(self, client: AsyncMock) -> None:
        client.blocks.children.list.return_value = {
            "results": [
                {"id": "cd", "type": "child_database", "has_children": True},
            ],
            "has_more": False,
        }

        blocks = asyncio.run(fetch_recursive(client, BLOCK_ID, timeout=None))

        assert "children" not in blocks[0]

    def test_gather_exception_propagates_cleanly(self, client: AsyncMock) -> None:
        top_level = {
            "results": [
                {"id": "ok-block", "type": "toggle", "has_children": True},
                {"id": "bad-block", "type": "toggle", "has_children": True},
            ],
            "has_more": False,
        }
        ok_children = {
            "results": [{"id": "c1", "type": "paragraph", "has_children": False}],
            "has_more": False,
        }

        async def side_effect(block_id: str, **kwargs: object) -> dict[str, Any]:
            if block_id == BLOCK_ID:
                return top_level
            if block_id == "ok-block":
                return ok_children
            raise RuntimeError("API failure")

        client.blocks.children.list.side_effect = side_effect

        with pytest.raises(RuntimeError, match="API failure"):
            asyncio.run(fetch_recursive(client, BLOCK_ID, timeout=None))

    def test_skips_block_missing_id(self, client: AsyncMock) -> None:
        client.blocks.children.list.return_value = {
            "results": [
                {"type": "paragraph", "has_children": True},
                {"id": "b2", "type": "paragraph", "has_children": False},
            ],
            "has_more": False,
        }

        blocks = asyncio.run(fetch_recursive(client, BLOCK_ID, timeout=None))

        assert len(blocks) == 2
        assert "children" not in blocks[0]
        assert client.blocks.children.list.call_count == 1

    def test_respects_max_depth(self, client: AsyncMock) -> None:
        def make_level(block_id: str) -> dict:
            return {
                "results": [{"id": f"{block_id}-child", "type": "toggle", "has_children": True}],
                "has_more": False,
            }

        client.blocks.children.list.side_effect = [
            make_level("L0"),
            make_level("L1"),
        ]

        blocks = asyncio.run(fetch_recursive(client, BLOCK_ID, timeout=None, max_depth=1))

        assert len(blocks) == 1
        assert "children" not in blocks[0]


class TestCleanBlock:
    def test_strips_server_fields(self) -> None:
        block = {
            "id": "abc",
            "type": "paragraph",
            "paragraph": {"rich_text": []},
            "created_time": "2024-01-01",
            "last_edited_time": "2024-01-02",
            "created_by": {"id": "user1"},
            "last_edited_by": {"id": "user2"},
            "has_children": False,
            "archived": False,
            "object": "block",
            "parent": {"type": "page_id", "page_id": "p1"},
            "in_trash": False,
        }

        cleaned = clean_block(block)

        assert "id" not in cleaned
        assert "created_time" not in cleaned
        assert "has_children" not in cleaned
        assert "parent" not in cleaned
        assert cleaned["type"] == "paragraph"
        assert cleaned["paragraph"] == {"rich_text": []}

    def test_recurses_into_children(self) -> None:
        block = {
            "id": "parent",
            "type": "toggle",
            "toggle": {"rich_text": []},
            "has_children": True,
            "children": [
                {
                    "id": "child",
                    "type": "paragraph",
                    "paragraph": {"rich_text": []},
                    "has_children": False,
                }
            ],
        }

        cleaned = clean_block(block)

        assert "id" not in cleaned
        assert len(cleaned["children"]) == 1
        assert "id" not in cleaned["children"][0]

    def test_deep_nesting_raises_value_error(self) -> None:
        block: dict[str, object] = {"type": "toggle", "toggle": {"rich_text": []}}
        current = block
        for _ in range(60):
            child: dict[str, object] = {"type": "toggle", "toggle": {"rich_text": []}}
            current["children"] = [child]
            current = child

        with pytest.raises(ValueError, match="depth"):
            clean_block(block)

    def test_filters_skip_types_from_nested_children(self) -> None:
        from notion_cli._block_utils import SKIP_CONTENT_TYPES

        block = {
            "id": "parent",
            "type": "toggle",
            "toggle": {"rich_text": []},
            "has_children": True,
            "children": [
                {
                    "id": "c1",
                    "type": "paragraph",
                    "paragraph": {"rich_text": []},
                    "has_children": False,
                },
                {"id": "c2", "type": "synced_block", "synced_block": {}, "has_children": True},
                {"id": "c3", "type": "unsupported", "has_children": False},
            ],
        }

        cleaned = clean_block(block, skip_types=SKIP_CONTENT_TYPES)

        assert len(cleaned["children"]) == 1
        assert cleaned["children"][0]["type"] == "paragraph"
