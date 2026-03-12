import click
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


def output_format_option() -> OptionInfo:
    """Shared --output-format option for list commands."""

    return typer.Option(
        "--output-format",
        "-o",
        click_type=click.Choice(["json", "ndjson"]),
        help="Output format: 'json' (default envelope) or 'ndjson' (one JSON object per line).",
    )
