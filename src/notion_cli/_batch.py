import json
import sys
from collections.abc import Callable, Coroutine, Iterable

from notion_cli.output import ExitCode, format_error, format_json, project_fields


async def process_batch(
    lines: Iterable[str],
    handler: Callable[[dict[str, object]], Coroutine[object, object, dict[str, object]]],
    fields: set[str] | None,
    on_result: Callable[[str], object] | None = None,
    on_error: Callable[[str], object] | None = None,
) -> ExitCode:
    """Process NDJSON lines through an async handler.

    Args:
        lines: Iterable of NDJSON strings (one JSON object per line).
        handler: Async function that processes a single item dict and returns a result dict.
        fields: Optional field projection set.
        on_result: Callback for each success result JSON string. Defaults to stdout.
        on_error: Callback for each error JSON string. Defaults to stderr.
    """

    def _default_result(s: str) -> None:
        sys.stdout.write(s + "\n")
        sys.stdout.flush()

    def _default_error(s: str) -> None:
        sys.stderr.write(s + "\n")
        sys.stderr.flush()

    write_result = on_result or _default_result
    write_error = on_error or _default_error

    failures = 0
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        try:
            item = json.loads(stripped)
        except json.JSONDecodeError as exc:
            failures += 1
            write_error(format_error("invalid_json", f"Bad JSON on input line: {exc.args[0]}"))
            continue
        try:
            result = await handler(item)
            write_result(format_json(project_fields(result, fields)))
        except Exception as exc:
            failures += 1
            write_error(format_error("batch_item_failed", str(exc)))
    return ExitCode.ERROR if failures else ExitCode.OK
