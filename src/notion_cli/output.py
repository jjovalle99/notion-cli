import enum
import json


class ExitCode(enum.IntEnum):
    OK = 0
    ERROR = 1
    BAD_ARGS = 2
    NOT_FOUND = 3
    PERMISSION = 4
    RATE_LIMITED = 5


_COMPACT = (",", ":")


def format_json(data: object) -> str:
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


def echo_dry_run(command: str, payload: dict[str, object]) -> None:
    """Print the dry-run payload and exit."""
    import typer

    typer.echo(format_json({"dry_run": True, "command": command, "payload": payload}))
    raise SystemExit(ExitCode.OK)


def format_error(error_type: str, message: str, *, suggestion: str | None = None) -> str:
    payload: dict[str, str] = {"error_type": error_type, "message": message}
    if suggestion is not None:
        payload["suggestion"] = suggestion
    return json.dumps(payload, separators=_COMPACT)
