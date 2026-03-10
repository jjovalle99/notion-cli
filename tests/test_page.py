import json
from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from notion_cli.cli import app

runner = CliRunner()

PAGE_ID = "aabbccdd-1122-3344-5566-778899001122"
PARENT_ID = "11223344-5566-7788-99aa-bbccddeeff00"
NEW_PARENT_ID = "ffeeddcc-bbaa-9988-7766-554433221100"

MOCK_PAGE = {
    "id": PAGE_ID,
    "object": "page",
    "properties": {"title": {"title": [{"plain_text": "Test Page"}]}},
    "url": "https://www.notion.so/Test-Page-aabbccdd112233445566778899001122",
}


def _make_client(mock_client: AsyncMock) -> AsyncMock:
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    return mock_client


class TestPageGet:
    def test_get_by_id(self) -> None:
        mock_client = _make_client(AsyncMock())
        mock_client.pages.retrieve.return_value = MOCK_PAGE

        with patch("notion_client.AsyncClient", return_value=mock_client):
            result = runner.invoke(app, ["page", "get", PAGE_ID], env={"NOTION_API_KEY": "secret"})

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["id"] == PAGE_ID

    def test_get_by_url(self) -> None:
        mock_client = _make_client(AsyncMock())
        mock_client.pages.retrieve.return_value = MOCK_PAGE

        with patch("notion_client.AsyncClient", return_value=mock_client):
            result = runner.invoke(
                app,
                ["page", "get", "https://www.notion.so/My-Page-abc123def456abc123def456abc123de"],
                env={"NOTION_API_KEY": "secret"},
            )

        assert result.exit_code == 0
        mock_client.pages.retrieve.assert_called_once_with("abc123de-f456-abc1-23de-f456abc123de")


class TestPageCreate:
    def test_create_with_title(self) -> None:
        mock_client = _make_client(AsyncMock())
        mock_client.pages.create.return_value = MOCK_PAGE

        with patch("notion_client.AsyncClient", return_value=mock_client):
            result = runner.invoke(
                app,
                ["page", "create", "--parent", PARENT_ID, "--title", "New Page"],
                env={"NOTION_API_KEY": "secret"},
            )

        assert result.exit_code == 0
        call_kwargs = mock_client.pages.create.call_args.kwargs
        assert "parent" in call_kwargs

    def test_create_with_markdown_content(self) -> None:
        mock_client = _make_client(AsyncMock())
        mock_client.pages.create.return_value = MOCK_PAGE

        with patch("notion_client.AsyncClient", return_value=mock_client):
            result = runner.invoke(
                app,
                [
                    "page",
                    "create",
                    "--parent",
                    PARENT_ID,
                    "--title",
                    "New Page",
                    "--content",
                    "# Heading\nSome text",
                ],
                env={"NOTION_API_KEY": "secret"},
            )

        assert result.exit_code == 0
        call_kwargs = mock_client.pages.create.call_args.kwargs
        assert "markdown" in call_kwargs


class TestPageUpdate:
    def test_update_title(self) -> None:
        mock_client = _make_client(AsyncMock())
        mock_client.pages.update.return_value = MOCK_PAGE

        with patch("notion_client.AsyncClient", return_value=mock_client):
            result = runner.invoke(
                app,
                ["page", "update", PAGE_ID, "--title", "Updated Title"],
                env={"NOTION_API_KEY": "secret"},
            )

        assert result.exit_code == 0

    def test_update_archive(self) -> None:
        mock_client = _make_client(AsyncMock())
        mock_client.pages.update.return_value = {**MOCK_PAGE, "archived": True}

        with patch("notion_client.AsyncClient", return_value=mock_client):
            result = runner.invoke(
                app,
                ["page", "update", PAGE_ID, "--archive"],
                env={"NOTION_API_KEY": "secret"},
            )

        assert result.exit_code == 0


class TestPageMove:
    def test_move_page(self) -> None:
        mock_client = _make_client(AsyncMock())
        mock_client.pages.update.return_value = MOCK_PAGE

        with patch("notion_client.AsyncClient", return_value=mock_client):
            result = runner.invoke(
                app,
                ["page", "move", PAGE_ID, "--to", NEW_PARENT_ID],
                env={"NOTION_API_KEY": "secret"},
            )

        assert result.exit_code == 0
        call_kwargs = mock_client.pages.update.call_args.kwargs
        assert "parent" in call_kwargs
