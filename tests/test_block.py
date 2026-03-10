import json
from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from notion_cli.cli import app

runner = CliRunner()

BLOCK_ID = "aabbccdd-1122-3344-5566-778899001122"
PARENT_ID = "11223344-5566-7788-99aa-bbccddeeff00"

MOCK_CHILDREN = {
    "results": [
        {"id": "child-1", "type": "paragraph", "paragraph": {"rich_text": []}},
        {"id": "child-2", "type": "heading_1", "heading_1": {"rich_text": []}},
    ],
    "has_more": False,
}

MOCK_APPEND = {
    "results": [{"id": "new-block-1", "type": "paragraph"}],
}


def _make_client(mock_client: AsyncMock) -> AsyncMock:
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    return mock_client


class TestBlockGet:
    def test_get_children(self) -> None:
        mock_client = _make_client(AsyncMock())
        mock_client.blocks.children.list.return_value = MOCK_CHILDREN

        with patch("notion_client.AsyncClient", return_value=mock_client):
            result = runner.invoke(
                app, ["block", "get", BLOCK_ID], env={"NOTION_API_KEY": "secret"}
            )

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert len(data["results"]) == 2

    def test_get_paginates_automatically(self) -> None:
        mock_client = _make_client(AsyncMock())
        page1 = {"results": [{"id": "child-1"}], "has_more": True, "next_cursor": "cur1"}
        page2 = {"results": [{"id": "child-2"}], "has_more": False}
        mock_client.blocks.children.list.side_effect = [page1, page2]

        with patch("notion_client.AsyncClient", return_value=mock_client):
            result = runner.invoke(
                app, ["block", "get", BLOCK_ID], env={"NOTION_API_KEY": "secret"}
            )

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert len(data["results"]) == 2
        assert mock_client.blocks.children.list.call_count == 2


class TestBlockAppend:
    def test_append_markdown(self) -> None:
        mock_client = _make_client(AsyncMock())
        mock_client.blocks.children.append.return_value = MOCK_APPEND

        with patch("notion_client.AsyncClient", return_value=mock_client):
            result = runner.invoke(
                app,
                ["block", "append", PARENT_ID, "--content", "# New heading\nSome text"],
                env={"NOTION_API_KEY": "secret"},
            )

        assert result.exit_code == 0
