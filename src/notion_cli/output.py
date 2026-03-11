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


def format_error(error_type: str, message: str, *, suggestion: str | None = None) -> str:
    payload: dict[str, str] = {"error_type": error_type, "message": message}
    if suggestion is not None:
        payload["suggestion"] = suggestion
    return json.dumps(payload, separators=_COMPACT)
