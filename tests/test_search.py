import json
from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from notion_cli.cli import app

runner = CliRunner()


def test_search_returns_results() -> None:
    mock_client = AsyncMock()
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
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("notion_cli.commands.search.AsyncClient", return_value=mock_client):
        result = runner.invoke(app, ["search", "test query"], env={"NOTION_API_KEY": "secret"})

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert len(data["results"]) == 1
    assert data["results"][0]["id"] == "abc-123"


def test_search_empty_results() -> None:
    mock_client = AsyncMock()
    mock_client.search.return_value = {"results": [], "has_more": False}
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("notion_cli.commands.search.AsyncClient", return_value=mock_client):
        result = runner.invoke(app, ["search", "nothing"], env={"NOTION_API_KEY": "secret"})

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["results"] == []


def test_search_passes_query_to_api() -> None:
    mock_client = AsyncMock()
    mock_client.search.return_value = {"results": [], "has_more": False}
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("notion_cli.commands.search.AsyncClient", return_value=mock_client):
        runner.invoke(app, ["search", "my query"], env={"NOTION_API_KEY": "secret"})

    mock_client.search.assert_called_once()
    call_kwargs = mock_client.search.call_args
    assert call_kwargs.kwargs.get("query") == "my query"


def test_search_without_token_fails() -> None:
    result = runner.invoke(app, ["search", "test"], env={})
    assert result.exit_code == 2


def test_search_with_explicit_token() -> None:
    mock_client = AsyncMock()
    mock_client.search.return_value = {"results": [], "has_more": False}
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("notion_cli.commands.search.AsyncClient", return_value=mock_client) as mock_cls:
        result = runner.invoke(app, ["search", "test", "--token", "explicit_secret"], env={})

    assert result.exit_code == 0
    mock_cls.assert_called_once_with(auth="explicit_secret")


def test_search_filter_by_type() -> None:
    mock_client = AsyncMock()
    mock_client.search.return_value = {"results": [], "has_more": False}
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("notion_cli.commands.search.AsyncClient", return_value=mock_client):
        result = runner.invoke(
            app, ["search", "test", "--type", "page"], env={"NOTION_API_KEY": "secret"}
        )

    assert result.exit_code == 0
    call_kwargs = mock_client.search.call_args.kwargs
    assert call_kwargs["filter"] == {"property": "object", "value": "page"}
