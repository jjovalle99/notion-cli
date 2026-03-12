import typer
from typer.models import OptionInfo


def token_option() -> OptionInfo:
    """Shared --token option for all commands."""
    return typer.Option(
        "--token",
        help="Notion API token. Defaults to NOTION_API_KEY env var.",
    )


def timeout_option() -> OptionInfo:
    """Shared --timeout option for all commands."""
    return typer.Option(
        "--timeout",
        help="Timeout per API request in seconds. Each paginated fetch gets its own timeout; total wall-clock time for multi-page results is not bounded. Omit for no timeout.",
    )


def fields_option() -> OptionInfo:
    """Shared --fields option for output projection."""
    return typer.Option(
        "--fields",
        "-f",
        help="Comma-separated list of fields to include in output.",
    )


def dry_run_option() -> OptionInfo:
    """Shared --dry-run option for mutating commands."""
    return typer.Option(
        "--dry-run",
        help="Show what would be sent to the API without making changes.",
    )
