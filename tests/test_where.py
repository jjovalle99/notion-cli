import json
from unittest.mock import AsyncMock

import pytest
from typer.testing import CliRunner

from notion_cli.cli import app
from notion_cli.parsing import parse_where

DB_ID = "aabbccdd-1122-3344-5566-778899001122"


class TestParseWhere:
    def test_select_equals(self) -> None:
        result = parse_where("Status = Done", "select")
        assert result == {"property": "Status", "select": {"equals": "Done"}}

    def test_select_not_equals(self) -> None:
        result = parse_where("Status != Done", "select")
        assert result == {"property": "Status", "select": {"does_not_equal": "Done"}}

    def test_rich_text_contains(self) -> None:
        result = parse_where("Name contains Report", "rich_text")
        assert result == {"property": "Name", "rich_text": {"contains": "Report"}}

    def test_number_greater_than(self) -> None:
        result = parse_where("Priority > 3", "number")
        assert result == {"property": "Priority", "number": {"greater_than": 3}}

    def test_number_less_equal(self) -> None:
        result = parse_where("Score <= 100", "number")
        assert result == {"property": "Score", "number": {"less_than_or_equal_to": 100}}

    def test_checkbox_equals_true(self) -> None:
        result = parse_where("Done = true", "checkbox")
        assert result == {"property": "Done", "checkbox": {"equals": True}}

    def test_checkbox_equals_false(self) -> None:
        result = parse_where("Done = false", "checkbox")
        assert result == {"property": "Done", "checkbox": {"equals": False}}

    def test_date_before(self) -> None:
        result = parse_where("Due before 2024-12-31", "date")
        assert result == {"property": "Due", "date": {"before": "2024-12-31"}}

    def test_date_after(self) -> None:
        result = parse_where("Due after 2024-01-01", "date")
        assert result == {"property": "Due", "date": {"after": "2024-01-01"}}

    def test_title_equals(self) -> None:
        result = parse_where("Name = Meeting Notes", "title")
        assert result == {"property": "Name", "title": {"equals": "Meeting Notes"}}

    def test_status_equals(self) -> None:
        result = parse_where("Status = In Progress", "status")
        assert result == {"property": "Status", "status": {"equals": "In Progress"}}

    def test_property_with_spaces(self) -> None:
        result = parse_where("Due Date before 2024-12-31", "date")
        assert result == {"property": "Due Date", "date": {"before": "2024-12-31"}}

    def test_invalid_expression(self) -> None:
        with pytest.raises(ValueError, match="Cannot parse"):
            parse_where("justoneword", "select")


class TestDbQueryWhere:
    def test_where_fetches_schema_and_filters(
        self, runner: CliRunner, mock_client: AsyncMock
    ) -> None:
        mock_client.databases.retrieve.return_value = {
            "properties": {
                "Status": {"type": "select"},
                "Name": {"type": "title"},
            }
        }
        mock_client.data_sources.query.return_value = {
            "results": [{"id": "r1"}],
            "has_more": False,
        }

        result = runner.invoke(
            app,
            ["db", "query", DB_ID, "--where", "Status = Done"],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        call_kwargs = mock_client.data_sources.query.call_args.kwargs
        assert call_kwargs["filter"] == {"property": "Status", "select": {"equals": "Done"}}

    def test_multiple_where_creates_and_filter(
        self, runner: CliRunner, mock_client: AsyncMock
    ) -> None:
        mock_client.databases.retrieve.return_value = {
            "properties": {
                "Status": {"type": "select"},
                "Priority": {"type": "number"},
            }
        }
        mock_client.data_sources.query.return_value = {
            "results": [],
            "has_more": False,
        }

        result = runner.invoke(
            app,
            ["db", "query", DB_ID, "--where", "Status = Done", "--where", "Priority > 3"],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        call_kwargs = mock_client.data_sources.query.call_args.kwargs
        filt = call_kwargs["filter"]
        assert "and" in filt
        assert len(filt["and"]) == 2

    def test_where_and_filter_conflict(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        result = runner.invoke(
            app,
            [
                "db",
                "query",
                DB_ID,
                "--where",
                "Status = Done",
                "--filter",
                '{"property": "Status", "select": {"equals": "Done"}}',
            ],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 2
        error = json.loads(result.stderr)
        assert error["error_type"] == "conflicting_args"

    def test_unknown_property_emits_warning(
        self, runner: CliRunner, mock_client: AsyncMock
    ) -> None:
        mock_client.databases.retrieve.return_value = {
            "properties": {"Status": {"type": "select"}}
        }
        mock_client.data_sources.query.return_value = {"results": [], "has_more": False}

        result = runner.invoke(
            app,
            ["db", "query", DB_ID, "--where", "NonExistent = Done"],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        assert "unresolved_property" in result.stderr
