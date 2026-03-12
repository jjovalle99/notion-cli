from typing import Annotated

import click
import typer

from notion_cli._async import await_with_timeout, run_async
from notion_cli.auth import resolve_token
from notion_cli.options import dry_run_option, fields_option, timeout_option, token_option
from notion_cli.output import ExitCode, echo_dry_run, format_error, format_json, project_fields
from notion_cli.parsing import extract_id, parse_fields, read_content

_READ_ONLY_TYPES = frozenset(
    {"formula", "rollup", "created_time", "last_edited_time", "created_by", "last_edited_by"}
)

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
    full: Annotated[
        bool,
        typer.Option(
            "--full",
            help="Return page metadata, content blocks, and comments in one call.",
        ),
    ] = False,
    fields: Annotated[str | None, fields_option()] = None,
    token: Annotated[str | None, token_option()] = None,
    timeout: Annotated[float | None, timeout_option()] = None,
) -> None:
    """Retrieve a single Notion page by ID or URL.

    Returns the page object including properties, parent, timestamps,
    and URL. Use --full to also fetch content blocks and comments.

    Examples:
        notion page get abc123
        notion page get abc123 --full
        notion page get https://notion.so/My-Page-abc123
    """
    import asyncio

    resolved_token = resolve_token(token=token)
    fields_set = parse_fields(fields)
    pid = extract_id(page_id)
    from notion_client import AsyncClient

    async with AsyncClient(auth=resolved_token) as client:
        if full:
            from notion_cli._block_utils import fetch_children

            page_coro = await_with_timeout(client.pages.retrieve(pid), timeout)
            blocks_coro = fetch_children(client, pid, timeout)
            comments_coro = await_with_timeout(client.comments.list(block_id=pid), timeout)
            page_result, (block_list, _), comments_result = await asyncio.gather(
                page_coro, blocks_coro, comments_coro, return_exceptions=True
            )
            if isinstance(page_result, BaseException):
                raise page_result
            if isinstance(block_list, BaseException):
                raise block_list
            comments: list[object] = []
            if not isinstance(comments_result, BaseException):
                comments = list(comments_result.get("results") or [])
            combined: dict[str, object] = {
                "page": page_result,
                "blocks": block_list,
                "comments": comments,
            }
            typer.echo(format_json(project_fields(combined, fields_set)))
        else:
            result = await await_with_timeout(client.pages.retrieve(pid), timeout)
            typer.echo(format_json(project_fields(result, fields_set)))


@page_app.command()
@run_async
async def create(
    parent: Annotated[
        str | None,
        typer.Option(
            "--parent",
            "-p",
            help=(
                "Parent page or database ID/URL where the new page will be created. "
                "Example: 'abc123' or 'https://notion.so/Parent-abc123'."
            ),
        ),
    ] = None,
    title: Annotated[
        str | None,
        typer.Option(
            "--title",
            "-t",
            help="Page title. Example: 'Meeting Notes 2026-03-10'.",
        ),
    ] = None,
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
    parent_type: Annotated[
        str,
        typer.Option(
            "--parent-type",
            help="Parent type: 'page' (default) or 'database'.",
            click_type=click.Choice(["page", "database"]),
        ),
    ] = "page",
    stdin: Annotated[
        bool,
        typer.Option(
            "--stdin",
            help=(
                "Read NDJSON from stdin. Each line: "
                '{"parent": "id", "title": "...", "content": "...", "icon": "...", "parent_type": "page|database"}. '
                "Only parent and title are required per line."
            ),
        ),
    ] = False,
    dry_run: Annotated[bool, dry_run_option()] = False,
    fields: Annotated[str | None, fields_option()] = None,
    token: Annotated[str | None, token_option()] = None,
    timeout: Annotated[float | None, timeout_option()] = None,
) -> None:
    """Create a new Notion page under a parent page or database.

    Content is provided as Notion-flavored Markdown via --content.
    The page is created with a title property and optional body.

    When creating a row in a database, use --parent-type database.
    Use --stdin to create multiple pages from NDJSON input.

    Examples:
        notion page create --parent abc123 --title "New Page"
        notion page create -p abc123 -t "Notes" -c "# Summary\\nKey points here"
        notion page create -p abc123 -t "Notes" -c @notes.md
        notion page create -p db123 -t "Row" --parent-type database
        echo '{"parent":"abc","title":"A"}' | notion page create --stdin
    """
    resolved_token = resolve_token(token=token)
    fields_set = parse_fields(fields)

    if stdin:
        if dry_run:
            echo_dry_run("page create --stdin", {"note": "stdin batch does not support dry-run"})

        import sys

        from notion_cli._batch import process_batch

        from notion_client import AsyncClient

        async def _create_one(item: dict[str, object]) -> dict[str, object]:
            p = str(item.get("parent", ""))
            t = str(item.get("title", ""))
            if not p or not t:
                msg = "Each line requires 'parent' and 'title' fields."
                raise ValueError(msg)
            pid = extract_id(p)
            pt = str(item.get("parent_type", "page"))
            if pt not in ("page", "database"):
                msg = f"parent_type must be 'page' or 'database', got {pt!r}."
                raise ValueError(msg)
            kw: dict[str, object] = {
                "parent": {f"{pt}_id": pid},
                "properties": {"title": {"title": [{"text": {"content": t}}]}},
            }
            item_icon = item.get("icon")
            if item_icon is not None:
                kw["icon"] = {"type": "emoji", "emoji": item_icon}
            item_content = item.get("content")
            if item_content is not None:
                kw["markdown"] = read_content(str(item_content))
                return await await_with_timeout(
                    client.request(path="pages", method="POST", body=kw), timeout
                )
            return await await_with_timeout(client.pages.create(**kw), timeout)

        async with AsyncClient(auth=resolved_token, notion_version="2026-03-11") as client:
            exit_code = await process_batch(
                lines=sys.stdin,
                handler=_create_one,
                fields=fields_set,
            )
        raise SystemExit(exit_code)

    if parent is None or title is None:
        typer.echo(
            format_error("missing_args", "--parent and --title are required (or use --stdin)."),
            err=True,
        )
        raise SystemExit(ExitCode.BAD_ARGS)

    parent_id = extract_id(parent)

    parent_key = f"{parent_type}_id"
    kwargs: dict[str, object] = {
        "parent": {parent_key: parent_id},
        "properties": {"title": {"title": [{"text": {"content": title}}]}},
    }

    if icon is not None:
        kwargs["icon"] = {"type": "emoji", "emoji": icon}

    if content is not None:
        kwargs["markdown"] = read_content(content)

    if dry_run:
        echo_dry_run("page create", kwargs)

    from notion_client import AsyncClient

    async with AsyncClient(auth=resolved_token, notion_version="2026-03-11") as client:
        if content is not None:
            coro = client.request(path="pages", method="POST", body=kwargs)
        else:
            coro = client.pages.create(**kwargs)
        result = await await_with_timeout(coro, timeout)
    typer.echo(format_json(project_fields(result, fields_set)))


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
    dry_run: Annotated[bool, dry_run_option()] = False,
    fields: Annotated[str | None, fields_option()] = None,
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
    fields_set = parse_fields(fields)
    pid = extract_id(page_id)

    kwargs: dict[str, object] = {"page_id": pid}
    props: dict[str, object] = {}
    if properties is not None:
        from notion_cli.parsing import parse_json

        parsed_props = parse_json(properties, expected_type=dict, label="--properties")
        if title is not None and "title" in parsed_props:
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

    if len(kwargs) == 1:
        typer.echo(
            format_error(
                "missing_args",
                "Provide at least --title, --icon, --properties, or --archive.",
            ),
            err=True,
        )
        raise SystemExit(ExitCode.BAD_ARGS)

    if dry_run:
        echo_dry_run("page update", kwargs)

    from notion_client import AsyncClient

    async with AsyncClient(auth=resolved_token) as client:
        result = await await_with_timeout(client.pages.update(**kwargs), timeout)
    typer.echo(format_json(project_fields(result, fields_set)))


@page_app.command()
@run_async
async def move(
    page_id: Annotated[
        str | None,
        typer.Argument(help="Page ID or Notion URL to move."),
    ] = None,
    to: Annotated[
        str | None,
        typer.Option(
            "--to",
            help="New parent page ID or URL. Example: 'abc123' or a full Notion URL.",
        ),
    ] = None,
    stdin: Annotated[
        bool,
        typer.Option(
            "--stdin",
            help=('Read NDJSON from stdin. Each line: {"page_id": "id", "to": "parent_id"}.'),
        ),
    ] = False,
    dry_run: Annotated[bool, dry_run_option()] = False,
    fields: Annotated[str | None, fields_option()] = None,
    token: Annotated[str | None, token_option()] = None,
    timeout: Annotated[float | None, timeout_option()] = None,
) -> None:
    """Move a Notion page to a different parent.

    Changes the parent of the specified page. The new parent must be a page
    the integration has access to. Use --stdin to move multiple pages from
    NDJSON input.

    Examples:
        notion page move abc123 --to def456
        notion page move abc123 --to https://notion.so/New-Parent-def456
        echo '{"page_id":"abc","to":"def"}' | notion page move --stdin
    """
    resolved_token = resolve_token(token=token)
    fields_set = parse_fields(fields)

    if stdin:
        if dry_run:
            echo_dry_run("page move --stdin", {"note": "stdin batch does not support dry-run"})

        import sys

        from notion_cli._batch import process_batch

        from notion_client import AsyncClient

        async def _move_one(item: dict[str, object]) -> dict[str, object]:
            raw_pid = str(item.get("page_id", ""))
            raw_to = str(item.get("to", ""))
            if not raw_pid or not raw_to:
                msg = "Each line requires 'page_id' and 'to' fields."
                raise ValueError(msg)
            pid = extract_id(raw_pid)
            new_parent_id = extract_id(raw_to)
            return await await_with_timeout(
                client.pages.move(page_id=pid, parent={"page_id": new_parent_id}), timeout
            )

        async with AsyncClient(auth=resolved_token) as client:
            exit_code = await process_batch(
                lines=sys.stdin,
                handler=_move_one,
                fields=fields_set,
            )
        raise SystemExit(exit_code)

    if page_id is None or to is None:
        typer.echo(
            format_error("missing_args", "PAGE_ID and --to are required (or use --stdin)."),
            err=True,
        )
        raise SystemExit(ExitCode.BAD_ARGS)

    pid = extract_id(page_id)
    new_parent_id = extract_id(to)
    kwargs: dict[str, object] = {"page_id": pid, "parent": {"page_id": new_parent_id}}

    if dry_run:
        echo_dry_run("page move", kwargs)

    from notion_client import AsyncClient

    async with AsyncClient(auth=resolved_token) as client:
        result = await await_with_timeout(client.pages.move(**kwargs), timeout)
    typer.echo(format_json(project_fields(result, fields_set)))


@page_app.command()
@run_async
async def duplicate(
    page_id: Annotated[
        str,
        typer.Argument(help="Page ID or Notion URL to duplicate."),
    ],
    with_content: Annotated[
        bool,
        typer.Option(
            "--with-content",
            help="Also copy page content blocks (not just properties).",
        ),
    ] = False,
    destination: Annotated[
        str | None,
        typer.Option(
            "--destination",
            "-d",
            help="Parent page or database ID/URL for the copy. Defaults to same parent as original.",
        ),
    ] = None,
    destination_type: Annotated[
        str,
        typer.Option(
            "--destination-type",
            help="Destination type: 'page' (default) or 'database'.",
            click_type=click.Choice(["page", "database"]),
        ),
    ] = "page",
    dry_run: Annotated[bool, dry_run_option()] = False,
    fields: Annotated[str | None, fields_option()] = None,
    token: Annotated[str | None, token_option()] = None,
    timeout: Annotated[float | None, timeout_option()] = None,
) -> None:
    """Duplicate a Notion page.

    Creates a copy of the page including its properties, icon, and cover.
    Use --with-content to also copy block content. Use --destination to
    place the copy under a different parent page.

    Examples:
        notion page duplicate abc123
        notion page duplicate abc123 --with-content
        notion page duplicate abc123 --destination def456
    """
    resolved_token = resolve_token(token=token)
    fields_set = parse_fields(fields)
    pid = extract_id(page_id)
    dest_id = extract_id(destination) if destination else None
    if destination_type != "page" and not dest_id:
        typer.echo(
            format_error("missing_args", "--destination-type requires --destination."), err=True
        )
        raise SystemExit(ExitCode.BAD_ARGS)

    if dry_run:
        payload: dict[str, object] = {
            "source_page_id": pid,
            "with_content": with_content,
        }
        if dest_id:
            payload["destination"] = {f"{destination_type}_id": dest_id}
        echo_dry_run("page duplicate", payload)

    from notion_client import AsyncClient

    async with AsyncClient(auth=resolved_token) as client:
        original = await await_with_timeout(client.pages.retrieve(pid), timeout)
        props = original.get("properties") or {}
        writable_props = {
            k: v
            for k, v in props.items()
            if isinstance(v, dict) and v.get("type") not in _READ_ONLY_TYPES
        }
        if dest_id:
            parent = {f"{destination_type}_id": dest_id}
        else:
            parent = original.get("parent", {})
        create_kwargs: dict[str, object] = {
            "parent": parent,
            "properties": writable_props,
        }
        if original.get("icon") is not None:
            create_kwargs["icon"] = original["icon"]
        if original.get("cover") is not None:
            create_kwargs["cover"] = original["cover"]
        result = await await_with_timeout(client.pages.create(**create_kwargs), timeout)

        if with_content:
            from notion_cli._block_utils import (
                APPEND_BATCH_SIZE,
                SKIP_CONTENT_TYPES,
                clean_block,
                fetch_recursive,
            )

            new_page_id = result.get("id")
            if not new_page_id:
                typer.echo(
                    format_error(
                        "invalid_response",
                        "Page created but response missing 'id'; cannot copy content.",
                    ),
                    err=True,
                )
                raise SystemExit(ExitCode.ERROR)
            blocks = await fetch_recursive(client, pid, timeout, max_depth=20)
            cleaned = [
                clean_block(b, skip_types=SKIP_CONTENT_TYPES)
                for b in blocks
                if b.get("type") not in SKIP_CONTENT_TYPES
            ]
            try:
                for i in range(0, len(cleaned), APPEND_BATCH_SIZE):
                    batch = cleaned[i : i + APPEND_BATCH_SIZE]
                    await await_with_timeout(
                        client.blocks.children.append(new_page_id, children=batch), timeout
                    )
            except Exception:
                try:
                    await client.pages.update(page_id=new_page_id, archived=True)
                    msg = f"Content copy failed; created page {new_page_id} has been archived."
                except Exception:
                    msg = f"Content copy failed; created page {new_page_id} could not be archived — clean it up manually."
                typer.echo(format_error("content_copy_failed", msg), err=True)
                raise SystemExit(ExitCode.ERROR)

    typer.echo(format_json(project_fields(result, fields_set)))


@page_app.command()
@run_async
async def edit(
    page_id: Annotated[
        str,
        typer.Argument(help="Page ID or Notion URL to edit."),
    ],
    find: Annotated[
        str,
        typer.Option("--find", help="Text to search for in page content."),
    ],
    replace: Annotated[
        str,
        typer.Option("--replace", help="Replacement text."),
    ],
    dry_run: Annotated[bool, dry_run_option()] = False,
    token: Annotated[str | None, token_option()] = None,
    timeout: Annotated[float | None, timeout_option()] = None,
) -> None:
    """Find and replace text in a page's content blocks.

    Searches all text blocks (paragraphs, headings, lists, etc.) recursively
    and replaces matching text while preserving formatting and annotations.

    Examples:
        notion page edit abc123 --find "old name" --replace "new name"
        notion page edit abc123 --find "TODO" --replace "DONE" --dry-run
    """
    from notion_cli._block_utils import (
        RICH_TEXT_BLOCK_TYPES,
        fetch_recursive,
        flatten_blocks,
        replace_in_rich_text,
    )

    resolved_token = resolve_token(token=token)
    pid = extract_id(page_id)

    from notion_client import AsyncClient

    async with AsyncClient(auth=resolved_token) as client:
        blocks = await fetch_recursive(client, pid, timeout, max_depth=20)
        flat = flatten_blocks(blocks)

        modifications: list[dict[str, object]] = []
        for block in flat:
            btype = block.get("type", "")
            if btype not in RICH_TEXT_BLOCK_TYPES:
                continue
            type_data = block.get(btype)
            if not type_data or "rich_text" not in type_data:
                continue
            new_rt, changed = replace_in_rich_text(type_data["rich_text"], find, replace)
            if changed and block.get("id"):
                modifications.append({"block_id": block["id"], "type": btype, "rich_text": new_rt})

        if dry_run:
            typer.echo(
                format_json(
                    {
                        "dry_run": True,
                        "command": "page edit",
                        "blocks_would_modify": len(modifications),
                        "block_ids": [m["block_id"] for m in modifications],
                    }
                )
            )
            raise SystemExit(ExitCode.OK)

        for mod in modifications:
            await await_with_timeout(
                client.blocks.update(
                    mod["block_id"], **{mod["type"]: {"rich_text": mod["rich_text"]}}
                ),
                timeout,
            )

    typer.echo(format_json({"blocks_modified": len(modifications)}))


@page_app.command()
@run_async
async def grep(
    page_id: Annotated[
        str,
        typer.Argument(help="Page ID or Notion URL to search."),
    ],
    pattern: Annotated[
        str,
        typer.Argument(help="Text or regex pattern to search for."),
    ],
    regex: Annotated[
        bool,
        typer.Option("--regex", "-E", help="Treat pattern as a regular expression."),
    ] = False,
    ignore_case: Annotated[
        bool,
        typer.Option("--ignore-case", "-i", help="Case-insensitive matching."),
    ] = False,
    count: Annotated[
        bool,
        typer.Option("--count", "-c", help="Print only the match count."),
    ] = False,
    token: Annotated[str | None, token_option()] = None,
    timeout: Annotated[float | None, timeout_option()] = None,
) -> None:
    """Search for text within a page's content blocks.

    Scans all text blocks (paragraphs, headings, lists, etc.) recursively.
    Returns matching blocks with match positions. Supports literal and regex
    patterns.

    Examples:
        notion page grep abc123 "search term"
        notion page grep abc123 "TODO" --ignore-case
        notion page grep abc123 "\\d{4}-\\d{2}-\\d{2}" --regex
        notion page grep abc123 "error" --count
    """
    import re

    from notion_cli._block_utils import RICH_TEXT_BLOCK_TYPES, fetch_recursive, flatten_blocks

    resolved_token = resolve_token(token=token)
    pid = extract_id(page_id)

    flags = re.IGNORECASE if ignore_case else 0
    if regex:
        compiled = re.compile(pattern, flags)
    else:
        compiled = re.compile(re.escape(pattern), flags)

    from notion_client import AsyncClient

    async with AsyncClient(auth=resolved_token) as client:
        blocks = await fetch_recursive(client, pid, timeout, max_depth=20)

    flat = flatten_blocks(blocks)
    results: list[dict[str, object]] = []

    for idx, block in enumerate(flat):
        btype = block.get("type", "")
        if btype not in RICH_TEXT_BLOCK_TYPES:
            continue
        type_data = block.get(btype)
        if not type_data or "rich_text" not in type_data:
            continue
        text = "".join(
            span.get("text", {}).get("content", "")
            for span in type_data["rich_text"]
            if span.get("type") == "text"
        )
        if not text:
            continue
        matches = [
            {"start": m.start(), "end": m.end(), "text": m.group()}
            for m in compiled.finditer(text)
        ]
        if matches:
            results.append(
                {
                    "block_id": block["id"],
                    "block_type": btype,
                    "block_index": idx,
                    "text": text,
                    "matches": matches,
                }
            )

    if count:
        typer.echo(format_json({"match_count": len(results)}))
    else:
        typer.echo(format_json({"match_count": len(results), "results": results}))
