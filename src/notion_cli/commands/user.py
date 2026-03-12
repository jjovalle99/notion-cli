from typing import Annotated

import typer

from notion_cli._async import await_with_timeout, paginate, run_async
from notion_cli.auth import resolve_token
from notion_cli.options import fields_option, output_format_option, timeout_option, token_option
from notion_cli.output import echo_list, format_json, project_fields
from notion_cli.parsing import extract_id, parse_fields

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
    limit: Annotated[
        int | None,
        typer.Option(
            "--limit",
            "-l",
            help="Maximum number of users to return. Omit to return all.",
        ),
    ] = None,
    fields: Annotated[str | None, fields_option()] = None,
    output_format: Annotated[str, output_format_option()] = "json",
    token: Annotated[str | None, token_option()] = None,
    timeout: Annotated[float | None, timeout_option()] = None,
) -> None:
    """List all users in the Notion workspace.

    Returns both people and bot users with their IDs, names, and types.

    Examples:
        notion user list
        notion user list --limit 10
    """
    from notion_cli.parsing import validate_limit

    resolved_token = resolve_token(token=token)
    fields_set = parse_fields(fields)
    validate_limit(limit)

    from notion_client import AsyncClient

    async with AsyncClient(auth=resolved_token) as client:
        all_results, envelope = await paginate(client.users.list, {}, timeout, limit=limit)

    echo_list(project_fields(all_results, fields_set), envelope, output_format)


@user_app.command()
@run_async
async def get(
    user_id: Annotated[
        str,
        typer.Argument(help="User ID or Notion URL."),
    ],
    fields: Annotated[str | None, fields_option()] = None,
    token: Annotated[str | None, token_option()] = None,
    timeout: Annotated[float | None, timeout_option()] = None,
) -> None:
    """Retrieve a specific Notion user by ID.

    Returns the user object including name, email (for people), and type.

    Examples:
        notion user get aabbccdd-1122-3344-5566-778899001122
    """
    resolved_token = resolve_token(token=token)
    fields_set = parse_fields(fields)
    uid = extract_id(user_id)
    from notion_client import AsyncClient

    async with AsyncClient(auth=resolved_token) as client:
        result = await await_with_timeout(client.users.retrieve(uid), timeout)
    typer.echo(format_json(project_fields(result, fields_set)))


@user_app.command()
@run_async
async def me(
    fields: Annotated[str | None, fields_option()] = None,
    token: Annotated[str | None, token_option()] = None,
    timeout: Annotated[float | None, timeout_option()] = None,
) -> None:
    """Get the current bot user and workspace info.

    Returns the integration's bot user object, including the workspace
    name and ID. Useful for verifying authentication.

    Examples:
        notion user me
    """
    resolved_token = resolve_token(token=token)
    fields_set = parse_fields(fields)
    from notion_client import AsyncClient

    async with AsyncClient(auth=resolved_token) as client:
        result = await await_with_timeout(client.users.me(), timeout)
    typer.echo(format_json(project_fields(result, fields_set)))
