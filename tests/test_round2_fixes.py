import asyncio
import json
from unittest.mock import AsyncMock

from typer.testing import CliRunner

from notion_cli._batch import process_batch
from notion_cli.cli import app
from notion_cli.output import ExitCode

PAGE_ID = "aabbccdd-1122-3344-5566-778899001122"


class TestBug1FullTupleUnpack:
    def test_full_with_blocks_error_propagates(
        self, runner: CliRunner, mock_client: AsyncMock
    ) -> None:
        from notion_client.errors import APIResponseError

        mock_client.pages.retrieve.return_value = {"id": PAGE_ID, "object": "page"}
        mock_client.blocks.children.list.side_effect = APIResponseError(
            code="object_not_found",
            status=404,
            message="not found",
            headers={},
            raw_body_text="",
        )
        mock_client.comments.list.return_value = {"results": [], "has_more": False}

        result = runner.invoke(
            app,
            ["page", "get", PAGE_ID, "--full"],
            env={"NOTION_API_KEY": "s"},
        )

        assert result.exit_code == 3
        error = json.loads(result.stderr)
        assert error["error_type"] == "object_not_found"


class TestBug2InvalidRegex:
    def test_edit_invalid_regex_exits_2(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        result = runner.invoke(
            app,
            ["page", "edit", PAGE_ID, "--find", "(unclosed", "--replace", "x", "--regex"],
            env={"NOTION_API_KEY": "s"},
        )

        assert result.exit_code == 2
        error = json.loads(result.stderr)
        assert error["error_type"] == "invalid_args"

    def test_grep_invalid_regex_exits_2(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        result = runner.invoke(
            app,
            ["page", "grep", PAGE_ID, "(unclosed", "--regex"],
            env={"NOTION_API_KEY": "s"},
        )

        assert result.exit_code == 2
        error = json.loads(result.stderr)
        assert error["error_type"] == "invalid_args"


class TestBug5NonDictBatchLine:
    def test_scalar_json_produces_clear_error(self) -> None:
        async def handler(item: dict[str, object]) -> dict[str, object]:
            return item

        lines = ["42\n", '"string"\n', '{"valid": true}\n']
        output_lines: list[str] = []
        error_lines: list[str] = []

        exit_code = asyncio.run(
            process_batch(
                lines=lines,
                handler=handler,
                fields=None,
                on_result=output_lines.append,
                on_error=error_lines.append,
            )
        )

        assert exit_code == ExitCode.ERROR
        assert len(output_lines) == 1
        assert len(error_lines) == 2
        assert "JSON object" in error_lines[0]
        assert "JSON object" in error_lines[1]


class TestBug6StaleNextCursor:
    def test_envelope_has_no_next_cursor(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.data_sources.query.return_value = {
            "results": [{"id": "r1"}],
            "has_more": False,
            "next_cursor": "stale_cursor",
        }

        result = runner.invoke(
            app,
            ["db", "query", PAGE_ID],
            env={"NOTION_API_KEY": "s"},
        )

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert "next_cursor" not in data
