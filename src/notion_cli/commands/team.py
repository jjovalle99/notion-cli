from typing import Annotated

import typer
from notion_client import AsyncClient

from notion_cli._async import run_async
from notion_cli.auth import resolve_token
from notion_cli.output import format_json

team_app = typer.Typer(
    name="team",
    help=(
        "List Notion teamspaces.\n\n"
        "Teamspaces (formerly called workspaces) organize content and members. "
        "The integration must have access to see teamspace information."
    ),
    no_args_is_help=True,
)


def _token_option() -> typer.Option:
    return typer.Option(
        "--token",
        envvar="NOTION_API_KEY",
        help="Notion API token. Defaults to NOTION_API_KEY env var.",
    )


@team_app.command(name="list")
@run_async
async def list_teams(
    token: Annotated[str | None, _token_option()] = None,
) -> None:
    """List all teamspaces accessible to the integration.

    Returns teamspace IDs and names. Requires the integration to have
    teamspace-level access.

    Examples:
        notion team list
    """
    resolved_token = resolve_token(token=token)
    async with AsyncClient(auth=resolved_token) as client:
        result = await client.request(
            path="teamspaces",
            method="GET",
        )
    typer.echo(format_json(result))
