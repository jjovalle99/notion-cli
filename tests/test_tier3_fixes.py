import json
import pathlib
from unittest.mock import AsyncMock

import pytest
from typer.testing import CliRunner

from notion_cli.cli import app

PAGE_ID = "aabbccdd-1122-3344-5566-778899001122"
PARENT_ID = "11223344-5566-7788-99aa-bbccddeeff00"
DB_ID = "aabbccdd-1122-3344-5566-778899001122"
BLOCK_ID = "aabbccdd-1122-3344-5566-778899001122"
DISC_ID = "11223344-5566-7788-99aa-bbccddeeff00"
MOCK_PAGE = {"id": PAGE_ID, "object": "page", "properties": {}}
MOCK_DB = {"id": DB_ID, "object": "database"}


class TestDryRunPageUpdate:
    def test_dry_run(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        result = runner.invoke(
            app,
            ["page", "update", PAGE_ID, "--title", "X", "--dry-run"],
            env={"NOTION_API_KEY": "s"},
        )
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["dry_run"] is True
        mock_client.pages.update.assert_not_called()


class TestDryRunPageMove:
    def test_dry_run(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        result = runner.invoke(
            app,
            ["page", "move", PAGE_ID, "--to", PARENT_ID, "--dry-run"],
            env={"NOTION_API_KEY": "s"},
        )
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["dry_run"] is True
        mock_client.pages.move.assert_not_called()


class TestDryRunPageDuplicate:
    def test_dry_run(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        result = runner.invoke(
            app,
            ["page", "duplicate", PAGE_ID, "--dry-run"],
            env={"NOTION_API_KEY": "s"},
        )
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["dry_run"] is True
        mock_client.pages.retrieve.assert_not_called()


class TestDryRunCommentAdd:
    def test_dry_run(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        result = runner.invoke(
            app,
            ["comment", "add", PAGE_ID, "--body", "hi", "--dry-run"],
            env={"NOTION_API_KEY": "s"},
        )
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["dry_run"] is True
        mock_client.comments.create.assert_not_called()


class TestDryRunCommentReply:
    def test_dry_run(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        result = runner.invoke(
            app,
            ["comment", "reply", DISC_ID, "--body", "hi", "--dry-run"],
            env={"NOTION_API_KEY": "s"},
        )
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["dry_run"] is True
        mock_client.comments.create.assert_not_called()


class TestDryRunDbCreate:
    def test_dry_run(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        result = runner.invoke(
            app,
            ["db", "create", "--parent", PARENT_ID, "--title", "X", "--dry-run"],
            env={"NOTION_API_KEY": "s"},
        )
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["dry_run"] is True
        mock_client.data_sources.create.assert_not_called()


class TestDryRunDbUpdate:
    def test_dry_run(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        result = runner.invoke(
            app,
            ["db", "update", DB_ID, "--title", "X", "--dry-run"],
            env={"NOTION_API_KEY": "s"},
        )
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["dry_run"] is True
        mock_client.data_sources.update.assert_not_called()


class TestDryRunBlockAppend:
    def test_dry_run(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        children = '[{"type":"paragraph","paragraph":{"rich_text":[]}}]'
        result = runner.invoke(
            app,
            ["block", "append", BLOCK_ID, "--children", children, "--dry-run"],
            env={"NOTION_API_KEY": "s"},
        )
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["dry_run"] is True
        mock_client.blocks.children.append.assert_not_called()


class TestBug18AtomicCredentials:
    def test_save_is_atomic(
        self, tmp_path: pathlib.Path, monkeypatch: "pytest.MonkeyPatch"
    ) -> None:
        fake_path = tmp_path / "credentials.json"
        monkeypatch.setattr("notion_cli.credentials._credentials_path", lambda: fake_path)

        from notion_cli.credentials import load_credentials, save_credentials

        save_credentials({"access_token": "test123", "workspace_id": "w"})
        loaded = load_credentials()
        assert loaded is not None
        assert loaded["access_token"] == "test123"

        assert fake_path.exists()
        assert oct(fake_path.stat().st_mode & 0o777) == "0o600"


class TestEmptyFindRejected:
    def test_empty_find_exits_2(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        result = runner.invoke(
            app,
            ["page", "edit", PAGE_ID, "--find", "", "--replace", "x"],
            env={"NOTION_API_KEY": "s"},
        )
        assert result.exit_code == 2
        error = json.loads(result.stderr)
        assert error["error_type"] == "invalid_args"
        mock_client.blocks.children.list.assert_not_called()


class TestBug20PageEditRegex:
    def test_regex_find_replace(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.blocks.children.list.return_value = {
            "results": [
                {
                    "id": "b1",
                    "type": "paragraph",
                    "has_children": False,
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {"content": "date: 2024-01-15"},
                                "annotations": {},
                            }
                        ]
                    },
                }
            ],
            "has_more": False,
        }
        mock_client.blocks.update.return_value = {"id": "b1"}

        result = runner.invoke(
            app,
            [
                "page",
                "edit",
                PAGE_ID,
                "--find",
                r"\d{4}-\d{2}-\d{2}",
                "--replace",
                "REDACTED",
                "--regex",
            ],
            env={"NOTION_API_KEY": "s"},
        )

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["blocks_modified"] == 1
        mock_client.blocks.update.assert_called_once()


class TestBug21WhereUnknownProperty:
    def test_unknown_property_warns(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.databases.retrieve.return_value = {
            "properties": {"Status": {"type": "select"}}
        }
        mock_client.data_sources.query.return_value = {"results": [], "has_more": False}

        result = runner.invoke(
            app,
            ["db", "query", DB_ID, "--where", "NonExistent = Done"],
            env={"NOTION_API_KEY": "s"},
        )

        assert result.exit_code == 0
        assert "unresolved_property" in result.stderr


class TestBug22VersionPinWithoutContent:
    def test_create_without_content_uses_pages_create(
        self, runner: CliRunner, mock_client: AsyncMock
    ) -> None:
        mock_client.pages.create.return_value = MOCK_PAGE

        result = runner.invoke(
            app,
            ["page", "create", "--parent", PARENT_ID, "--title", "No content"],
            env={"NOTION_API_KEY": "s"},
        )

        assert result.exit_code == 0
        mock_client.pages.create.assert_called_once()
        mock_client.request.assert_not_called()
