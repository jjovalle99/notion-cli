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
