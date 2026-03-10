import os
import sys

from notion_cli.output import format_error, ExitCode


def resolve_token(*, token: str | None) -> str:
    """Return the Notion API token from explicit flag or NOTION_API_KEY env var."""
    if token is not None and token != "":
        return token
    env_token = os.environ.get("NOTION_API_KEY")
    if env_token is not None and env_token != "":
        return env_token
    sys.stderr.write(
        format_error(
            "auth_missing",
            "No Notion API token found.",
            suggestion="Set NOTION_API_KEY env var or pass --token.",
        )
        + "\n"
    )
    raise SystemExit(ExitCode.BAD_ARGS)
