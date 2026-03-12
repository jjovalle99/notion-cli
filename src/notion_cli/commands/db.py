from functools import partial
from typing import Annotated

import typer

from notion_cli._async import await_with_timeout, paginate, paginate_stream, run_async
from notion_cli.auth import resolve_token
from notion_cli.options import (
    dry_run_option,
    fields_option,
    output_format_option,
    timeout_option,
    token_option,
)
from notion_cli.output import (
    ExitCode,
    echo_dry_run,
    echo_list,
    format_error,
    format_json,
    project_fields,
    stream_ndjson_page,
)
from notion_cli.parsing import extract_id, parse_fields


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
    fields: Annotated[str | None, fields_option()] = None,
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
    fields_set = parse_fields(fields)
    did = extract_id(db_id)
    from notion_client import AsyncClient

    async with AsyncClient(auth=resolved_token) as client:
        result = await await_with_timeout(client.databases.retrieve(did), timeout)
    typer.echo(format_json(project_fields(result, fields_set)))


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
    where: Annotated[
        list[str] | None,
        typer.Option(
            "--where",
            "-w",
            help=(
                "Human-friendly filter expression. Format: 'Property operator value'. "
                "Operators: =, !=, >, <, >=, <=, contains, before, after. "
                "Repeat for AND logic. Fetches DB schema to resolve property types. "
                "Example: --where 'Status = Done' --where 'Priority > 3'"
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
    fields: Annotated[
        str | None,
        typer.Option("--fields", help="Comma-separated list of fields to include in output."),
    ] = None,
    stream: Annotated[
        bool,
        typer.Option(
            "--stream",
            help="Stream results as NDJSON (one JSON object per line), writing each page immediately.",
        ),
    ] = False,
    output_format: Annotated[str, output_format_option()] = "json",
    token: Annotated[str | None, token_option()] = None,
    timeout: Annotated[float | None, timeout_option()] = None,
) -> None:
    """Query pages in a Notion database with optional filter and sort.

    Returns matching pages with their properties. Supports Notion's full
    compound filter syntax (and/or logic across property types) and
    multi-level sorting.

    Examples:
        notion db query abc123 --where "Status = Done"
        notion db query abc123 --where "Status = Done" --where "Priority > 3"
        notion db query abc123 --filter '{"property": "Status", "select": {"equals": "Done"}}'
        notion db query abc123 --sort '[{"property": "Date", "direction": "descending"}]'
    """

    from notion_cli.parsing import parse_json, validate_limit

    resolved_token = resolve_token(token=token)
    fields_set = parse_fields(fields)
    did = extract_id(db_id)
    validate_limit(limit)

    if where and filter is not None:
        typer.echo(
            format_error("conflicting_args", "--where and --filter are mutually exclusive."),
            err=True,
        )
        raise SystemExit(ExitCode.BAD_ARGS)

    kwargs: dict[str, object] = {}
    if filter is not None:
        kwargs["filter"] = parse_json(filter, expected_type=dict, label="--filter")
    if sort is not None:
        kwargs["sorts"] = parse_json(sort, expected_type=list, label="--sort")

    from notion_client import AsyncClient

    async with AsyncClient(auth=resolved_token) as client:
        if where:
            from notion_cli.parsing import parse_where

            schema = await await_with_timeout(client.databases.retrieve(did), timeout)
            props = schema.get("properties") or {}
            sorted_names = sorted(props, key=len, reverse=True)
            filters: list[dict[str, object]] = []
            for expr in where:
                prop_type = "rich_text"
                resolved = False
                for name in sorted_names:
                    if expr.startswith(name):
                        prop_type = props[name].get("type", "rich_text")
                        resolved = True
                        break
                if not resolved:
                    typer.echo(
                        format_error(
                            "unresolved_property",
                            f"No matching property in database schema for: {expr!r}. Defaulting to rich_text filter.",
                        ),
                        err=True,
                    )
                filters.append(parse_where(expr, prop_type))
            if len(filters) == 1:
                kwargs["filter"] = filters[0]
            else:
                kwargs["filter"] = {"and": filters}
        if stream:
            async for page_results in paginate_stream(
                partial(client.data_sources.query, did), kwargs, timeout, limit=limit
            ):
                stream_ndjson_page(page_results, fields_set)
        else:
            all_results, envelope = await paginate(
                partial(client.data_sources.query, did), kwargs, timeout, limit=limit
            )

    if not stream:
        echo_list(project_fields(all_results, fields_set), envelope, output_format)


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
    dry_run: Annotated[bool, dry_run_option()] = False,
    fields: Annotated[str | None, fields_option()] = None,
    token: Annotated[str | None, token_option()] = None,
    timeout: Annotated[float | None, timeout_option()] = None,
) -> None:
    """Create a new Notion database under a parent page.

    Creates a database with a title and optional properties schema.
    A 'Name' title property is included by default.

    Examples:
        notion db create --parent abc123 --title "Task Board"
        notion db create -p abc123 -t "Tracker" --properties '{"Status": {"select": {}}}'
    """
    resolved_token = resolve_token(token=token)
    fields_set = parse_fields(fields)
    parent_id = extract_id(parent)

    kwargs: dict[str, object] = {
        "parent": {"page_id": parent_id},
        "title": [{"text": {"content": title}}],
        "properties": {"Name": {"title": {}}},
    }

    if properties is not None:
        from notion_cli.parsing import parse_json

        parsed_props = parse_json(properties, expected_type=dict, label="--properties")
        kwargs["properties"] = {**kwargs["properties"], **parsed_props}

    if dry_run:
        echo_dry_run("db create", kwargs)

    from notion_client import AsyncClient

    async with AsyncClient(auth=resolved_token) as client:
        result = await await_with_timeout(client.data_sources.create(**kwargs), timeout)
    typer.echo(format_json(project_fields(result, fields_set)))


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
    dry_run: Annotated[bool, dry_run_option()] = False,
    fields: Annotated[str | None, fields_option()] = None,
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
    fields_set = parse_fields(fields)
    did = extract_id(db_id)

    kwargs: dict[str, object] = {}
    if title is not None:
        kwargs["title"] = [{"text": {"content": title}}]
    if properties is not None:
        from notion_cli.parsing import parse_json

        kwargs["properties"] = parse_json(properties, expected_type=dict, label="--properties")

    if not kwargs:
        typer.echo(
            format_error("missing_args", "Provide at least --title or --properties."), err=True
        )
        raise SystemExit(ExitCode.BAD_ARGS)

    if dry_run:
        echo_dry_run("db update", {"database_id": did, **kwargs})

    from notion_client import AsyncClient

    async with AsyncClient(auth=resolved_token) as client:
        result = await await_with_timeout(client.data_sources.update(did, **kwargs), timeout)
    typer.echo(format_json(project_fields(result, fields_set)))
