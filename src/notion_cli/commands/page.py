import json
from typing import Annotated

import typer

from notion_cli._async import await_with_timeout, run_async
from notion_cli.auth import resolve_token
from notion_cli.options import timeout_option, token_option
from notion_cli.output import ExitCode, format_json
from notion_cli.parsing import extract_id, read_content

page_app = typer.Typer(
    name="page",
    help=(
        "Create, read, update, move, and duplicate Notion pages.\n\n"
        "All page IDs accept either a raw UUID or a full Notion URL."
    ),
    no_args_is_help=True,
)


@page_app.command()
@run_async
async def get(
    page_id: Annotated[
        str,
        typer.Argument(
            help="Page ID or Notion URL. Example: 'abc123' or 'https://notion.so/My-Page-abc123'.",
        ),
    ],
    token: Annotated[str | None, token_option()] = None,
    timeout: Annotated[float | None, timeout_option()] = None,
) -> None:
    """Retrieve a single Notion page by ID or URL.

    Returns the full page object including properties, parent, timestamps,
    and URL. Does not include page content blocks — use 'notion block get'
    for that.

    Examples:
        notion page get abc123def456abc123def456abc123de
        notion page get https://notion.so/My-Page-abc123def456abc123def456abc123de
    """
    resolved_token = resolve_token(token=token)
    pid = extract_id(page_id)
    from notion_client import AsyncClient

    async with AsyncClient(auth=resolved_token) as client:
        result = await await_with_timeout(client.pages.retrieve(pid), timeout)
    typer.echo(format_json(result))


@page_app.command()
@run_async
async def create(
    parent: Annotated[
        str,
        typer.Option(
            "--parent",
            "-p",
            help=(
                "Parent page or database ID/URL where the new page will be created. "
                "Example: 'abc123' or 'https://notion.so/Parent-abc123'."
            ),
        ),
    ],
    title: Annotated[
        str,
        typer.Option(
            "--title",
            "-t",
            help="Page title. Example: 'Meeting Notes 2026-03-10'.",
        ),
    ],
    content: Annotated[
        str | None,
        typer.Option(
            "--content",
            "-c",
            help=(
                "Page body as Notion-flavored Markdown. "
                "Use '@path/to/file.md' to read from a file, or '-' for stdin. "
                "Example: '# Heading\\nSome paragraph text'."
            ),
        ),
    ] = None,
    icon: Annotated[
        str | None,
        typer.Option(
            "--icon",
            help="Page icon as an emoji. Example: '📝'.",
        ),
    ] = None,
    token: Annotated[str | None, token_option()] = None,
    timeout: Annotated[float | None, timeout_option()] = None,
) -> None:
    """Create a new Notion page under a parent page or database.

    Content is provided as Notion-flavored Markdown via --content.
    The page is created with a title property and optional body.

    Examples:
        notion page create --parent abc123 --title "New Page"
        notion page create -p abc123 -t "Notes" -c "# Summary\\nKey points here"
        notion page create -p abc123 -t "Notes" -c @notes.md
    """
    resolved_token = resolve_token(token=token)
    parent_id = extract_id(parent)

    kwargs: dict[str, object] = {
        "parent": {"page_id": parent_id},
        "properties": {"title": {"title": [{"text": {"content": title}}]}},
    }

    if content is not None:
        kwargs["content"] = read_content(content)

    if icon is not None:
        kwargs["icon"] = {"type": "emoji", "emoji": icon}

    from notion_client import AsyncClient

    async with AsyncClient(auth=resolved_token) as client:
        result = await await_with_timeout(client.pages.create(**kwargs), timeout)
    typer.echo(format_json(result))


@page_app.command()
@run_async
async def update(
    page_id: Annotated[
        str,
        typer.Argument(
            help="Page ID or Notion URL to update.",
        ),
    ],
    title: Annotated[
        str | None,
        typer.Option(
            "--title",
            "-t",
            help="New page title.",
        ),
    ] = None,
    icon: Annotated[
        str | None,
        typer.Option(
            "--icon",
            help="New page icon as an emoji. Example: '🔥'.",
        ),
    ] = None,
    properties: Annotated[
        str | None,
        typer.Option(
            "--properties",
            help=(
                "Properties as a JSON string. Use this to update any page property "
                "including database row fields like Status, Date, or custom fields. "
                'Example: \'{"Status": {"select": {"name": "Done"}}}\''
            ),
        ),
    ] = None,
    archive: Annotated[
        bool | None,
        typer.Option(
            "--archive/--no-archive",
            help="Archive (--archive) or unarchive (--no-archive) the page.",
        ),
    ] = None,
    token: Annotated[str | None, token_option()] = None,
    timeout: Annotated[float | None, timeout_option()] = None,
) -> None:
    """Update properties of an existing Notion page.

    Modify the title, icon, archive status, or any page property. For database
    rows, use --properties to set fields like Status, Date, or custom properties.
    Only specified fields are changed; omitted fields remain untouched.
    Using --title together with a "title" key in --properties is an error.

    Examples:
        notion page update abc123 --title "Renamed Page"
        notion page update abc123 --archive
        notion page update abc123 --properties '{"Status": {"select": {"name": "Done"}}}'
    """

    resolved_token = resolve_token(token=token)
    pid = extract_id(page_id)

    kwargs: dict[str, object] = {"page_id": pid}
    props: dict[str, object] = {}
    if properties is not None:
        parsed_props = json.loads(properties)
        if title is not None and "title" in parsed_props:
            from notion_cli.output import format_error

            typer.echo(
                format_error(
                    "conflicting_args",
                    "--title conflicts with 'title' key in --properties. Use one or the other.",
                ),
                err=True,
            )
            raise SystemExit(ExitCode.BAD_ARGS)
        props.update(parsed_props)
    if title is not None:
        props["title"] = {"title": [{"text": {"content": title}}]}
    if props:
        kwargs["properties"] = props
    if icon is not None:
        kwargs["icon"] = {"type": "emoji", "emoji": icon}
    if archive is not None:
        kwargs["archived"] = archive

    from notion_client import AsyncClient

    async with AsyncClient(auth=resolved_token) as client:
        result = await await_with_timeout(client.pages.update(**kwargs), timeout)
    typer.echo(format_json(result))


@page_app.command()
@run_async
async def move(
    page_id: Annotated[
        str,
        typer.Argument(help="Page ID or Notion URL to move."),
    ],
    to: Annotated[
        str,
        typer.Option(
            "--to",
            help="New parent page ID or URL. Example: 'abc123' or a full Notion URL.",
        ),
    ],
    token: Annotated[str | None, token_option()] = None,
    timeout: Annotated[float | None, timeout_option()] = None,
) -> None:
    """Move a Notion page to a different parent.

    Changes the parent of the specified page. The new parent must be a page
    the integration has access to.

    Examples:
        notion page move abc123 --to def456
        notion page move abc123 --to https://notion.so/New-Parent-def456
    """
    resolved_token = resolve_token(token=token)
    pid = extract_id(page_id)
    new_parent_id = extract_id(to)

    from notion_client import AsyncClient

    async with AsyncClient(auth=resolved_token) as client:
        result = await await_with_timeout(
            client.pages.move(
                page_id=pid,
                parent={"page_id": new_parent_id},
            ),
            timeout,
        )
    typer.echo(format_json(result))


@page_app.command()
@run_async
async def duplicate(
    page_id: Annotated[
        str,
        typer.Argument(help="Page ID or Notion URL to duplicate."),
    ],
    token: Annotated[str | None, token_option()] = None,
    timeout: Annotated[float | None, timeout_option()] = None,
) -> None:
    """Duplicate a Notion page.

    Creates a copy of the page including its properties. The duplicate is placed
    in the same parent as the original. This is an async operation — the response
    may return before the full copy is complete.

    Examples:
        notion page duplicate abc123
        notion page duplicate https://notion.so/My-Page-abc123
    """
    resolved_token = resolve_token(token=token)
    pid = extract_id(page_id)

    from notion_client import AsyncClient

    async with AsyncClient(auth=resolved_token) as client:
        original = await await_with_timeout(client.pages.retrieve(pid), timeout)
        create_kwargs: dict[str, object] = {
            "parent": original["parent"],
            "properties": original["properties"],
        }
        if original.get("icon") is not None:
            create_kwargs["icon"] = original["icon"]
        if original.get("cover") is not None:
            create_kwargs["cover"] = original["cover"]
        result = await await_with_timeout(client.pages.create(**create_kwargs), timeout)
    typer.echo(format_json(result))
