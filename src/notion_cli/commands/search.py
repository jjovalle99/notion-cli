from typing import Annotated

import click
import typer

from notion_cli._async import await_with_timeout, run_async
from notion_cli.auth import resolve_token
from notion_cli.options import fields_option, timeout_option, token_option
from notion_cli.output import format_json, project_fields


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
            click_type=click.Choice(["page", "database"]),
            help="Filter results by object type. Omit to return both.",
        ),
    ] = None,
    limit: Annotated[
        int | None,
        typer.Option(
            "--limit",
            "-l",
            help="Maximum number of results to return. Omit to return all.",
        ),
    ] = None,
    fields: Annotated[str | None, fields_option()] = None,
    token: Annotated[str | None, token_option()] = None,
    timeout: Annotated[float | None, timeout_option()] = None,
) -> None:
    """Search the Notion workspace by title.

    Returns pages and databases matching the query. Results are ordered by
    relevance. Only content shared with the integration is searchable.

    Examples:
        notion search "meeting notes"
        notion search "Q1 roadmap" --type page
        notion search "projects" --limit 10
    """
    from notion_cli.parsing import validate_limit

    resolved_token = resolve_token(token=token)
    fields_set = set(fields.split(",")) if fields else None
    validate_limit(limit)
    kwargs: dict[str, object] = {"query": query}
    if type is not None:
        kwargs["filter"] = {"property": "object", "value": type}
    if limit is not None:
        kwargs["page_size"] = min(limit, 100)

    all_results: list[object] = []
    from notion_client import AsyncClient

    async with AsyncClient(auth=resolved_token) as client:
        result = await await_with_timeout(client.search(**kwargs), timeout)
        all_results.extend(result.get("results") or [])

        while (
            result.get("has_more")
            and result.get("next_cursor")
            and result.get("results")
            and (limit is None or len(all_results) < limit)
        ):
            kwargs["start_cursor"] = result["next_cursor"]
            if limit is not None:
                kwargs["page_size"] = min(limit - len(all_results), 100)
            result = await await_with_timeout(client.search(**kwargs), timeout)
            all_results.extend(result.get("results") or [])

        envelope = {k: v for k, v in result.items() if k not in ("results", "has_more")}

    if limit is not None:
        all_results = all_results[:limit]
    typer.echo(
        format_json(
            {**envelope, "results": project_fields(all_results, fields_set), "has_more": False}
        )
    )
