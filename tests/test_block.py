import json
import pathlib
from unittest.mock import AsyncMock

from typer.testing import CliRunner

from notion_cli.cli import app

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


class TestBlockGet:
    def test_get_children(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.blocks.children.list.return_value = MOCK_CHILDREN

        result = runner.invoke(app, ["block", "get", BLOCK_ID], env={"NOTION_API_KEY": "secret"})

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert len(data["results"]) == 2

    def test_get_paginates_automatically(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        page1 = {"results": [{"id": "child-1"}], "has_more": True, "next_cursor": "cur1"}
        page2 = {"results": [{"id": "child-2"}], "has_more": False}
        mock_client.blocks.children.list.side_effect = [page1, page2]

        result = runner.invoke(app, ["block", "get", BLOCK_ID], env={"NOTION_API_KEY": "secret"})

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert len(data["results"]) == 2
        assert mock_client.blocks.children.list.call_count == 2

    def test_get_markdown_output(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.blocks.children.list.return_value = {
            "results": [
                {
                    "type": "heading_1",
                    "heading_1": {
                        "rich_text": [
                            {"type": "text", "text": {"content": "Hello"}, "annotations": {}}
                        ]
                    },
                },
                {
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {"type": "text", "text": {"content": "World"}, "annotations": {}}
                        ]
                    },
                },
            ],
            "has_more": False,
        }

        result = runner.invoke(
            app, ["block", "get", BLOCK_ID, "--markdown"], env={"NOTION_API_KEY": "secret"}
        )

        assert result.exit_code == 0
        assert "# Hello" in result.stdout
        assert "World" in result.stdout
        # Should NOT be JSON
        assert "{" not in result.stdout

    def test_get_with_limit(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        page1 = {"results": [{"id": f"child-{i}"} for i in range(3)], "has_more": False}
        mock_client.blocks.children.list.return_value = page1

        result = runner.invoke(
            app, ["block", "get", BLOCK_ID, "--limit", "2"], env={"NOTION_API_KEY": "secret"}
        )

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert len(data["results"]) == 2

    def test_get_limit_sets_page_size(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.blocks.children.list.return_value = {
            "results": [{"id": "child-1"}],
            "has_more": False,
        }

        runner.invoke(
            app, ["block", "get", BLOCK_ID, "--limit", "5"], env={"NOTION_API_KEY": "secret"}
        )

        call_kwargs = mock_client.blocks.children.list.call_args.kwargs
        assert call_kwargs["page_size"] == 5

    def test_get_limit_stops_pagination_early(
        self, runner: CliRunner, mock_client: AsyncMock
    ) -> None:
        page1 = {"results": [{"id": "child-1"}], "has_more": True, "next_cursor": "cur1"}
        page2 = {"results": [{"id": "child-2"}], "has_more": True, "next_cursor": "cur2"}
        mock_client.blocks.children.list.side_effect = [page1, page2]

        result = runner.invoke(
            app, ["block", "get", BLOCK_ID, "--limit", "2"], env={"NOTION_API_KEY": "secret"}
        )

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert len(data["results"]) == 2
        assert mock_client.blocks.children.list.call_count == 2

    def test_get_recursive(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        top_level = {
            "results": [
                {
                    "id": "parent-1",
                    "type": "toggle",
                    "has_children": True,
                    "toggle": {
                        "rich_text": [
                            {"type": "text", "text": {"content": "T"}, "annotations": {}}
                        ]
                    },
                }
            ],
            "has_more": False,
        }
        nested = {
            "results": [
                {
                    "id": "child-1",
                    "type": "paragraph",
                    "has_children": False,
                    "paragraph": {"rich_text": []},
                }
            ],
            "has_more": False,
        }
        mock_client.blocks.children.list.side_effect = [top_level, nested]

        result = runner.invoke(
            app,
            ["block", "get", BLOCK_ID, "--recursive"],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["results"][0]["children"][0]["id"] == "child-1"

    def test_get_recursive_markdown(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        top_level = {
            "results": [
                {
                    "id": "parent-1",
                    "type": "bulleted_list_item",
                    "has_children": True,
                    "bulleted_list_item": {
                        "rich_text": [
                            {"type": "text", "text": {"content": "parent"}, "annotations": {}}
                        ]
                    },
                }
            ],
            "has_more": False,
        }
        nested = {
            "results": [
                {
                    "id": "child-1",
                    "type": "bulleted_list_item",
                    "has_children": False,
                    "bulleted_list_item": {
                        "rich_text": [
                            {"type": "text", "text": {"content": "child"}, "annotations": {}}
                        ]
                    },
                }
            ],
            "has_more": False,
        }
        mock_client.blocks.children.list.side_effect = [top_level, nested]

        result = runner.invoke(
            app,
            ["block", "get", BLOCK_ID, "--recursive", "--markdown"],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        assert "- parent" in result.stdout
        assert "    - child" in result.stdout

    def test_get_recursive_with_limit_rejected(
        self, runner: CliRunner, mock_client: AsyncMock
    ) -> None:
        result = runner.invoke(
            app,
            ["block", "get", BLOCK_ID, "--recursive", "--limit", "10"],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 2
        error = json.loads(result.stderr)
        assert error["error_type"] == "conflicting_args"
        mock_client.blocks.children.list.assert_not_called()

    def test_get_limit_zero_rejected(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        result = runner.invoke(
            app, ["block", "get", BLOCK_ID, "--limit", "0"], env={"NOTION_API_KEY": "secret"}
        )

        assert result.exit_code == 2
        error = json.loads(result.stderr)
        assert error["error_type"] == "invalid_args"


class TestBlockAppend:
    def test_append_children(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        mock_client.blocks.children.append.return_value = MOCK_APPEND
        children_json = (
            '[{"type": "paragraph", "paragraph": {"rich_text": [{"text": {"content": "Hello"}}]}}]'
        )

        result = runner.invoke(
            app,
            ["block", "append", PARENT_ID, "--children", children_json],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        call_kwargs = mock_client.blocks.children.append.call_args.kwargs
        assert "children" in call_kwargs
        assert len(call_kwargs["children"]) == 1

    def test_append_empty_list_rejected(self, runner: CliRunner, mock_client: AsyncMock) -> None:
        result = runner.invoke(
            app,
            ["block", "append", PARENT_ID, "--children", "[]"],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 2
        error = json.loads(result.stderr)
        assert error["error_type"] == "empty_input"
        mock_client.blocks.children.append.assert_not_called()

    def test_append_partial_failure_reports_progress(
        self, runner: CliRunner, mock_client: AsyncMock
    ) -> None:
        from notion_client.errors import APIResponseError

        blocks = [{"type": "paragraph", "paragraph": {"rich_text": []}} for _ in range(150)]
        mock_client.blocks.children.append.side_effect = [
            {"results": []},
            APIResponseError(
                code="internal_server_error",
                status=500,
                message="fail",
                headers={},
                raw_body_text="",
            ),
        ]

        result = runner.invoke(
            app,
            ["block", "append", PARENT_ID, "--children", json.dumps(blocks)],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 1
        error = json.loads(result.stderr)
        assert error["error_type"] == "partial_append"
        assert "100" in error["message"]

    def test_append_from_file(
        self,
        runner: CliRunner,
        mock_client: AsyncMock,
        tmp_path: pathlib.Path,
    ) -> None:
        json_file = tmp_path / "blocks.json"
        json_file.write_text(
            '[{"type": "paragraph", "paragraph": {"rich_text": [{"text": {"content": "File"}}]}}]'
        )
        mock_client.blocks.children.append.return_value = MOCK_APPEND

        result = runner.invoke(
            app,
            ["block", "append", PARENT_ID, "--children", f"@{json_file}"],
            env={"NOTION_API_KEY": "secret"},
        )

        assert result.exit_code == 0
        call_kwargs = mock_client.blocks.children.append.call_args.kwargs
        assert call_kwargs["children"][0]["type"] == "paragraph"
