from typing import Annotated

import typer

from notion_cli._async import await_with_timeout, run_async
from notion_cli.auth import resolve_token
from notion_cli.options import timeout_option, token_option
from notion_cli.output import format_json
from notion_cli.parsing import extract_id


db_app = typer.Typer(
    name="db",
    help=(
        "Create, read, query, and update Notion databases.\n\n"
        "All database IDs accept either a raw UUID or a full Notion URL."
    ),
    no_args_is_help=True,
)


@db_app.command()
@run_async
async def get(
    db_id: Annotated[
        str,
        typer.Argument(
            help="Database ID or Notion URL. Example: 'abc123' or a full Notion database URL.",
        ),
    ],
    token: Annotated[str | None, token_option()] = None,
    timeout: Annotated[float | None, timeout_option()] = None,
) -> None:
    """Retrieve a Notion database schema by ID or URL.

    Returns the database object including title, properties schema,
    parent, and timestamps.

    Examples:
        notion db get aabbccdd11223344556677889900aabb
        notion db get https://notion.so/myworkspace/aabbccdd11223344556677889900aabb?v=...
    """
    resolved_token = resolve_token(token=token)
    did = extract_id(db_id)
    from notion_client import AsyncClient

    async with AsyncClient(auth=resolved_token) as client:
        result = await await_with_timeout(client.databases.retrieve(did), timeout)
    typer.echo(format_json(result))


@db_app.command()
@run_async
async def query(
    db_id: Annotated[
        str,
        typer.Argument(
            help="Database or data source ID/URL to query.",
        ),
    ],
    filter: Annotated[
        str | None,
        typer.Option(
            "--filter",
            "-f",
            help=(
                "Filter as a JSON string. Uses Notion's filter object format. "
                'Example: \'{"property": "Status", "select": {"equals": "Done"}}\''
            ),
        ),
    ] = None,
    sort: Annotated[
        str | None,
        typer.Option(
            "--sort",
            "-s",
            help=(
                "Sort as a JSON array. Each element has 'property' and 'direction'. "
                'Example: \'[{"property": "Created", "direction": "descending"}]\''
            ),
        ),
    ] = None,
    limit: Annotated[
        int | None,
        typer.Option(
            "--limit",
            "-l",
            help="Maximum number of rows to return. All rows are buffered in memory; use --limit on large databases.",
        ),
    ] = None,
    token: Annotated[str | None, token_option()] = None,
    timeout: Annotated[float | None, timeout_option()] = None,
) -> None:
    """Query pages in a Notion database with optional filter and sort.

    Returns matching pages with their properties. Supports Notion's full
    compound filter syntax (and/or logic across property types) and
    multi-level sorting.

    Examples:
        notion db query aabbccdd11223344556677889900aabb
        notion db query abc123 --filter '{"property": "Status", "select": {"equals": "Done"}}'
        notion db query abc123 --sort '[{"property": "Date", "direction": "descending"}]'
    """
    from notion_cli.parsing import parse_json, validate_limit

    resolved_token = resolve_token(token=token)
    did = extract_id(db_id)
    validate_limit(limit)

    kwargs: dict[str, object] = {}
    if filter is not None:
        kwargs["filter"] = parse_json(filter, expected_type=dict, label="--filter")
    if sort is not None:
        kwargs["sorts"] = parse_json(sort, expected_type=list, label="--sort")
    if limit is not None:
        kwargs["page_size"] = min(limit, 100)

    all_results: list[object] = []
    from notion_client import AsyncClient

    async with AsyncClient(auth=resolved_token) as client:
        result = await await_with_timeout(client.data_sources.query(did, **kwargs), timeout)
        all_results.extend(result.get("results", []))

        while (
            result.get("has_more")
            and result.get("next_cursor")
            and result.get("results")
            and (limit is None or len(all_results) < limit)
        ):
            kwargs["start_cursor"] = result["next_cursor"]
            if limit is not None:
                kwargs["page_size"] = min(limit - len(all_results), 100)
            result = await await_with_timeout(client.data_sources.query(did, **kwargs), timeout)
            all_results.extend(result.get("results", []))

        envelope = {k: v for k, v in result.items() if k not in ("results", "has_more")}

    if limit is not None:
        all_results = all_results[:limit]
    typer.echo(format_json({**envelope, "results": all_results, "has_more": False}))


@db_app.command()
@run_async
async def create(
    parent: Annotated[
        str,
        typer.Option(
            "--parent",
            "-p",
            help="Parent page ID or URL where the database will be created.",
        ),
    ],
    title: Annotated[
        str,
        typer.Option(
            "--title",
            "-t",
            help="Database title. Example: 'Project Tracker'.",
        ),
    ],
    properties: Annotated[
        str | None,
        typer.Option(
            "--properties",
            help=(
                "Properties schema as a JSON string. "
                'Example: \'{"Status": {"select": {"options": [{"name": "Todo"}]}}}\''
            ),
        ),
    ] = None,
    token: Annotated[str | None, token_option()] = None,
    timeout: Annotated[float | None, timeout_option()] = None,
) -> None:
    """Create a new Notion database under a parent page.

    Creates a database with a title and optional properties schema.
    A 'Name' title property is always included automatically by Notion.

    Examples:
        notion db create --parent abc123 --title "Task Board"
        notion db create -p abc123 -t "Tracker" --properties '{"Status": {"select": {}}}'
    """
    resolved_token = resolve_token(token=token)
    parent_id = extract_id(parent)

    kwargs: dict[str, object] = {
        "parent": {"page_id": parent_id},
        "title": [{"text": {"content": title}}],
        "properties": {"Name": {"title": {}}},
    }

    if properties is not None:
        from notion_cli.parsing import parse_json

        parsed_props = parse_json(properties, expected_type=dict, label="--properties")
        kwargs["properties"] = {**kwargs["properties"], **parsed_props}  # type: ignore[arg-type]

    from notion_client import AsyncClient

    async with AsyncClient(auth=resolved_token) as client:
        result = await await_with_timeout(client.data_sources.create(**kwargs), timeout)
    typer.echo(format_json(result))


@db_app.command()
@run_async
async def update(
    db_id: Annotated[
        str,
        typer.Argument(help="Database ID or URL to update."),
    ],
    title: Annotated[
        str | None,
        typer.Option(
            "--title",
            "-t",
            help="New database title.",
        ),
    ] = None,
    properties: Annotated[
        str | None,
        typer.Option(
            "--properties",
            help="Updated properties schema as a JSON string.",
        ),
    ] = None,
    token: Annotated[str | None, token_option()] = None,
    timeout: Annotated[float | None, timeout_option()] = None,
) -> None:
    """Update a Notion database's title or properties schema.

    Only specified fields are modified; omitted fields remain unchanged.

    Examples:
        notion db update abc123 --title "Renamed DB"
        notion db update abc123 --properties '{"Priority": {"select": {}}}'
    """
    resolved_token = resolve_token(token=token)
    did = extract_id(db_id)

    kwargs: dict[str, object] = {}
    if title is not None:
        kwargs["title"] = [{"text": {"content": title}}]
    if properties is not None:
        from notion_cli.parsing import parse_json

        kwargs["properties"] = parse_json(properties, expected_type=dict, label="--properties")

    from notion_client import AsyncClient

    async with AsyncClient(auth=resolved_token) as client:
        result = await await_with_timeout(client.data_sources.update(did, **kwargs), timeout)
    typer.echo(format_json(result))
