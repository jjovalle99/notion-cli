import json
from unittest.mock import AsyncMock

from typer.testing import CliRunner

from notion_cli.cli import app


def test_search_returns_results(runner: CliRunner, mock_client: AsyncMock) -> None:
    mock_client.search.return_value = {
        "results": [
            {
                "id": "abc-123",
                "object": "page",
                "properties": {"title": {"title": [{"plain_text": "My Page"}]}},
            },
        ],
        "has_more": False,
    }

    result = runner.invoke(app, ["search", "test query"], env={"NOTION_API_KEY": "secret"})

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert len(data["results"]) == 1
    assert data["results"][0]["id"] == "abc-123"


def test_search_empty_results(runner: CliRunner, mock_client: AsyncMock) -> None:
    mock_client.search.return_value = {"results": [], "has_more": False}

    result = runner.invoke(app, ["search", "nothing"], env={"NOTION_API_KEY": "secret"})

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["results"] == []


def test_search_passes_query_to_api(runner: CliRunner, mock_client: AsyncMock) -> None:
    mock_client.search.return_value = {"results": [], "has_more": False}

    runner.invoke(app, ["search", "my query"], env={"NOTION_API_KEY": "secret"})

    mock_client.search.assert_called_once()
    call_kwargs = mock_client.search.call_args
    assert call_kwargs.kwargs.get("query") == "my query"


def test_search_without_token_fails(runner: CliRunner) -> None:
    result = runner.invoke(app, ["search", "test"], env={})
    assert result.exit_code == 2


def test_search_with_explicit_token(runner: CliRunner, mock_client: AsyncMock) -> None:
    mock_client.search.return_value = {"results": [], "has_more": False}

    result = runner.invoke(app, ["search", "test", "--token", "explicit_secret"], env={})

    assert result.exit_code == 0


def test_search_filter_by_type(runner: CliRunner, mock_client: AsyncMock) -> None:
    mock_client.search.return_value = {"results": [], "has_more": False}

    result = runner.invoke(
        app, ["search", "test", "--type", "page"], env={"NOTION_API_KEY": "secret"}
    )

    assert result.exit_code == 0
    call_kwargs = mock_client.search.call_args.kwargs
    assert call_kwargs["filter"] == {"property": "object", "value": "page"}


def test_search_paginates(runner: CliRunner, mock_client: AsyncMock) -> None:
    page1 = {"results": [{"id": "p1"}], "has_more": True, "next_cursor": "cur1"}
    page2 = {"results": [{"id": "p2"}], "has_more": False}
    mock_client.search.side_effect = [page1, page2]

    result = runner.invoke(app, ["search", "test"], env={"NOTION_API_KEY": "secret"})

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert len(data["results"]) == 2
    assert mock_client.search.call_count == 2


def test_search_with_limit(runner: CliRunner, mock_client: AsyncMock) -> None:
    mock_client.search.return_value = {
        "results": [{"id": f"p{i}"} for i in range(20)],
        "has_more": True,
        "next_cursor": "cur",
    }

    result = runner.invoke(
        app, ["search", "test", "--limit", "5"], env={"NOTION_API_KEY": "secret"}
    )

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert len(data["results"]) == 5
