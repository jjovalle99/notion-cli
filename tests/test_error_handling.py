import json
from unittest.mock import AsyncMock, patch

from notion_client.errors import APIResponseError
from typer.testing import CliRunner

from notion_cli.cli import app

runner = CliRunner()


def _make_client(mock_client: AsyncMock) -> AsyncMock:
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    return mock_client


def _make_api_error(code: str, status: int, message: str) -> APIResponseError:
    return APIResponseError(
        code=code, status=status, message=message, headers={}, raw_body_text=""
    )


class TestNotFoundError:
    def test_page_not_found_returns_json_error(self) -> None:
        mock_client = _make_client(AsyncMock())
        mock_client.pages.retrieve.side_effect = _make_api_error(
            "object_not_found", 404, "Could not find page"
        )

        with patch("notion_client.AsyncClient", return_value=mock_client):
            result = runner.invoke(
                app,
                ["page", "get", "aabbccdd-1122-3344-5566-778899001122"],
                env={"NOTION_API_KEY": "secret"},
            )

        assert result.exit_code == 3
        error = json.loads(result.output)
        assert error["error_type"] == "object_not_found"
        assert "Could not find page" in error["message"]


class TestUnauthorizedError:
    def test_bad_token_returns_json_error(self) -> None:
        mock_client = _make_client(AsyncMock())
        mock_client.search.side_effect = _make_api_error(
            "unauthorized", 401, "API token is invalid"
        )

        with patch("notion_client.AsyncClient", return_value=mock_client):
            result = runner.invoke(
                app,
                ["search", "test"],
                env={"NOTION_API_KEY": "bad_token"},
            )

        assert result.exit_code == 4
        error = json.loads(result.output)
        assert error["error_type"] == "unauthorized"


class TestRateLimitedError:
    def test_rate_limited_returns_json_error(self) -> None:
        mock_client = _make_client(AsyncMock())
        mock_client.search.side_effect = _make_api_error("rate_limited", 429, "Rate limited")

        with patch("notion_client.AsyncClient", return_value=mock_client):
            result = runner.invoke(
                app,
                ["search", "test"],
                env={"NOTION_API_KEY": "secret"},
            )

        assert result.exit_code == 5
        error = json.loads(result.output)
        assert error["error_type"] == "rate_limited"


class TestGenericApiError:
    def test_internal_server_error_returns_json_error(self) -> None:
        mock_client = _make_client(AsyncMock())
        mock_client.search.side_effect = _make_api_error(
            "internal_server_error", 500, "Internal error"
        )

        with patch("notion_client.AsyncClient", return_value=mock_client):
            result = runner.invoke(
                app,
                ["search", "test"],
                env={"NOTION_API_KEY": "secret"},
            )

        assert result.exit_code == 1
        error = json.loads(result.output)
        assert error["error_type"] == "internal_server_error"
