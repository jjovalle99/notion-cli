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


def stream_ndjson_page(items: list[object], fields: set[str] | None) -> None:
    """Write a page of items to stdout as NDJSON, flushing immediately."""
    for item in items:
        sys.stdout.write(format_json(project_fields(item, fields)) + "\n")
    sys.stdout.flush()


def format_error(error_type: str, message: str, *, suggestion: str | None = None) -> str:
    payload: dict[str, str] = {"error_type": error_type, "message": message}
    if suggestion is not None:
        payload["suggestion"] = suggestion
    return json.dumps(payload, separators=_COMPACT)
