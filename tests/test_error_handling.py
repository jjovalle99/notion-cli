import json
from unittest.mock import AsyncMock

from notion_client.errors import APIResponseError
from typer.testing import CliRunner

from notion_cli.cli import app


def _make_api_error(code: str, status: int, message: str) -> APIResponseError:
    return APIResponseError(
        code=code, status=status, message=message, headers={}, raw_body_text=""
    )


class TestNotFoundError:
    def test_page_not_found_returns_json_error(
        self, runner: CliRunner, mock_client: AsyncMock
    ) -> None:
        mock_client.pages.retrieve.side_effect = _make_api_error(
            "object_not_found", 404, "Could not find page"
        )

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
    def test_bad_token_returns_json_error(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.search.side_effect = _make_api_error(
            "unauthorized", 401, "API token is invalid"
        )

        result = runner.invoke(app, ["search", "test"], env={"NOTION_API_KEY": "bad_token"})

        assert result.exit_code == 4
        error = json.loads(result.output)
        assert error["error_type"] == "unauthorized"


class TestRateLimitedError:
    def test_rate_limited_returns_json_error(
        self, runner: CliRunner, mock_client: AsyncMock
    ) -> None:
        mock_client.search.side_effect = _make_api_error("rate_limited", 429, "Rate limited")

        result = runner.invoke(app, ["search", "test"], env={"NOTION_API_KEY": "secret"})

        assert result.exit_code == 5
        error = json.loads(result.output)
        assert error["error_type"] == "rate_limited"


class TestGenericApiError:
    def test_internal_server_error_returns_json_error(
        self, runner: CliRunner, mock_client: AsyncMock
    ) -> None:
        mock_client.search.side_effect = _make_api_error(
            "internal_server_error", 500, "Internal error"
        )

        result = runner.invoke(app, ["search", "test"], env={"NOTION_API_KEY": "secret"})

        assert result.exit_code == 1
        error = json.loads(result.output)
        assert error["error_type"] == "internal_server_error"


class TestUnexpectedError:
    def test_connection_error_returns_json(
        self, runner: CliRunner, mock_client: AsyncMock
    ) -> None:
        mock_client.search.side_effect = ConnectionError("Connection refused")

        result = runner.invoke(app, ["search", "test"], env={"NOTION_API_KEY": "secret"})

        assert result.exit_code == 1
        error = json.loads(result.output)
        assert error["error_type"] == "unexpected"
        assert "Connection refused" in error["message"]


class TestRestrictedResourceError:
    def test_restricted_resource_returns_permission_exit_code(
        self, runner: CliRunner, mock_client: AsyncMock
    ) -> None:
        mock_client.search.side_effect = _make_api_error(
            "restricted_resource", 403, "Resource is restricted"
        )

        result = runner.invoke(app, ["search", "test"], env={"NOTION_API_KEY": "secret"})

        assert result.exit_code == 4
        error = json.loads(result.output)
        assert error["error_type"] == "restricted_resource"


class TestRequestTimeoutError:
    def test_sdk_timeout_returns_json_error(
        self, runner: CliRunner, mock_client: AsyncMock
    ) -> None:
        from notion_client.errors import RequestTimeoutError

        mock_client.search.side_effect = RequestTimeoutError()

        result = runner.invoke(app, ["search", "test"], env={"NOTION_API_KEY": "secret"})

        assert result.exit_code == 1
        error = json.loads(result.output)
        assert error["error_type"] == "timeout"


class TestBadJsonInput:
    def test_malformed_filter_returns_json_error(
        self, runner: CliRunner, mock_client: AsyncMock
    ) -> None:
        result = runner.invoke(
            app,
            ["db", "query", "aabbccdd-1122-3344-5566-778899001122", "--filter", "{bad json}"],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 2
        error = json.loads(result.output)
        assert error["error_type"] == "invalid_json"

    def test_malformed_properties_returns_json_error(
        self, runner: CliRunner, mock_client: AsyncMock
    ) -> None:
        result = runner.invoke(
            app,
            ["page", "update", "aabbccdd-1122-3344-5566-778899001122", "--properties", "nope"],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 2
        error = json.loads(result.output)
        assert error["error_type"] == "invalid_json"

    def test_wrong_json_type_returns_error(
        self, runner: CliRunner, mock_client: AsyncMock
    ) -> None:
        result = runner.invoke(
            app,
            [
                "page",
                "update",
                "aabbccdd-1122-3344-5566-778899001122",
                "--properties",
                '["array"]',
            ],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 2
        error = json.loads(result.output)
        assert error["error_type"] == "invalid_json"
        assert "object" in error["message"]

    def test_children_dict_instead_of_list_returns_error(
        self, runner: CliRunner, mock_client: AsyncMock
    ) -> None:
        result = runner.invoke(
            app,
            [
                "block",
                "append",
                "aabbccdd-1122-3344-5566-778899001122",
                "--children",
                '{"key": "value"}',
            ],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 2
        error = json.loads(result.output)
        assert error["error_type"] == "invalid_json"
        assert "array" in error["message"]


class TestVersionFlag:
    def test_version_flag(self, runner: CliRunner) -> None:
        result = runner.invoke(app, ["--version"])

        assert result.exit_code == 0
        assert "notion-cli" in result.output


class TestLimitValidation:
    def test_limit_zero_returns_bad_args(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        result = runner.invoke(
            app,
            ["search", "test", "--limit", "0"],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 2
        error = json.loads(result.output)
        assert error["error_type"] == "invalid_args"

    def test_limit_negative_returns_bad_args(
        self, runner: CliRunner, mock_client: AsyncMock
    ) -> None:
        result = runner.invoke(
            app,
            ["db", "query", "aabbccdd-1122-3344-5566-778899001122", "--limit", "-5"],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 2
        error = json.loads(result.output)
        assert error["error_type"] == "invalid_args"

    def test_user_list_limit_zero_returns_bad_args(
        self, runner: CliRunner, mock_client: AsyncMock
    ) -> None:
        result = runner.invoke(
            app,
            ["user", "list", "--limit", "0"],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 2
