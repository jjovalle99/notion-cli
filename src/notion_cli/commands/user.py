from typing import Annotated

import typer

from notion_cli._async import run_async
from notion_cli.auth import resolve_token
from notion_cli.options import token_option
from notion_cli.output import format_json
from notion_cli.parsing import extract_id

user_app = typer.Typer(
    name="user",
    help=(
        "List and retrieve Notion workspace users.\n\n"
        "Includes both people and bot (integration) users. "
        "Use 'notion user me' to get the current bot user info."
    ),
    no_args_is_help=True,
)


@user_app.command(name="list")
@run_async
async def list_users(
    token: Annotated[str | None, token_option()] = None,
) -> None:
    """List all users in the Notion workspace.

    Returns both people and bot users with their IDs, names, and types.

    Examples:
        notion user list
    """
    resolved_token = resolve_token(token=token)
    from notion_client import AsyncClient

    async with AsyncClient(auth=resolved_token) as client:
        result = await client.users.list()
    typer.echo(format_json(result))


@user_app.command()
@run_async
async def get(
    user_id: Annotated[
        str,
        typer.Argument(help="User ID (UUID format)."),
    ],
    token: Annotated[str | None, token_option()] = None,
) -> None:
    """Retrieve a specific Notion user by ID.

    Returns the user object including name, email (for people), and type.

    Examples:
        notion user get aabbccdd-1122-3344-5566-778899001122
    """
    resolved_token = resolve_token(token=token)
    uid = extract_id(user_id)
    from notion_client import AsyncClient

    async with AsyncClient(auth=resolved_token) as client:
        result = await client.users.retrieve(uid)
    typer.echo(format_json(result))


@user_app.command()
@run_async
async def me(
    token: Annotated[str | None, token_option()] = None,
) -> None:
    """Get the current bot user and workspace info.

    Returns the integration's bot user object, including the workspace
    name and ID. Useful for verifying authentication.

    Examples:
        notion user me
    """
    resolved_token = resolve_token(token=token)
    from notion_client import AsyncClient

    async with AsyncClient(auth=resolved_token) as client:
        result = await client.users.me()
    typer.echo(format_json(result))
