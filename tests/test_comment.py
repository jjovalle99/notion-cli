import json
from unittest.mock import AsyncMock

from typer.testing import CliRunner

from notion_cli.cli import app

PAGE_ID = "aabbccdd-1122-3344-5566-778899001122"

MOCK_COMMENT = {
    "id": "comment-1",
    "object": "comment",
    "rich_text": [{"plain_text": "Hello"}],
}


class TestCommentAdd:
    def test_add_page_comment(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.comments.create.return_value = MOCK_COMMENT

        result = runner.invoke(
            app,
            ["comment", "add", PAGE_ID, "--body", "Great work!"],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        call_kwargs = mock_client.comments.create.call_args.kwargs
        assert call_kwargs["parent"] == {"page_id": PAGE_ID}


class TestCommentList:
    def test_list_comments(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.comments.list.return_value = {
            "results": [MOCK_COMMENT],
            "has_more": False,
        }

        result = runner.invoke(app, ["comment", "list", PAGE_ID], env={"NOTION_API_KEY": "secret"})

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert len(data["results"]) == 1
