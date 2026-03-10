from typing import Annotated

import typer

from notion_cli._async import run_async
from notion_cli.auth import resolve_token
from notion_cli.options import timeout_option, token_option
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


@team_app.command(name="list")
@run_async
async def list_teams(
    token: Annotated[str | None, token_option()] = None,
    timeout: Annotated[float | None, timeout_option()] = None,
) -> None:
    """List all teamspaces accessible to the integration.

    Returns teamspace IDs and names. Requires the integration to have
    teamspace-level access.

    Examples:
        notion team list
    """
    resolved_token = resolve_token(token=token)
    import asyncio

    from notion_client import AsyncClient

    async with AsyncClient(auth=resolved_token) as client:
        coro = client.request(path="teamspaces", method="GET")
        result = await (asyncio.wait_for(coro, timeout=timeout) if timeout else coro)
    typer.echo(format_json(result))
