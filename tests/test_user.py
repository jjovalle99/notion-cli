import json
from unittest.mock import AsyncMock

from typer.testing import CliRunner

from notion_cli.cli import app

USER_ID = "aabbccdd-1122-3344-5566-778899001122"

MOCK_USER = {"id": USER_ID, "object": "user", "name": "Test User", "type": "person"}
MOCK_BOT = {"id": "bot-123", "object": "user", "name": "My Integration", "type": "bot"}


class TestUserList:
    def test_list_users(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.users.list.return_value = {
            "results": [MOCK_USER, MOCK_BOT],
            "has_more": False,
        }

        result = runner.invoke(app, ["user", "list"], env={"NOTION_API_KEY": "secret"})

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert len(data["results"]) == 2

    def test_list_with_limit(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.users.list.return_value = {
            "results": [MOCK_USER, MOCK_BOT, {**MOCK_USER, "id": "extra"}],
            "has_more": False,
        }

        result = runner.invoke(
            app, ["user", "list", "--limit", "2"], env={"NOTION_API_KEY": "secret"}
        )

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert len(data["results"]) == 2
        call_kwargs = mock_client.users.list.call_args.kwargs
        assert call_kwargs["page_size"] == 2

    def test_list_paginates(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        page1 = {"results": [MOCK_USER], "has_more": True, "next_cursor": "cursor-abc"}
        page2 = {"results": [MOCK_BOT], "has_more": False}
        mock_client.users.list.side_effect = [page1, page2]

        result = runner.invoke(app, ["user", "list"], env={"NOTION_API_KEY": "secret"})

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert len(data["results"]) == 2
        assert mock_client.users.list.call_count == 2


class TestUserGet:
    def test_get_user(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.users.retrieve.return_value = MOCK_USER

        result = runner.invoke(app, ["user", "get", USER_ID], env={"NOTION_API_KEY": "secret"})

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["name"] == "Test User"

    def test_get_user_extracts_id_from_url(
        self, runner: CliRunner, mock_client: AsyncMock
    ) -> None:
        mock_client.users.retrieve.return_value = MOCK_USER

        result = runner.invoke(
            app,
            ["user", "get", "https://notion.so/aabbccdd112233445566778899001122"],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        mock_client.users.retrieve.assert_called_once_with(USER_ID)


class TestUserMe:
    def test_me(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.users.me.return_value = MOCK_BOT

        result = runner.invoke(app, ["user", "me"], env={"NOTION_API_KEY": "secret"})

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["type"] == "bot"
