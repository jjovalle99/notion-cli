import json
import pathlib
from unittest.mock import AsyncMock

from typer.testing import CliRunner

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
