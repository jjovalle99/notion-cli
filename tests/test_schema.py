import json

from typer.testing import CliRunner

from notion_cli.cli import app


def test_schema_page_create(runner: CliRunner) -> None:
    result = runner.invoke(app, ["schema", "page", "create"])

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["command"] == "page create"
    assert "description" in data
    param_names = {p["name"] for p in data["parameters"]}
    assert "parent" in param_names
    assert "title" in param_names


def test_schema_db_query(runner: CliRunner) -> None:
    result = runner.invoke(app, ["schema", "db", "query"])

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["command"] == "db query"
    param_names = {p["name"] for p in data["parameters"]}
    assert "db_id" in param_names


def test_schema_top_level_search(runner: CliRunner) -> None:
    result = runner.invoke(app, ["schema", "search"])

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["command"] == "search"


def test_schema_unknown_command(runner: CliRunner) -> None:
    result = runner.invoke(app, ["schema", "nonexistent"])

    assert result.exit_code == 2
    error = json.loads(result.stderr)
    assert error["error_type"] == "unknown_command"
