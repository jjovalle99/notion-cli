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
            return path.read_text()
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

    return value
