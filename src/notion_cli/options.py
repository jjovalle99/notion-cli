import typer


def token_option() -> typer.Option:
    """Shared --token option for all commands."""
    return typer.Option(
        "--token",
        envvar="NOTION_API_KEY",
        help="Notion API token. Defaults to NOTION_API_KEY env var.",
    )


def timeout_option() -> typer.Option:
    """Shared --timeout option for all commands."""
    return typer.Option(
        "--timeout",
        help="API request timeout in seconds. Omit for no timeout.",
    )
