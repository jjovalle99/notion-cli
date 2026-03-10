import enum
import json


class ExitCode(enum.IntEnum):
    OK = 0
    ERROR = 1
    BAD_ARGS = 2
    NOT_FOUND = 3
    PERMISSION = 4
    RATE_LIMITED = 5


def format_json(data: object, *, pretty: bool = False) -> str:
    indent = 2 if pretty else None
    return json.dumps(data, indent=indent, default=str)


def format_error(error_type: str, message: str, *, suggestion: str | None = None) -> str:
    payload: dict[str, str] = {"error_type": error_type, "message": message}
    if suggestion is not None:
        payload["suggestion"] = suggestion
    return json.dumps(payload)
