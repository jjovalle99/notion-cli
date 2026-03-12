from typing import Annotated

import click
import typer

from notion_cli._async import paginate, run_async
from notion_cli.auth import resolve_token
from notion_cli.options import fields_option, output_format_option, timeout_option, token_option
from notion_cli.output import echo_list, project_fields


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
    output_format: Annotated[str, output_format_option()] = "json",
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
    from notion_cli.parsing import parse_fields, validate_limit

    resolved_token = resolve_token(token=token)
    fields_set = parse_fields(fields)
    validate_limit(limit)
    kwargs: dict[str, object] = {"query": query}
    if type is not None:
        kwargs["filter"] = {"property": "object", "value": type}

    from notion_client import AsyncClient

    async with AsyncClient(auth=resolved_token) as client:
        all_results, envelope = await paginate(client.search, kwargs, timeout, limit=limit)

    echo_list(project_fields(all_results, fields_set), envelope, output_format)
