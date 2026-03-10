import json
from unittest.mock import AsyncMock

from typer.testing import CliRunner

from notion_cli.cli import app

MOCK_TEAMS = {
    "results": [
        {"id": "team-1", "name": "Engineering"},
        {"id": "team-2", "name": "Design"},
    ],
}


class TestTeamList:
    def test_list_teams(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.request.return_value = MOCK_TEAMS

        result = runner.invoke(app, ["team", "list"], env={"NOTION_API_KEY": "secret"})

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert len(data["results"]) == 2
