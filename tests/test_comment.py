import json
from unittest.mock import AsyncMock

from typer.testing import CliRunner

from notion_cli.cli import app

PAGE_ID = "aabbccdd-1122-3344-5566-778899001122"
DISCUSSION_ID = "dddddddd-1111-2222-3333-444444444444"

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

    def test_add_with_rich_text(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.comments.create.return_value = MOCK_COMMENT
        rt = '[{"text": {"content": "bold"}, "annotations": {"bold": true}}]'

        result = runner.invoke(
            app,
            ["comment", "add", PAGE_ID, "--rich-text", rt],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        call_kwargs = mock_client.comments.create.call_args.kwargs
        assert call_kwargs["rich_text"][0]["annotations"]["bold"] is True

    def test_add_body_and_rich_text_conflict(
        self, runner: CliRunner, mock_client: AsyncMock
    ) -> None:
        result = runner.invoke(
            app,
            ["comment", "add", PAGE_ID, "--body", "hi", "--rich-text", "[]"],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 2

    def test_add_empty_body_with_rich_text_is_conflict(
        self, runner: CliRunner, mock_client: AsyncMock
    ) -> None:
        result = runner.invoke(
            app,
            [
                "comment",
                "add",
                PAGE_ID,
                "--body",
                "",
                "--rich-text",
                '[{"text": {"content": "x"}}]',
            ],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 2
        error = json.loads(result.stderr)
        assert error["error_type"] == "conflicting_args"


class TestCommentReply:
    def test_reply_with_body(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.comments.create.return_value = MOCK_COMMENT

        result = runner.invoke(
            app,
            ["comment", "reply", DISCUSSION_ID, "--body", "Agreed!"],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        call_kwargs = mock_client.comments.create.call_args.kwargs
        assert call_kwargs["discussion_id"] == DISCUSSION_ID
        assert "parent" not in call_kwargs

    def test_reply_with_rich_text(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.comments.create.return_value = MOCK_COMMENT
        rt = '[{"text": {"content": "formatted"}}]'

        result = runner.invoke(
            app,
            ["comment", "reply", DISCUSSION_ID, "--rich-text", rt],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        call_kwargs = mock_client.comments.create.call_args.kwargs
        assert call_kwargs["discussion_id"] == DISCUSSION_ID

    def test_reply_requires_body_or_rich_text(
        self, runner: CliRunner, mock_client: AsyncMock
    ) -> None:
        result = runner.invoke(
            app,
            ["comment", "reply", DISCUSSION_ID],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 2


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

    def test_list_with_fields(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.comments.list.return_value = {
            "results": [MOCK_COMMENT],
            "has_more": False,
        }

        result = runner.invoke(
            app,
            ["comment", "list", PAGE_ID, "--fields", "id"],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["results"] == [{"id": "comment-1"}]

    def test_list_with_limit(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.comments.list.return_value = {
            "results": [
                {"id": "c-1", "object": "comment"},
                {"id": "c-2", "object": "comment"},
                {"id": "c-3", "object": "comment"},
            ],
            "has_more": False,
        }

        result = runner.invoke(
            app, ["comment", "list", PAGE_ID, "--limit", "2"], env={"NOTION_API_KEY": "secret"}
        )

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert len(data["results"]) == 2

    def test_list_limit_sets_page_size(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.comments.list.return_value = {
            "results": [MOCK_COMMENT],
            "has_more": False,
        }

        runner.invoke(
            app, ["comment", "list", PAGE_ID, "--limit", "5"], env={"NOTION_API_KEY": "secret"}
        )

        call_kwargs = mock_client.comments.list.call_args.kwargs
        assert call_kwargs["page_size"] == 5

    def test_list_limit_stops_pagination_early(
        self, runner: CliRunner, mock_client: AsyncMock
    ) -> None:
        page1 = {"results": [MOCK_COMMENT], "has_more": True, "next_cursor": "cur1"}
        page2 = {
            "results": [{"id": "c-2", "object": "comment"}],
            "has_more": True,
            "next_cursor": "cur2",
        }
        mock_client.comments.list.side_effect = [page1, page2]

        result = runner.invoke(
            app, ["comment", "list", PAGE_ID, "--limit", "2"], env={"NOTION_API_KEY": "secret"}
        )

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert len(data["results"]) == 2
        assert mock_client.comments.list.call_count == 2

    def test_list_limit_zero_rejected(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        result = runner.invoke(
            app, ["comment", "list", PAGE_ID, "--limit", "0"], env={"NOTION_API_KEY": "secret"}
        )

        assert result.exit_code == 2
        error = json.loads(result.stderr)
        assert error["error_type"] == "invalid_args"

    def test_list_paginates(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        page1 = {"results": [MOCK_COMMENT], "has_more": True, "next_cursor": "cursor-abc"}
        page2 = {
            "results": [{"id": "comment-2", "object": "comment", "rich_text": []}],
            "has_more": False,
        }
        mock_client.comments.list.side_effect = [page1, page2]

        result = runner.invoke(app, ["comment", "list", PAGE_ID], env={"NOTION_API_KEY": "secret"})

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert len(data["results"]) == 2
        assert mock_client.comments.list.call_count == 2
