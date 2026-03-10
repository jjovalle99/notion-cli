import json
from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from notion_cli.cli import app

runner = CliRunner()

DB_ID = "aabbccdd-1122-3344-5566-778899001122"
PARENT_ID = "11223344-5566-7788-99aa-bbccddeeff00"

MOCK_DB = {
    "id": DB_ID,
    "object": "database",
    "title": [{"plain_text": "My Database"}],
    "properties": {"Name": {"type": "title", "title": {}}},
}

MOCK_QUERY_RESULT = {
    "results": [
        {"id": "row-1", "object": "page", "properties": {}},
        {"id": "row-2", "object": "page", "properties": {}},
    ],
    "has_more": False,
}


def _make_client(mock_client: AsyncMock) -> AsyncMock:
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    return mock_client


class TestDbGet:
    def test_get_database(self) -> None:
        mock_client = _make_client(AsyncMock())
        mock_client.databases.retrieve.return_value = MOCK_DB

        with patch("notion_client.AsyncClient", return_value=mock_client):
            result = runner.invoke(app, ["db", "get", DB_ID], env={"NOTION_API_KEY": "secret"})

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["id"] == DB_ID


class TestDbQuery:
    def test_query_without_filter(self) -> None:
        mock_client = _make_client(AsyncMock())
        mock_client.databases.query.return_value = MOCK_QUERY_RESULT

        with patch("notion_client.AsyncClient", return_value=mock_client):
            result = runner.invoke(app, ["db", "query", DB_ID], env={"NOTION_API_KEY": "secret"})

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert len(data["results"]) == 2

    def test_query_with_filter(self) -> None:
        mock_client = _make_client(AsyncMock())
        mock_client.databases.query.return_value = MOCK_QUERY_RESULT

        filter_json = '{"property": "Status", "select": {"equals": "Done"}}'
        with patch("notion_client.AsyncClient", return_value=mock_client):
            result = runner.invoke(
                app,
                ["db", "query", DB_ID, "--filter", filter_json],
                env={"NOTION_API_KEY": "secret"},
            )

        assert result.exit_code == 0
        call_kwargs = mock_client.databases.query.call_args.kwargs
        assert call_kwargs["filter"] == json.loads(filter_json)

    def test_query_with_sort(self) -> None:
        mock_client = _make_client(AsyncMock())
        mock_client.databases.query.return_value = MOCK_QUERY_RESULT

        sort_json = '[{"property": "Created", "direction": "descending"}]'
        with patch("notion_client.AsyncClient", return_value=mock_client):
            result = runner.invoke(
                app,
                ["db", "query", DB_ID, "--sort", sort_json],
                env={"NOTION_API_KEY": "secret"},
            )

        assert result.exit_code == 0
        call_kwargs = mock_client.databases.query.call_args.kwargs
        assert call_kwargs["sorts"] == json.loads(sort_json)

    def test_query_paginates_automatically(self) -> None:
        mock_client = _make_client(AsyncMock())
        page1 = {
            "results": [{"id": "row-1"}],
            "has_more": True,
            "next_cursor": "cursor-abc",
        }
        page2 = {
            "results": [{"id": "row-2"}],
            "has_more": False,
        }
        mock_client.databases.query.side_effect = [page1, page2]

        with patch("notion_client.AsyncClient", return_value=mock_client):
            result = runner.invoke(app, ["db", "query", DB_ID], env={"NOTION_API_KEY": "secret"})

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert len(data["results"]) == 2
        assert data["results"][0]["id"] == "row-1"
        assert data["results"][1]["id"] == "row-2"
        assert mock_client.databases.query.call_count == 2
        second_call_kwargs = mock_client.databases.query.call_args_list[1].kwargs
        assert second_call_kwargs["start_cursor"] == "cursor-abc"


class TestDbCreate:
    def test_create_database(self) -> None:
        mock_client = _make_client(AsyncMock())
        mock_client.databases.create.return_value = MOCK_DB

        with patch("notion_client.AsyncClient", return_value=mock_client):
            result = runner.invoke(
                app,
                ["db", "create", "--parent", PARENT_ID, "--title", "New DB"],
                env={"NOTION_API_KEY": "secret"},
            )

        assert result.exit_code == 0
        call_kwargs = mock_client.databases.create.call_args.kwargs
        assert "parent" in call_kwargs


class TestDbUpdate:
    def test_update_title(self) -> None:
        mock_client = _make_client(AsyncMock())
        mock_client.databases.update.return_value = MOCK_DB

        with patch("notion_client.AsyncClient", return_value=mock_client):
            result = runner.invoke(
                app,
                ["db", "update", DB_ID, "--title", "Renamed DB"],
                env={"NOTION_API_KEY": "secret"},
            )

        assert result.exit_code == 0
