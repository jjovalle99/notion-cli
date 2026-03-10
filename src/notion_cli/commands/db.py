import json as json_mod
from typing import Annotated

import typer
from notion_client import AsyncClient

from notion_cli._async import run_async
from notion_cli.auth import resolve_token
from notion_cli.output import format_json
from notion_cli.parsing import extract_id


def _token_option() -> typer.Option:
    return typer.Option(
        "--token",
        envvar="NOTION_API_KEY",
        help="Notion API token. Defaults to NOTION_API_KEY env var.",
    )


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
    token: Annotated[str | None, _token_option()] = None,
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
    async with AsyncClient(auth=resolved_token) as client:
        result = await client.databases.retrieve(did)
    typer.echo(format_json(result))


@db_app.command()
@run_async
async def query(
    db_id: Annotated[
        str,
        typer.Argument(
            help="Database ID or URL to query.",
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
            help="Maximum number of results to return. Omit to return all.",
        ),
    ] = None,
    token: Annotated[str | None, _token_option()] = None,
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
    resolved_token = resolve_token(token=token)
    did = extract_id(db_id)

    kwargs: dict[str, object] = {"database_id": did}
    if filter is not None:
        kwargs["filter"] = json_mod.loads(filter)
    if sort is not None:
        kwargs["sorts"] = json_mod.loads(sort)
    if limit is not None:
        kwargs["page_size"] = min(limit, 100)

    async with AsyncClient(auth=resolved_token) as client:
        result = await client.databases.query(**kwargs)
    typer.echo(format_json(result))


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
    token: Annotated[str | None, _token_option()] = None,
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
        parsed_props = json_mod.loads(properties)
        kwargs["properties"] = {**kwargs["properties"], **parsed_props}  # type: ignore[arg-type]

    async with AsyncClient(auth=resolved_token) as client:
        result = await client.databases.create(**kwargs)
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
    token: Annotated[str | None, _token_option()] = None,
) -> None:
    """Update a Notion database's title or properties schema.

    Only specified fields are modified; omitted fields remain unchanged.

    Examples:
        notion db update abc123 --title "Renamed DB"
        notion db update abc123 --properties '{"Priority": {"select": {}}}'
    """
    resolved_token = resolve_token(token=token)
    did = extract_id(db_id)

    kwargs: dict[str, object] = {"database_id": did}
    if title is not None:
        kwargs["title"] = [{"text": {"content": title}}]
    if properties is not None:
        kwargs["properties"] = json_mod.loads(properties)

    async with AsyncClient(auth=resolved_token) as client:
        result = await client.databases.update(**kwargs)
    typer.echo(format_json(result))
