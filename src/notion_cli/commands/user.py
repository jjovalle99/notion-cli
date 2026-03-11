from typing import Annotated

import typer

from notion_cli._async import await_with_timeout, run_async
from notion_cli.auth import resolve_token
from notion_cli.options import timeout_option, token_option
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
    limit: Annotated[
        int | None,
        typer.Option(
            "--limit",
            "-l",
            help="Maximum number of users to return. Omit to return all.",
        ),
    ] = None,
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
    validate_limit(limit)
    kwargs: dict[str, object] = {}
    if limit is not None:
        kwargs["page_size"] = min(limit, 100)

    all_results: list[object] = []
    from notion_client import AsyncClient

    async with AsyncClient(auth=resolved_token) as client:
        result = await await_with_timeout(client.users.list(**kwargs), timeout)
        all_results.extend(result.get("results", []))

        while (
            result.get("has_more")
            and result.get("next_cursor")
            and result.get("results")
            and (limit is None or len(all_results) < limit)
        ):
            if limit is not None:
                kwargs["page_size"] = min(limit - len(all_results), 100)
            result = await await_with_timeout(
                client.users.list(start_cursor=result["next_cursor"], **kwargs), timeout
            )
            all_results.extend(result.get("results", []))

        envelope = {k: v for k, v in result.items() if k not in ("results", "has_more")}

    if limit is not None:
        all_results = all_results[:limit]
    typer.echo(format_json({**envelope, "results": all_results, "has_more": False}))


@user_app.command()
@run_async
async def get(
    user_id: Annotated[
        str,
        typer.Argument(help="User ID or Notion URL."),
    ],
    token: Annotated[str | None, token_option()] = None,
    timeout: Annotated[float | None, timeout_option()] = None,
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
        result = await await_with_timeout(client.users.retrieve(uid), timeout)
    typer.echo(format_json(result))


@user_app.command()
@run_async
async def me(
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
    from notion_client import AsyncClient

    async with AsyncClient(auth=resolved_token) as client:
        result = await await_with_timeout(client.users.me(), timeout)
    typer.echo(format_json(result))
