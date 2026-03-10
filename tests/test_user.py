import json
from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from notion_cli.cli import app

runner = CliRunner()

USER_ID = "aabbccdd-1122-3344-5566-778899001122"

MOCK_USER = {"id": USER_ID, "object": "user", "name": "Test User", "type": "person"}
MOCK_BOT = {"id": "bot-123", "object": "user", "name": "My Integration", "type": "bot"}


def _make_client(mock_client: AsyncMock) -> AsyncMock:
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    return mock_client


class TestUserList:
    def test_list_users(self) -> None:
        mock_client = _make_client(AsyncMock())
        mock_client.users.list.return_value = {
            "results": [MOCK_USER, MOCK_BOT],
            "has_more": False,
        }

        with patch("notion_cli.commands.user.AsyncClient", return_value=mock_client):
            result = runner.invoke(app, ["user", "list"], env={"NOTION_API_KEY": "secret"})

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert len(data["results"]) == 2


class TestUserGet:
    def test_get_user(self) -> None:
        mock_client = _make_client(AsyncMock())
        mock_client.users.retrieve.return_value = MOCK_USER

        with patch("notion_cli.commands.user.AsyncClient", return_value=mock_client):
            result = runner.invoke(app, ["user", "get", USER_ID], env={"NOTION_API_KEY": "secret"})

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["name"] == "Test User"


class TestUserMe:
    def test_me(self) -> None:
        mock_client = _make_client(AsyncMock())
        mock_client.users.me.return_value = MOCK_BOT

        with patch("notion_cli.commands.user.AsyncClient", return_value=mock_client):
            result = runner.invoke(app, ["user", "me"], env={"NOTION_API_KEY": "secret"})

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["type"] == "bot"
