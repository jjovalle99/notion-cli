import json
from unittest.mock import AsyncMock

from typer.testing import CliRunner

from notion_cli.cli import app

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


class TestDbGet:
    def test_get_database(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.databases.retrieve.return_value = MOCK_DB

        result = runner.invoke(app, ["db", "get", DB_ID], env={"NOTION_API_KEY": "secret"})

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["id"] == DB_ID


class TestDbQuery:
    def test_query_without_filter(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.data_sources.query.return_value = MOCK_QUERY_RESULT

        result = runner.invoke(app, ["db", "query", DB_ID], env={"NOTION_API_KEY": "secret"})

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert len(data["results"]) == 2

    def test_query_with_filter(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.data_sources.query.return_value = MOCK_QUERY_RESULT
        filter_json = '{"property": "Status", "select": {"equals": "Done"}}'

        result = runner.invoke(
            app,
            ["db", "query", DB_ID, "--filter", filter_json],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        call_kwargs = mock_client.data_sources.query.call_args.kwargs
        assert call_kwargs["filter"] == json.loads(filter_json)

    def test_query_with_sort(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.data_sources.query.return_value = MOCK_QUERY_RESULT
        sort_json = '[{"property": "Created", "direction": "descending"}]'

        result = runner.invoke(
            app,
            ["db", "query", DB_ID, "--sort", sort_json],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        call_kwargs = mock_client.data_sources.query.call_args.kwargs
        assert call_kwargs["sorts"] == json.loads(sort_json)

    def test_query_paginates_automatically(
        self, runner: CliRunner, mock_client: AsyncMock
    ) -> None:
        page1 = {"results": [{"id": "row-1"}], "has_more": True, "next_cursor": "cursor-abc"}
        page2 = {"results": [{"id": "row-2"}], "has_more": False}
        mock_client.data_sources.query.side_effect = [page1, page2]

        result = runner.invoke(app, ["db", "query", DB_ID], env={"NOTION_API_KEY": "secret"})

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert len(data["results"]) == 2
        assert data["results"][0]["id"] == "row-1"
        assert data["results"][1]["id"] == "row-2"
        assert mock_client.data_sources.query.call_count == 2
        second_call_kwargs = mock_client.data_sources.query.call_args_list[1].kwargs
        assert second_call_kwargs["start_cursor"] == "cursor-abc"

    def test_query_stops_on_missing_next_cursor(
        self, runner: CliRunner, mock_client: AsyncMock
    ) -> None:
        page1 = {"results": [{"id": "row-1"}], "has_more": True}
        mock_client.data_sources.query.return_value = page1

        result = runner.invoke(app, ["db", "query", DB_ID], env={"NOTION_API_KEY": "secret"})

        assert result.exit_code == 0
        assert mock_client.data_sources.query.call_count == 1

    def test_query_stops_on_empty_results(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        page1 = {"results": [], "has_more": True, "next_cursor": "cur"}
        mock_client.data_sources.query.return_value = page1

        result = runner.invoke(app, ["db", "query", DB_ID], env={"NOTION_API_KEY": "secret"})

        assert result.exit_code == 0
        assert mock_client.data_sources.query.call_count == 1

    def test_query_with_limit(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        page1 = {
            "results": [{"id": f"r{i}"} for i in range(100)],
            "has_more": True,
            "next_cursor": "c",
        }
        page2 = {"results": [{"id": f"r{i}"} for i in range(100, 200)], "has_more": False}
        mock_client.data_sources.query.side_effect = [page1, page2]

        result = runner.invoke(
            app, ["db", "query", DB_ID, "--limit", "50"], env={"NOTION_API_KEY": "secret"}
        )

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert len(data["results"]) == 50


class TestDbCreate:
    def test_create_database(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.data_sources.create.return_value = MOCK_DB

        result = runner.invoke(
            app,
            ["db", "create", "--parent", PARENT_ID, "--title", "New DB"],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        call_kwargs = mock_client.data_sources.create.call_args.kwargs
        assert "parent" in call_kwargs

    def test_create_with_properties(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.data_sources.create.return_value = MOCK_DB
        props_json = '{"Status": {"select": {}}}'

        result = runner.invoke(
            app,
            [
                "db",
                "create",
                "--parent",
                PARENT_ID,
                "--title",
                "New DB",
                "--properties",
                props_json,
            ],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        call_kwargs = mock_client.data_sources.create.call_args.kwargs
        assert "Name" in call_kwargs["properties"]
        assert "Status" in call_kwargs["properties"]


class TestDbUpdate:
    def test_update_title(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.data_sources.update.return_value = MOCK_DB

        result = runner.invoke(
            app,
            ["db", "update", DB_ID, "--title", "Renamed DB"],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0

    def test_update_properties(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.data_sources.update.return_value = MOCK_DB
        props_json = '{"Priority": {"select": {}}}'

        result = runner.invoke(
            app,
            ["db", "update", DB_ID, "--properties", props_json],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        call_kwargs = mock_client.data_sources.update.call_args.kwargs
        assert "Priority" in call_kwargs["properties"]
