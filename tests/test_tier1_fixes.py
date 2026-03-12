import json
from unittest.mock import AsyncMock

from typer.testing import CliRunner

from notion_cli._block_utils import replace_in_rich_text
from notion_cli.cli import app
from notion_cli.parsing import parse_fields

PAGE_ID = "aabbccdd-1122-3344-5566-778899001122"
PARENT_ID = "11223344-5566-7788-99aa-bbccddeeff00"
MOCK_PAGE = {"id": PAGE_ID, "object": "page", "properties": {}}


class TestBug1StdinDryRun:
    def test_create_stdin_dry_run_does_not_call_api(
        self, runner: CliRunner, mock_client: AsyncMock
    ) -> None:
        ndjson = f'{{"parent": "{PARENT_ID}", "title": "A"}}\n'
        result = runner.invoke(
            app,
            ["page", "create", "--stdin", "--dry-run"],
            input=ndjson,
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["dry_run"] is True
        mock_client.pages.create.assert_not_called()

    def test_move_stdin_dry_run_does_not_call_api(
        self, runner: CliRunner, mock_client: AsyncMock
    ) -> None:
        ndjson = f'{{"page_id": "{PAGE_ID}", "to": "{PARENT_ID}"}}\n'
        result = runner.invoke(
            app,
            ["page", "move", "--stdin", "--dry-run"],
            input=ndjson,
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["dry_run"] is True
        mock_client.pages.move.assert_not_called()


class TestBug2ParseFieldsWhitespace:
    def test_strips_spaces_after_commas(self) -> None:
        result = parse_fields("id, url, title")
        assert result == {"id", "url", "title"}

    def test_pure_whitespace_returns_none(self) -> None:
        result = parse_fields("   ")
        assert result is None


class TestBug4ApiLeadingSlash:
    def test_leading_slash_stripped(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.request.return_value = {"id": "x"}
        runner.invoke(
            app,
            ["api", "GET", "/pages/abc-123"],
            env={"NOTION_API_KEY": "secret"},
        )

        mock_client.request.assert_called_once_with(path="pages/abc-123", method="GET")


class TestBug5PageUpdateNoOp:
    def test_no_flags_rejected(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        result = runner.invoke(
            app,
            ["page", "update", PAGE_ID],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 2
        error = json.loads(result.stderr)
        assert error["error_type"] == "missing_args"
        mock_client.pages.update.assert_not_called()


class TestBug6FullGracefulComments:
    def test_full_with_comments_403_returns_empty_comments(
        self, runner: CliRunner, mock_client: AsyncMock
    ) -> None:
        from notion_client.errors import APIResponseError

        mock_client.pages.retrieve.return_value = MOCK_PAGE
        mock_client.blocks.children.list.return_value = {
            "results": [{"id": "b1", "type": "paragraph", "has_children": False}],
            "has_more": False,
        }
        mock_client.comments.list.side_effect = APIResponseError(
            code="restricted_resource",
            status=403,
            message="forbidden",
            headers={},
            raw_body_text="",
        )

        result = runner.invoke(
            app,
            ["page", "get", PAGE_ID, "--full"],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["page"]["id"] == PAGE_ID
        assert len(data["blocks"]) == 1
        assert data["comments"] == []


class TestBug8MalformedSpans:
    def test_replace_handles_missing_text_key(self) -> None:
        rich_text = [{"type": "text"}]
        result, changed = replace_in_rich_text(rich_text, "find", "replace")
        assert not changed

    def test_replace_handles_missing_content_key(self) -> None:
        rich_text = [{"type": "text", "text": {}}]
        result, changed = replace_in_rich_text(rich_text, "find", "replace")
        assert not changed
