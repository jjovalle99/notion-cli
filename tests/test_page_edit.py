import json
from unittest.mock import AsyncMock

from typer.testing import CliRunner

from notion_cli._block_utils import replace_in_rich_text
from notion_cli.cli import app

PAGE_ID = "aabbccdd-1122-3344-5566-778899001122"


class TestReplaceInRichText:
    def test_simple_replace(self) -> None:
        rich_text = [{"type": "text", "text": {"content": "hello world"}, "annotations": {}}]
        result, changed = replace_in_rich_text(rich_text, "world", "earth")
        assert changed
        assert result[0]["text"]["content"] == "hello earth"

    def test_no_match(self) -> None:
        rich_text = [{"type": "text", "text": {"content": "hello"}, "annotations": {}}]
        result, changed = replace_in_rich_text(rich_text, "xyz", "abc")
        assert not changed
        assert result is rich_text

    def test_preserves_annotations(self) -> None:
        rich_text = [
            {
                "type": "text",
                "text": {"content": "old value"},
                "annotations": {"bold": True, "color": "red"},
            }
        ]
        result, changed = replace_in_rich_text(rich_text, "old", "new")
        assert changed
        assert result[0]["annotations"] == {"bold": True, "color": "red"}
        assert result[0]["text"]["content"] == "new value"

    def test_preserves_href(self) -> None:
        rich_text = [
            {
                "type": "text",
                "text": {"content": "click old here", "link": {"url": "https://example.com"}},
                "annotations": {},
            }
        ]
        result, changed = replace_in_rich_text(rich_text, "old", "new")
        assert changed
        assert result[0]["text"]["link"] == {"url": "https://example.com"}

    def test_skips_non_text_types(self) -> None:
        rich_text = [
            {"type": "mention", "mention": {"user": {"id": "u1"}}},
            {"type": "text", "text": {"content": "hello old"}, "annotations": {}},
        ]
        result, changed = replace_in_rich_text(rich_text, "old", "new")
        assert changed
        assert result[0]["type"] == "mention"
        assert result[1]["text"]["content"] == "hello new"

    def test_multiple_spans(self) -> None:
        rich_text = [
            {"type": "text", "text": {"content": "old A"}, "annotations": {}},
            {"type": "text", "text": {"content": "old B"}, "annotations": {"bold": True}},
        ]
        result, changed = replace_in_rich_text(rich_text, "old", "new")
        assert changed
        assert result[0]["text"]["content"] == "new A"
        assert result[1]["text"]["content"] == "new B"
        assert result[1]["annotations"] == {"bold": True}


class TestPageEdit:
    def test_basic_find_replace(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.blocks.children.list.return_value = {
            "results": [
                {
                    "id": "b1",
                    "type": "paragraph",
                    "has_children": False,
                    "paragraph": {
                        "rich_text": [
                            {"type": "text", "text": {"content": "hello world"}, "annotations": {}}
                        ]
                    },
                }
            ],
            "has_more": False,
        }
        mock_client.blocks.update.return_value = {"id": "b1", "type": "paragraph"}

        result = runner.invoke(
            app,
            ["page", "edit", PAGE_ID, "--find", "world", "--replace", "earth"],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["blocks_modified"] == 1
        mock_client.blocks.update.assert_called_once()

    def test_no_matches(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.blocks.children.list.return_value = {
            "results": [
                {
                    "id": "b1",
                    "type": "paragraph",
                    "has_children": False,
                    "paragraph": {
                        "rich_text": [
                            {"type": "text", "text": {"content": "hello"}, "annotations": {}}
                        ]
                    },
                }
            ],
            "has_more": False,
        }

        result = runner.invoke(
            app,
            ["page", "edit", PAGE_ID, "--find", "xyz", "--replace", "abc"],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["blocks_modified"] == 0
        mock_client.blocks.update.assert_not_called()

    def test_dry_run(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.blocks.children.list.return_value = {
            "results": [
                {
                    "id": "b1",
                    "type": "paragraph",
                    "has_children": False,
                    "paragraph": {
                        "rich_text": [
                            {"type": "text", "text": {"content": "old text"}, "annotations": {}}
                        ]
                    },
                }
            ],
            "has_more": False,
        }

        result = runner.invoke(
            app,
            ["page", "edit", PAGE_ID, "--find", "old", "--replace", "new", "--dry-run"],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["dry_run"] is True
        assert data["blocks_would_modify"] == 1
        mock_client.blocks.update.assert_not_called()
