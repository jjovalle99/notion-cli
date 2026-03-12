import json
import re
import sys
from pathlib import Path

from notion_cli.output import ExitCode, format_error

_UUID_PATTERN = re.compile(
    r"[0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12}", re.I
)


def _format_uuid(hex32: str) -> str:
    h = hex32.replace("-", "")
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"


def extract_id(value: str) -> str:
    """Extract a Notion UUID from a raw ID or URL.

    Accepts:
        - Raw UUID with or without dashes
        - Notion page/database/block URLs
    """
    clean = value.split("?")[0]

    match = _UUID_PATTERN.search(clean)
    if match:
        return _format_uuid(match.group())

    sys.stderr.write(
        format_error(
            "invalid_id",
            f"Cannot extract Notion ID from: {value}",
            suggestion="Provide a valid Notion URL or 32-character hex ID.",
        )
        + "\n"
    )
    raise SystemExit(ExitCode.BAD_ARGS)


def read_content(value: str) -> str:
    """Read content from a string, file path (@path), or stdin (-).

    Args:
        value: Plain string, '@/path/to/file.md', or '-' for stdin.
    """
    if value == "-":
        return sys.stdin.read()

    if value.startswith("@"):
        path = Path(value[1:])
        try:
            return path.read_text(encoding="utf-8")
        except FileNotFoundError:
            sys.stderr.write(
                format_error(
                    "file_not_found",
                    f"File not found: {path}",
                    suggestion="Check the file path and try again.",
                )
                + "\n"
            )
            raise SystemExit(ExitCode.BAD_ARGS)
        except (UnicodeDecodeError, IsADirectoryError, PermissionError):
            sys.stderr.write(
                format_error(
                    "file_read_error",
                    f"Cannot read file: {path}",
                    suggestion="File must be UTF-8 encoded text.",
                )
                + "\n"
            )
            raise SystemExit(ExitCode.BAD_ARGS)

    return value


def parse_json(value: str, *, expected_type: type, label: str) -> dict | list:
    """Parse a JSON string and validate its type.

    Args:
        value: Raw JSON string.
        expected_type: Expected Python type (dict or list).
        label: Option name for error messages (e.g. "--filter").
    """

    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        sys.stderr.write(
            format_error(
                "invalid_json",
                f"Invalid JSON for {label}: {exc.args[0]}",
                suggestion="Check your JSON syntax.",
            )
            + "\n"
        )
        raise SystemExit(ExitCode.BAD_ARGS)
    expected_name = "object" if expected_type is dict else "array"
    if not isinstance(parsed, expected_type):
        sys.stderr.write(
            format_error(
                "invalid_json",
                f"{label} must be a JSON {expected_name}, got {type(parsed).__name__}.",
            )
            + "\n"
        )
        raise SystemExit(ExitCode.BAD_ARGS)
    return parsed


def resolve_rich_text(body: str | None, rich_text_json: str | None) -> list[object]:
    """Resolve --body / --rich-text into a Notion rich_text array."""
    if body is not None and rich_text_json is not None:
        sys.stderr.write(
            format_error("conflicting_args", "--body and --rich-text are mutually exclusive.")
            + "\n"
        )
        raise SystemExit(ExitCode.BAD_ARGS)
    if rich_text_json is not None:
        return parse_json(rich_text_json, expected_type=list, label="--rich-text")  # ty: ignore[invalid-return-type]
    if body is not None:
        return [{"text": {"content": body}}]
    sys.stderr.write(format_error("missing_args", "Provide --body or --rich-text.") + "\n")
    raise SystemExit(ExitCode.BAD_ARGS)


def parse_fields(fields: str | None) -> set[str] | None:
    """Parse a comma-separated fields string into a set, or None if empty."""
    return set(fields.split(",")) if fields else None


def validate_limit(limit: int | None) -> None:
    """Validate that --limit is >= 1 if provided."""
    if limit is not None and limit < 1:
        sys.stderr.write(
            format_error(
                "invalid_args",
                f"--limit must be >= 1, got {limit}.",
            )
            + "\n"
        )
        raise SystemExit(ExitCode.BAD_ARGS)


_WHERE_OPS: list[tuple[str, str]] = [
    (">=", "greater_than_or_equal_to"),
    ("<=", "less_than_or_equal_to"),
    ("!=", "does_not_equal"),
    (">", "greater_than"),
    ("<", "less_than"),
    ("=", "equals"),
    (" contains ", "contains"),
    (" before ", "before"),
    (" after ", "after"),
]

_NUMBER_FILTER_TYPES = frozenset({"number"})
_BOOL_FILTER_TYPES = frozenset({"checkbox"})


def _coerce_value(value: str, prop_type: str) -> object:
    if prop_type in _BOOL_FILTER_TYPES:
        return value.lower() == "true"
    if prop_type in _NUMBER_FILTER_TYPES:
        try:
            return int(value)
        except ValueError:
            return float(value)
    return value


def parse_where(expr: str, prop_type: str) -> dict[str, object]:
    """Parse a human-friendly where expression into a Notion filter object.

    Args:
        expr: Expression like "Status = Done" or "Priority > 3".
        prop_type: Notion property type (select, number, checkbox, etc.).
    """
    for op_token, notion_op in _WHERE_OPS:
        if op_token.startswith(" "):
            idx = expr.find(op_token)
            if idx == -1:
                continue
            prop = expr[:idx].strip()
            value = expr[idx + len(op_token) :].strip()
            if not prop or not value:
                continue
        else:
            parts = expr.split(op_token, 1)
            if len(parts) != 2:
                continue
            prop = parts[0].strip()
            value = parts[1].strip()
            if not prop or not value:
                continue
        coerced = _coerce_value(value, prop_type)
        return {"property": prop, prop_type: {notion_op: coerced}}
    msg = f"Cannot parse --where expression: {expr!r}"
    raise ValueError(msg)
