from typing import Annotated

import typer

from notion_cli._async import run_async
from notion_cli.auth import resolve_token
from notion_cli.options import timeout_option, token_option
from notion_cli.output import format_json


@run_async
async def search(
    query: Annotated[
        str,
        typer.Argument(
            help=(
                "Search query matched against page and database titles. "
                "Example: 'meeting notes' or 'Q1 roadmap'."
            ),
        ),
    ],
    type: Annotated[
        str | None,
        typer.Option(
            "--type",
            "-t",
            help=(
                "Filter results by object type. "
                "Accepted values: 'page', 'database'. "
                "Omit to return both."
            ),
        ),
    ] = None,
    token: Annotated[str | None, token_option()] = None,
    timeout: Annotated[float | None, timeout_option()] = None,
) -> None:
    """Search the Notion workspace by title.

    Returns pages and databases matching the query. Results are ordered by
    relevance. Only content shared with the integration is searchable.

    Examples:
        notion search "meeting notes"
        notion search "Q1 roadmap" --type page
        notion search "projects" --type database
    """
    resolved_token = resolve_token(token=token)
    kwargs: dict[str, object] = {"query": query}
    if type is not None:
        kwargs["filter"] = {"property": "object", "value": type}

    import asyncio

    from notion_client import AsyncClient

    async with AsyncClient(auth=resolved_token) as client:
        coro = client.search(**kwargs)
        result = await (asyncio.wait_for(coro, timeout=timeout) if timeout else coro)

    typer.echo(format_json(result))
