import json
from unittest.mock import AsyncMock

from typer.testing import CliRunner

from notion_cli.cli import app

DB_ID = "aabbccdd-1122-3344-5566-778899001122"


class TestDbQueryStreaming:
    def test_stream_ndjson_outputs_pages_incrementally(
        self, runner: CliRunner, mock_client: AsyncMock
    ) -> None:
        page1 = {
            "results": [{"id": "r1"}, {"id": "r2"}],
            "has_more": True,
            "next_cursor": "cur1",
        }
        page2 = {
            "results": [{"id": "r3"}],
            "has_more": False,
        }
        mock_client.data_sources.query.side_effect = [page1, page2]

        result = runner.invoke(
            app,
            ["db", "query", DB_ID, "--stream"],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        lines = [line for line in result.stdout.strip().split("\n") if line]
        assert len(lines) == 3
        assert json.loads(lines[0])["id"] == "r1"
        assert json.loads(lines[1])["id"] == "r2"
        assert json.loads(lines[2])["id"] == "r3"

    def test_stream_with_fields(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.data_sources.query.return_value = {
            "results": [{"id": "r1", "object": "page", "props": {}}],
            "has_more": False,
        }

        result = runner.invoke(
            app,
            ["db", "query", DB_ID, "--stream", "--fields", "id"],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        lines = [line for line in result.stdout.strip().split("\n") if line]
        assert json.loads(lines[0]) == {"id": "r1"}

    def test_stream_with_limit(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.data_sources.query.return_value = {
            "results": [{"id": f"r{i}"} for i in range(10)],
            "has_more": False,
        }

        result = runner.invoke(
            app,
            ["db", "query", DB_ID, "--stream", "--limit", "3"],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        lines = [line for line in result.stdout.strip().split("\n") if line]
        assert len(lines) == 3
