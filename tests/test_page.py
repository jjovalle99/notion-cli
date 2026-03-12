import json
import pathlib
from unittest.mock import AsyncMock

from typer.testing import CliRunner

from notion_client.errors import APIResponseError
from notion_cli.cli import app

PAGE_ID = "aabbccdd-1122-3344-5566-778899001122"
PARENT_ID = "11223344-5566-7788-99aa-bbccddeeff00"
NEW_PARENT_ID = "ffeeddcc-bbaa-9988-7766-554433221100"

MOCK_PAGE = {
    "id": PAGE_ID,
    "object": "page",
    "properties": {"title": {"title": [{"plain_text": "Test Page"}]}},
    "url": "https://www.notion.so/Test-Page-aabbccdd112233445566778899001122",
}


class TestPageGet:
    def test_get_by_id(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.pages.retrieve.return_value = MOCK_PAGE

        result = runner.invoke(app, ["page", "get", PAGE_ID], env={"NOTION_API_KEY": "secret"})

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["id"] == PAGE_ID

    def test_get_by_url(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.pages.retrieve.return_value = MOCK_PAGE

        result = runner.invoke(
            app,
            ["page", "get", "https://www.notion.so/My-Page-abc123def456abc123def456abc123de"],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        mock_client.pages.retrieve.assert_called_once_with("abc123de-f456-abc1-23de-f456abc123de")

    def test_get_with_fields(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.pages.retrieve.return_value = {
            "id": PAGE_ID,
            "object": "page",
            "url": "https://notion.so/page",
            "properties": {},
        }

        result = runner.invoke(
            app,
            ["page", "get", PAGE_ID, "--fields", "id,url"],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data == {"id": PAGE_ID, "url": "https://notion.so/page"}


class TestPageGetFull:
    def test_full_returns_page_blocks_comments(
        self, runner: CliRunner, mock_client: AsyncMock
    ) -> None:
        mock_client.pages.retrieve.return_value = MOCK_PAGE
        mock_client.blocks.children.list.return_value = {
            "results": [{"id": "b1", "type": "paragraph", "has_children": False}],
            "has_more": False,
        }
        mock_client.comments.list.return_value = {
            "results": [{"id": "c1", "rich_text": []}],
            "has_more": False,
        }

        result = runner.invoke(
            app,
            ["page", "get", PAGE_ID, "--full"],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["page"]["id"] == PAGE_ID
        assert len(data["blocks"]) == 1
        assert data["blocks"][0]["id"] == "b1"
        assert len(data["comments"]) == 1
        assert data["comments"][0]["id"] == "c1"

    def test_full_with_fields(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.pages.retrieve.return_value = MOCK_PAGE
        mock_client.blocks.children.list.return_value = {
            "results": [],
            "has_more": False,
        }
        mock_client.comments.list.return_value = {
            "results": [],
            "has_more": False,
        }

        result = runner.invoke(
            app,
            ["page", "get", PAGE_ID, "--full", "--fields", "page"],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert "page" in data
        assert "blocks" not in data

    def test_full_handles_comments_403_gracefully(
        self, runner: CliRunner, mock_client: AsyncMock
    ) -> None:

        mock_client.pages.retrieve.return_value = MOCK_PAGE
        mock_client.blocks.children.list.return_value = {
            "results": [{"id": "b1", "type": "paragraph", "has_children": False}],
            "has_more": False,
        }
        mock_client.comments.list.side_effect = APIResponseError(
            code="restricted_resource",
            status=403,
            message="forbidden",
            headers={},
            raw_body_text="",
        )

        result = runner.invoke(
            app,
            ["page", "get", PAGE_ID, "--full"],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["page"]["id"] == PAGE_ID
        assert len(data["blocks"]) == 1
        assert data["comments"] == []

    def test_full_blocks_api_error_propagates(
        self, runner: CliRunner, mock_client: AsyncMock
    ) -> None:

        mock_client.pages.retrieve.return_value = {"id": PAGE_ID, "object": "page"}
        mock_client.blocks.children.list.side_effect = APIResponseError(
            code="object_not_found",
            status=404,
            message="not found",
            headers={},
            raw_body_text="",
        )
        mock_client.comments.list.return_value = {"results": [], "has_more": False}

        result = runner.invoke(
            app,
            ["page", "get", PAGE_ID, "--full"],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 3
        error = json.loads(result.stderr)
        assert error["error_type"] == "object_not_found"


class TestPageCreate:
    def test_create_with_title(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.pages.create.return_value = MOCK_PAGE

        result = runner.invoke(
            app,
            ["page", "create", "--parent", PARENT_ID, "--title", "New Page"],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        call_kwargs = mock_client.pages.create.call_args.kwargs
        assert "parent" in call_kwargs

    def test_create_with_markdown_content(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.request.return_value = MOCK_PAGE

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
        mock_client.request.assert_called_once()
        call_kwargs = mock_client.request.call_args.kwargs
        assert call_kwargs["path"] == "pages"
        assert call_kwargs["method"] == "POST"
        body = call_kwargs["body"]
        assert body["markdown"] == "# Heading\nSome text"
        assert "content" not in body
        assert "parent" in body
        assert "properties" in body

    def test_create_with_icon(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.pages.create.return_value = MOCK_PAGE

        result = runner.invoke(
            app,
            ["page", "create", "--parent", PARENT_ID, "--title", "New Page", "--icon", "📝"],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        call_kwargs = mock_client.pages.create.call_args.kwargs
        assert call_kwargs["icon"] == {"type": "emoji", "emoji": "📝"}

    def test_create_without_content_uses_pages_create(
        self, runner: CliRunner, mock_client: AsyncMock
    ) -> None:
        mock_client.pages.create.return_value = MOCK_PAGE

        result = runner.invoke(
            app,
            ["page", "create", "--parent", PARENT_ID, "--title", "No content"],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        mock_client.pages.create.assert_called_once()
        mock_client.request.assert_not_called()


class TestPageCreateDryRun:
    def test_dry_run_outputs_payload_and_skips_api(
        self, runner: CliRunner, mock_client: AsyncMock
    ) -> None:
        result = runner.invoke(
            app,
            ["page", "create", "--parent", PARENT_ID, "--title", "New Page", "--dry-run"],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["dry_run"] is True
        assert data["command"] == "page create"
        assert "parent" in data["payload"]
        mock_client.pages.create.assert_not_called()

    def test_stdin_dry_run_skips_api(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        ndjson = f'{{"parent": "{PARENT_ID}", "title": "A"}}\n'
        result = runner.invoke(
            app,
            ["page", "create", "--stdin", "--dry-run"],
            input=ndjson,
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["dry_run"] is True
        mock_client.pages.create.assert_not_called()


class TestPageCreateFileAndStdin:
    def test_create_with_at_file(
        self, runner: CliRunner, mock_client: AsyncMock, tmp_path: pathlib.Path
    ) -> None:
        md_file = tmp_path / "notes.md"
        md_file.write_text("# Title\nBody text")
        mock_client.request.return_value = MOCK_PAGE

        result = runner.invoke(
            app,
            [
                "page",
                "create",
                "--parent",
                PARENT_ID,
                "--title",
                "Notes",
                "--content",
                f"@{md_file}",
            ],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        body = mock_client.request.call_args.kwargs["body"]
        assert body["markdown"] == "# Title\nBody text"

    def test_create_with_stdin(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.request.return_value = MOCK_PAGE

        result = runner.invoke(
            app,
            ["page", "create", "--parent", PARENT_ID, "--title", "Notes", "--content", "-"],
            input="stdin content",
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        body = mock_client.request.call_args.kwargs["body"]
        assert body["markdown"] == "stdin content"


class TestPageCreateParentType:
    def test_create_with_database_parent(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.pages.create.return_value = MOCK_PAGE

        result = runner.invoke(
            app,
            [
                "page",
                "create",
                "--parent",
                PARENT_ID,
                "--title",
                "Row",
                "--parent-type",
                "database",
            ],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        call_kwargs = mock_client.pages.create.call_args.kwargs
        assert "database_id" in call_kwargs["parent"]
        assert "page_id" not in call_kwargs["parent"]

    def test_create_defaults_to_page_parent(
        self, runner: CliRunner, mock_client: AsyncMock
    ) -> None:
        mock_client.pages.create.return_value = MOCK_PAGE

        result = runner.invoke(
            app,
            ["page", "create", "--parent", PARENT_ID, "--title", "Page"],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        call_kwargs = mock_client.pages.create.call_args.kwargs
        assert "page_id" in call_kwargs["parent"]


class TestPageUpdate:
    def test_update_title(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.pages.update.return_value = MOCK_PAGE

        result = runner.invoke(
            app,
            ["page", "update", PAGE_ID, "--title", "Updated Title"],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0

    def test_update_archive(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.pages.update.return_value = {**MOCK_PAGE, "archived": True}

        result = runner.invoke(
            app,
            ["page", "update", PAGE_ID, "--archive"],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0

    def test_unarchive(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.pages.update.return_value = {**MOCK_PAGE, "archived": False}

        result = runner.invoke(
            app,
            ["page", "update", PAGE_ID, "--no-archive"],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        call_kwargs = mock_client.pages.update.call_args.kwargs
        assert call_kwargs["archived"] is False

    def test_update_properties_json(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.pages.update.return_value = MOCK_PAGE
        props_json = '{"Status": {"select": {"name": "Done"}}}'

        result = runner.invoke(
            app,
            ["page", "update", PAGE_ID, "--properties", props_json],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        call_kwargs = mock_client.pages.update.call_args.kwargs
        assert call_kwargs["properties"]["Status"] == {"select": {"name": "Done"}}

    def test_update_title_and_properties_title_conflict(
        self, runner: CliRunner, mock_client: AsyncMock
    ) -> None:
        props_json = '{"title": {"title": [{"text": {"content": "from props"}}]}}'

        result = runner.invoke(
            app,
            ["page", "update", PAGE_ID, "--title", "from flag", "--properties", props_json],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 2
        error = json.loads(result.stderr)
        assert error["error_type"] == "conflicting_args"

    def test_update_icon(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.pages.update.return_value = MOCK_PAGE

        result = runner.invoke(
            app,
            ["page", "update", PAGE_ID, "--icon", "🔥"],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        call_kwargs = mock_client.pages.update.call_args.kwargs
        assert call_kwargs["icon"] == {"type": "emoji", "emoji": "🔥"}

    def test_no_flags_rejected(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        result = runner.invoke(
            app,
            ["page", "update", PAGE_ID],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 2
        error = json.loads(result.stderr)
        assert error["error_type"] == "missing_args"
        mock_client.pages.update.assert_not_called()

    def test_dry_run_skips_api(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        result = runner.invoke(
            app,
            ["page", "update", PAGE_ID, "--title", "X", "--dry-run"],
            env={"NOTION_API_KEY": "secret"},
        )
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["dry_run"] is True
        mock_client.pages.update.assert_not_called()


class TestPageMove:
    def test_move_page(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.pages.move.return_value = MOCK_PAGE

        result = runner.invoke(
            app,
            ["page", "move", PAGE_ID, "--to", NEW_PARENT_ID],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        call_kwargs = mock_client.pages.move.call_args.kwargs
        assert call_kwargs["parent"] == {"page_id": NEW_PARENT_ID}

    def test_move_extracts_ids_from_urls(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.pages.move.return_value = MOCK_PAGE

        result = runner.invoke(
            app,
            [
                "page",
                "move",
                f"https://notion.so/{PAGE_ID.replace('-', '')}",
                "--to",
                f"https://notion.so/{NEW_PARENT_ID.replace('-', '')}",
            ],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        call_kwargs = mock_client.pages.move.call_args.kwargs
        assert call_kwargs["page_id"] == PAGE_ID
        assert call_kwargs["parent"] == {"page_id": NEW_PARENT_ID}

    def test_dry_run_skips_api(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        result = runner.invoke(
            app,
            ["page", "move", PAGE_ID, "--to", PARENT_ID, "--dry-run"],
            env={"NOTION_API_KEY": "secret"},
        )
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["dry_run"] is True
        mock_client.pages.move.assert_not_called()


class TestPageMoveStdin:
    def test_moves_multiple_pages(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.pages.move.return_value = MOCK_PAGE
        ndjson = (
            f'{{"page_id": "{PAGE_ID}", "to": "{NEW_PARENT_ID}"}}\n'
            f'{{"page_id": "{PAGE_ID}", "to": "{PARENT_ID}"}}\n'
        )

        result = runner.invoke(
            app,
            ["page", "move", "--stdin"],
            input=ndjson,
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        assert mock_client.pages.move.call_count == 2

    def test_stdin_continues_on_failure(self, runner: CliRunner, mock_client: AsyncMock) -> None:

        mock_client.pages.move.side_effect = [
            APIResponseError(
                code="object_not_found",
                status=404,
                message="not found",
                headers={},
                raw_body_text="",
            ),
            MOCK_PAGE,
        ]
        ndjson = (
            f'{{"page_id": "{PAGE_ID}", "to": "{NEW_PARENT_ID}"}}\n'
            f'{{"page_id": "{PAGE_ID}", "to": "{PARENT_ID}"}}\n'
        )

        result = runner.invoke(
            app,
            ["page", "move", "--stdin"],
            input=ndjson,
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 1
        assert mock_client.pages.move.call_count == 2

    def test_stdin_dry_run_skips_api(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        ndjson = f'{{"page_id": "{PAGE_ID}", "to": "{PARENT_ID}"}}\n'
        result = runner.invoke(
            app,
            ["page", "move", "--stdin", "--dry-run"],
            input=ndjson,
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["dry_run"] is True
        mock_client.pages.move.assert_not_called()


class TestPageDuplicate:
    def test_duplicate_page(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.pages.retrieve.return_value = {
            **MOCK_PAGE,
            "parent": {"page_id": PARENT_ID},
            "icon": {"type": "emoji", "emoji": "📝"},
            "cover": None,
        }
        mock_client.pages.create.return_value = {**MOCK_PAGE, "id": "new-page-id"}

        result = runner.invoke(
            app, ["page", "duplicate", PAGE_ID], env={"NOTION_API_KEY": "secret"}
        )

        assert result.exit_code == 0
        mock_client.pages.retrieve.assert_called_once()
        mock_client.pages.create.assert_called_once()

    def test_duplicate_filters_read_only_properties(
        self, runner: CliRunner, mock_client: AsyncMock
    ) -> None:
        mock_client.pages.retrieve.return_value = {
            **MOCK_PAGE,
            "parent": {"page_id": PARENT_ID},
            "icon": None,
            "cover": None,
            "properties": {
                "title": {"type": "title", "title": [{"plain_text": "Test"}]},
                "Status": {"type": "select", "select": {"name": "Done"}},
                "Created": {"type": "created_time", "created_time": "2026-01-01"},
                "Edited": {"type": "last_edited_time", "last_edited_time": "2026-01-02"},
                "Author": {"type": "created_by", "created_by": {}},
                "Editor": {"type": "last_edited_by", "last_edited_by": {}},
                "Calc": {"type": "formula", "formula": {"number": 42}},
                "Roll": {"type": "rollup", "rollup": {"number": 10}},
            },
        }
        mock_client.pages.create.return_value = {**MOCK_PAGE, "id": "new-page-id"}

        result = runner.invoke(
            app, ["page", "duplicate", PAGE_ID], env={"NOTION_API_KEY": "secret"}
        )

        assert result.exit_code == 0
        create_kwargs = mock_client.pages.create.call_args.kwargs
        props = create_kwargs["properties"]
        assert "title" in props
        assert "Status" in props
        assert "Created" not in props
        assert "Edited" not in props
        assert "Author" not in props
        assert "Editor" not in props
        assert "Calc" not in props
        assert "Roll" not in props

    def test_duplicate_with_destination(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.pages.retrieve.return_value = {
            **MOCK_PAGE,
            "parent": {"page_id": PARENT_ID},
            "icon": None,
            "cover": None,
        }
        mock_client.pages.create.return_value = {**MOCK_PAGE, "id": "new-page-id"}

        result = runner.invoke(
            app,
            ["page", "duplicate", PAGE_ID, "--destination", NEW_PARENT_ID],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        create_kwargs = mock_client.pages.create.call_args.kwargs
        assert create_kwargs["parent"] == {"page_id": NEW_PARENT_ID}

    def test_duplicate_with_destination_database(
        self, runner: CliRunner, mock_client: AsyncMock
    ) -> None:
        mock_client.pages.retrieve.return_value = {
            **MOCK_PAGE,
            "parent": {"page_id": PARENT_ID},
            "icon": None,
            "cover": None,
        }
        mock_client.pages.create.return_value = {**MOCK_PAGE, "id": "new-page-id"}

        result = runner.invoke(
            app,
            [
                "page",
                "duplicate",
                PAGE_ID,
                "--destination",
                NEW_PARENT_ID,
                "--destination-type",
                "database",
            ],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        create_kwargs = mock_client.pages.create.call_args.kwargs
        assert create_kwargs["parent"] == {"database_id": NEW_PARENT_ID}

    def test_duplicate_with_content(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.pages.retrieve.return_value = {
            **MOCK_PAGE,
            "parent": {"page_id": PARENT_ID},
            "icon": None,
            "cover": None,
        }
        mock_client.pages.create.return_value = {**MOCK_PAGE, "id": "new-page-id"}
        mock_client.blocks.children.list.return_value = {
            "results": [
                {
                    "id": "block-1",
                    "type": "paragraph",
                    "has_children": False,
                    "paragraph": {"rich_text": [{"text": {"content": "Hello"}}]},
                    "object": "block",
                    "created_time": "2024-01-01",
                }
            ],
            "has_more": False,
        }
        mock_client.blocks.children.append.return_value = {"results": []}

        result = runner.invoke(
            app,
            ["page", "duplicate", PAGE_ID, "--with-content"],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        mock_client.blocks.children.append.assert_called_once()
        append_kwargs = mock_client.blocks.children.append.call_args.kwargs
        children = append_kwargs["children"]
        assert children[0]["type"] == "paragraph"
        assert "id" not in children[0]
        assert "created_time" not in children[0]

    def test_duplicate_with_content_errors_when_create_returns_no_id(
        self, runner: CliRunner, mock_client: AsyncMock
    ) -> None:
        mock_client.pages.retrieve.return_value = {
            **MOCK_PAGE,
            "parent": {"page_id": PARENT_ID},
            "icon": None,
            "cover": None,
        }
        mock_client.pages.create.return_value = {"object": "page"}
        mock_client.blocks.children.list.return_value = {
            "results": [
                {
                    "id": "b1",
                    "type": "paragraph",
                    "has_children": False,
                    "paragraph": {"rich_text": []},
                    "object": "block",
                }
            ],
            "has_more": False,
        }

        result = runner.invoke(
            app,
            ["page", "duplicate", PAGE_ID, "--with-content"],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 1
        error = json.loads(result.stderr)
        assert error["error_type"] == "invalid_response"
        mock_client.blocks.children.append.assert_not_called()

    def test_duplicate_with_content_archives_page_on_append_failure(
        self, runner: CliRunner, mock_client: AsyncMock
    ) -> None:
        mock_client.pages.retrieve.return_value = {
            **MOCK_PAGE,
            "parent": {"page_id": PARENT_ID},
            "icon": None,
            "cover": None,
        }
        new_id = "new-page-id"
        mock_client.pages.create.return_value = {**MOCK_PAGE, "id": new_id}
        mock_client.blocks.children.list.return_value = {
            "results": [
                {
                    "id": "b1",
                    "type": "paragraph",
                    "has_children": False,
                    "paragraph": {"rich_text": []},
                    "object": "block",
                }
            ],
            "has_more": False,
        }
        mock_client.blocks.children.append.side_effect = RuntimeError("API failure")
        mock_client.pages.update.return_value = {}

        result = runner.invoke(
            app,
            ["page", "duplicate", PAGE_ID, "--with-content"],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 1
        mock_client.pages.update.assert_called_once_with(page_id=new_id, archived=True)
        error = json.loads(result.stderr)
        assert error["error_type"] == "content_copy_failed"
        assert "archived" in error["message"].lower()

    def test_duplicate_with_content_skips_synced_block(
        self, runner: CliRunner, mock_client: AsyncMock
    ) -> None:
        mock_client.pages.retrieve.return_value = {
            **MOCK_PAGE,
            "parent": {"page_id": PARENT_ID},
            "icon": None,
            "cover": None,
        }
        mock_client.pages.create.return_value = {**MOCK_PAGE, "id": "new-page-id"}
        mock_client.blocks.children.list.return_value = {
            "results": [
                {
                    "id": "sb-1",
                    "type": "synced_block",
                    "has_children": True,
                    "synced_block": {"synced_from": {"block_id": "original-block"}},
                    "object": "block",
                },
                {
                    "id": "p-1",
                    "type": "paragraph",
                    "has_children": False,
                    "paragraph": {"rich_text": []},
                    "object": "block",
                },
            ],
            "has_more": False,
        }
        mock_client.blocks.children.append.return_value = {"results": []}

        result = runner.invoke(
            app,
            ["page", "duplicate", PAGE_ID, "--with-content"],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        children = mock_client.blocks.children.append.call_args.kwargs["children"]
        child_types = [c["type"] for c in children]
        assert "synced_block" not in child_types
        assert "paragraph" in child_types

    def test_duplicate_missing_properties(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.pages.retrieve.return_value = {
            "id": PAGE_ID,
            "object": "page",
            "parent": {"page_id": PARENT_ID},
        }
        mock_client.pages.create.return_value = {**MOCK_PAGE, "id": "new-page-id"}

        result = runner.invoke(
            app, ["page", "duplicate", PAGE_ID], env={"NOTION_API_KEY": "secret"}
        )

        assert result.exit_code == 0
        create_kwargs = mock_client.pages.create.call_args.kwargs
        assert create_kwargs["properties"] == {}

    def test_dry_run_skips_api(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        result = runner.invoke(
            app,
            ["page", "duplicate", PAGE_ID, "--dry-run"],
            env={"NOTION_API_KEY": "secret"},
        )
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["dry_run"] is True
        mock_client.pages.retrieve.assert_not_called()


class TestPageCreateStdin:
    def test_creates_multiple_pages(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.pages.create.return_value = {**MOCK_PAGE, "id": "new-id"}
        ndjson = (
            f'{{"parent": "{PARENT_ID}", "title": "Page A"}}\n'
            f'{{"parent": "{PARENT_ID}", "title": "Page B"}}\n'
        )

        result = runner.invoke(
            app,
            ["page", "create", "--stdin"],
            input=ndjson,
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        assert mock_client.pages.create.call_count == 2

    def test_stdin_outputs_ndjson(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.pages.create.side_effect = [
            {**MOCK_PAGE, "id": "id-1"},
            {**MOCK_PAGE, "id": "id-2"},
        ]
        ndjson = (
            f'{{"parent": "{PARENT_ID}", "title": "A"}}\n'
            f'{{"parent": "{PARENT_ID}", "title": "B"}}\n'
        )

        result = runner.invoke(
            app,
            ["page", "create", "--stdin"],
            input=ndjson,
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        lines = [ln for ln in result.stdout.strip().split("\n") if ln]
        assert len(lines) == 2
        assert json.loads(lines[0])["id"] == "id-1"
        assert json.loads(lines[1])["id"] == "id-2"

    def test_stdin_continues_on_failure(self, runner: CliRunner, mock_client: AsyncMock) -> None:

        mock_client.pages.create.side_effect = [
            APIResponseError(
                code="validation_error",
                status=400,
                message="bad",
                headers={},
                raw_body_text="",
            ),
            {**MOCK_PAGE, "id": "id-2"},
        ]
        ndjson = (
            f'{{"parent": "{PARENT_ID}", "title": "A"}}\n'
            f'{{"parent": "{PARENT_ID}", "title": "B"}}\n'
        )

        result = runner.invoke(
            app,
            ["page", "create", "--stdin"],
            input=ndjson,
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 1
        assert mock_client.pages.create.call_count == 2
        stdout_lines = [ln for ln in result.stdout.strip().split("\n") if ln]
        assert len(stdout_lines) == 1
