import json
from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from notion_cli.cli import app

runner = CliRunner()

MOCK_TEAMS = {
    "results": [
        {"id": "team-1", "name": "Engineering"},
        {"id": "team-2", "name": "Design"},
    ],
}


def _make_client(mock_client: AsyncMock) -> AsyncMock:
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    return mock_client


class TestTeamList:
    def test_list_teams(self) -> None:
        mock_client = _make_client(AsyncMock())
        mock_client.request.return_value = MOCK_TEAMS

        with patch("notion_client.AsyncClient", return_value=mock_client):
            result = runner.invoke(app, ["team", "list"], env={"NOTION_API_KEY": "secret"})

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert len(data["results"]) == 2
