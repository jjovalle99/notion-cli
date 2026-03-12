import json
from unittest.mock import AsyncMock

from typer.testing import CliRunner

from notion_cli.cli import app

PAGE_ID = "aabbccdd-1122-3344-5566-778899001122"

MOCK_BLOCKS = {
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
        },
        {
            "id": "b2",
            "type": "heading_1",
            "has_children": False,
            "heading_1": {
                "rich_text": [
                    {"type": "text", "text": {"content": "no match here"}, "annotations": {}}
                ]
            },
        },
        {
            "id": "b3",
            "type": "paragraph",
            "has_children": False,
            "paragraph": {
                "rich_text": [
                    {"type": "text", "text": {"content": "world peace"}, "annotations": {}}
                ]
            },
        },
    ],
    "has_more": False,
}


class TestPageGrep:
    def test_finds_matches(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.blocks.children.list.return_value = MOCK_BLOCKS

        result = runner.invoke(
            app,
            ["page", "grep", PAGE_ID, "world"],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["match_count"] == 2
        assert len(data["results"]) == 2
        assert data["results"][0]["block_id"] == "b1"
        assert data["results"][1]["block_id"] == "b3"

    def test_no_matches(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.blocks.children.list.return_value = MOCK_BLOCKS

        result = runner.invoke(
            app,
            ["page", "grep", PAGE_ID, "xyz"],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["match_count"] == 0

    def test_match_offsets(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.blocks.children.list.return_value = MOCK_BLOCKS

        result = runner.invoke(
            app,
            ["page", "grep", PAGE_ID, "world"],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        match = data["results"][0]
        assert match["text"] == "hello world"
        assert match["matches"][0]["start"] == 6
        assert match["matches"][0]["end"] == 11
        assert match["matches"][0]["text"] == "world"

    def test_ignore_case(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.blocks.children.list.return_value = MOCK_BLOCKS

        result = runner.invoke(
            app,
            ["page", "grep", PAGE_ID, "WORLD", "--ignore-case"],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["match_count"] == 2

    def test_regex_mode(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.blocks.children.list.return_value = MOCK_BLOCKS

        result = runner.invoke(
            app,
            ["page", "grep", PAGE_ID, "w.rld", "--regex"],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["match_count"] == 2

    def test_count_only(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.blocks.children.list.return_value = MOCK_BLOCKS

        result = runner.invoke(
            app,
            ["page", "grep", PAGE_ID, "world", "--count"],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data == {"match_count": 2}

    def test_invalid_regex_exits_2(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        result = runner.invoke(
            app,
            ["page", "grep", PAGE_ID, "(unclosed", "--regex"],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 2
        error = json.loads(result.stderr)
        assert error["error_type"] == "invalid_args"
