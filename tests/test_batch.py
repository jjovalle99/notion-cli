import asyncio
import json

from notion_cli._batch import process_batch
from notion_cli.output import ExitCode


class TestProcessBatch:
    def test_processes_all_lines(self) -> None:
        results: list[dict[str, object]] = []

        async def handler(item: dict[str, object]) -> dict[str, object]:
            results.append(item)
            return {"id": item["name"], "status": "ok"}

        lines = ['{"name": "a"}\n', '{"name": "b"}\n']
        output_lines: list[str] = []
        error_lines: list[str] = []

        exit_code = asyncio.run(
            process_batch(
                lines=lines,
                handler=handler,
                fields=None,
                on_result=output_lines.append,
                on_error=error_lines.append,
            )
        )

        assert exit_code == ExitCode.OK
        assert len(results) == 2
        assert len(output_lines) == 2
        assert json.loads(output_lines[0])["id"] == "a"
        assert json.loads(output_lines[1])["id"] == "b"
        assert len(error_lines) == 0

    def test_continues_on_failure(self) -> None:
        call_count = 0

        async def handler(item: dict[str, object]) -> dict[str, object]:
            nonlocal call_count
            call_count += 1
            if item.get("fail"):
                msg = "boom"
                raise ValueError(msg)
            return {"id": "ok"}

        lines = ['{"fail": true}\n', '{"fail": false}\n']
        output_lines: list[str] = []
        error_lines: list[str] = []

        exit_code = asyncio.run(
            process_batch(
                lines=lines,
                handler=handler,
                fields=None,
                on_result=output_lines.append,
                on_error=error_lines.append,
            )
        )

        assert exit_code == ExitCode.ERROR
        assert call_count == 2
        assert len(output_lines) == 1
        assert len(error_lines) == 1
        assert "boom" in error_lines[0]

    def test_skips_blank_lines(self) -> None:
        call_count = 0

        async def handler(item: dict[str, object]) -> dict[str, object]:
            nonlocal call_count
            call_count += 1
            return {"id": "ok"}

        lines = ['{"a": 1}\n', "\n", "  \n", '{"b": 2}\n']
        output_lines: list[str] = []

        asyncio.run(
            process_batch(
                lines=lines,
                handler=handler,
                fields=None,
                on_result=output_lines.append,
                on_error=lambda _: None,
            )
        )

        assert call_count == 2

    def test_reports_invalid_json(self) -> None:
        async def handler(item: dict[str, object]) -> dict[str, object]:
            return item

        lines = ["not json\n"]
        error_lines: list[str] = []

        exit_code = asyncio.run(
            process_batch(
                lines=lines,
                handler=handler,
                fields=None,
                on_result=lambda _: None,
                on_error=error_lines.append,
            )
        )

        assert exit_code == ExitCode.ERROR
        assert len(error_lines) == 1
        error = json.loads(error_lines[0])
        assert error["error_type"] == "invalid_json"

    def test_applies_field_projection(self) -> None:
        async def handler(item: dict[str, object]) -> dict[str, object]:
            return {"id": "x", "name": "y", "extra": "z"}

        lines = ['{"a": 1}\n']
        output_lines: list[str] = []

        asyncio.run(
            process_batch(
                lines=lines,
                handler=handler,
                fields={"id", "name"},
                on_result=output_lines.append,
                on_error=lambda _: None,
            )
        )

        data = json.loads(output_lines[0])
        assert data == {"id": "x", "name": "y"}
