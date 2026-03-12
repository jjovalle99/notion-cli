import json
from unittest.mock import AsyncMock

from typer.testing import CliRunner

from notion_cli.cli import app

MOCK_PAGE = {"id": "abc-123", "object": "page"}


class TestApi:
    def test_get_request(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.request.return_value = MOCK_PAGE

        result = runner.invoke(
            app,
            ["api", "GET", "/pages/abc-123"],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["id"] == "abc-123"
        mock_client.request.assert_called_once_with(path="/pages/abc-123", method="GET")

    def test_post_with_body(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.request.return_value = MOCK_PAGE
        body = '{"parent": {"page_id": "x"}, "properties": {}}'

        result = runner.invoke(
            app,
            ["api", "POST", "/pages", "--body", body],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        mock_client.request.assert_called_once_with(
            path="/pages",
            method="POST",
            body={"parent": {"page_id": "x"}, "properties": {}},
        )

    def test_method_case_insensitive(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.request.return_value = MOCK_PAGE

        result = runner.invoke(
            app,
            ["api", "get", "/pages/abc-123"],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        mock_client.request.assert_called_once_with(path="/pages/abc-123", method="GET")

    def test_invalid_method_rejected(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        result = runner.invoke(
            app,
            ["api", "FETCH", "/pages/abc-123"],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 2
        error = json.loads(result.stderr)
        assert error["error_type"] == "invalid_args"

    def test_dry_run(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        result = runner.invoke(
            app,
            ["api", "POST", "/pages", "--body", '{"properties": {}}', "--dry-run"],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["dry_run"] is True
        assert data["command"] == "api"
        assert data["payload"]["method"] == "POST"
        assert data["payload"]["path"] == "/pages"
        mock_client.request.assert_not_called()

    def test_fields_projection(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.request.return_value = MOCK_PAGE

        result = runner.invoke(
            app,
            ["api", "GET", "/pages/abc-123", "--fields", "id"],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data == {"id": "abc-123"}
