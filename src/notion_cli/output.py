import enum
import json
import sys


class ExitCode(enum.IntEnum):
    OK = 0
    ERROR = 1
    BAD_ARGS = 2
    NOT_FOUND = 3
    PERMISSION = 4
    RATE_LIMITED = 5


_COMPACT = (",", ":")
_STDOUT_IS_TTY = sys.stdout.isatty()


def format_json(data: object) -> str:
    if _STDOUT_IS_TTY:
        return json.dumps(data, default=str, indent=2)
    return json.dumps(data, default=str, separators=_COMPACT)


def project_fields(data: object, fields: set[str] | None) -> object:
    """Filter top-level keys from a dict or each dict in a list."""
    if fields is None:
        return data
    if isinstance(data, dict):
        return {k: v for k, v in data.items() if k in fields}
    if isinstance(data, list):
        return [
            {k: v for k, v in item.items() if k in fields} if isinstance(item, dict) else item
            for item in data
        ]
    return data


def stream_ndjson_page(items: list[object], fields: set[str] | None) -> None:
    """Write a page of items to stdout as NDJSON, flushing immediately."""
    for item in items:
        sys.stdout.write(format_json(project_fields(item, fields)) + "\n")
    sys.stdout.flush()


def echo_dry_run(command: str, payload: dict[str, object]) -> None:
    """Print the dry-run payload and exit."""
    import typer

    typer.echo(format_json({"dry_run": True, "command": command, "payload": payload}))
    raise SystemExit(ExitCode.OK)


def format_ndjson(items: list[object]) -> str:
    """Format a list of items as newline-delimited JSON (one compact JSON object per line)."""
    if not items:
        return ""
    return "\n".join(format_json(item) for item in items) + "\n"


def echo_list(
    results: object,
    envelope: dict[str, object],
    output_format: str,
) -> None:
    """Write list results to stdout in the requested format."""
    import typer

    if output_format == "ndjson":
        typer.echo(format_ndjson(results), nl=False)
    else:
        typer.echo(format_json({**envelope, "results": results, "has_more": False}))


def format_error(error_type: str, message: str, *, suggestion: str | None = None) -> str:
    payload: dict[str, str] = {"error_type": error_type, "message": message}
    if suggestion is not None:
        payload["suggestion"] = suggestion
    return json.dumps(payload, separators=_COMPACT)
