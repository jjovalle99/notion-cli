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
        help="Timeout per API request in seconds (each paginated fetch gets its own timeout). Omit for no timeout.",
    )
