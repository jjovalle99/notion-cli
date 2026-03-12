from typing import Annotated, Any

import typer

from notion_cli._async import await_with_timeout, run_async
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
)
from notion_cli.parsing import extract_id, read_content

block_app = typer.Typer(
    name="block",
    help=(
        "Read and append content blocks within Notion pages.\n\n"
        "Blocks are the content elements inside a page: paragraphs, headings, "
        "lists, code blocks, images, etc. Use 'notion page get' for page metadata "
        "and 'notion block get' for page content."
    ),
    no_args_is_help=True,
)


@block_app.command()
@run_async
async def get(
    block_id: Annotated[
        str,
        typer.Argument(
            help=(
                "Block or page ID/URL whose children to retrieve. "
                "Pass a page ID to get the top-level content blocks of that page."
            ),
        ),
    ],
    markdown: Annotated[
        bool,
        typer.Option(
            "--markdown",
            "-m",
            help="Output content as Markdown instead of raw JSON blocks.",
        ),
    ] = False,
    limit: Annotated[
        int | None,
        typer.Option(
            "--limit",
            "-l",
            help="Maximum number of blocks to return. Omit to return all.",
        ),
    ] = None,
    recursive: Annotated[
        bool,
        typer.Option(
            "--recursive",
            "-r",
            help="Recursively fetch nested blocks (toggles, sub-lists, etc.).",
        ),
    ] = False,
    depth: Annotated[
        int,
        typer.Option(
            "--depth",
            help="Maximum nesting depth when using --recursive. 1 = top level only.",
        ),
    ] = 5,
    fields: Annotated[str | None, fields_option()] = None,
    output_format: Annotated[str, output_format_option()] = "json",
    token: Annotated[str | None, token_option()] = None,
    timeout: Annotated[float | None, timeout_option()] = None,
) -> None:
    """List child blocks of a page or block.

    Returns raw JSON blocks by default. Use --markdown to convert the output
    to readable Markdown text. Use --recursive to include nested content
    (controlled by --depth, default 5). Note: --recursive and --limit cannot
    be combined.

    Examples:
        notion block get abc123
        notion block get abc123 --markdown
        notion block get abc123 --recursive --markdown
        notion block get abc123 --recursive --depth 2 --markdown
        notion block get https://notion.so/My-Page-abc123 -r -m
    """
    from notion_cli.parsing import parse_fields, validate_limit

    resolved_token = resolve_token(token=token)
    fields_set = parse_fields(fields)
    bid = extract_id(block_id)
    validate_limit(limit)
    if recursive and limit is not None:
        typer.echo(
            format_error(
                "conflicting_args",
                "--recursive and --limit cannot be combined. Recursive fetch traverses the full tree.",
            ),
            err=True,
        )
        raise SystemExit(ExitCode.BAD_ARGS)

    from notion_client import AsyncClient

    all_results: list[dict[str, Any]] = []
    envelope: dict[str, object] = {}

    async with AsyncClient(auth=resolved_token) as client:
        if recursive:
            from notion_cli._block_utils import fetch_recursive

            all_results = await fetch_recursive(client, bid, timeout, max_depth=depth)
            envelope = {"object": "list", "type": "block"}
        else:
            from notion_cli._block_utils import fetch_children

            all_results, envelope = await fetch_children(client, bid, timeout, limit=limit)

    if limit is not None:
        all_results = all_results[:limit]

    if markdown:
        from notion_cli.markdown import blocks_to_markdown

        typer.echo(blocks_to_markdown(all_results), nl=False)
    else:
        echo_list(project_fields(all_results, fields_set), envelope, output_format)


@block_app.command()
@run_async
async def append(
    parent_id: Annotated[
        str,
        typer.Argument(
            help="Page or block ID/URL to append content to.",
        ),
    ],
    children: Annotated[
        str,
        typer.Option(
            "--children",
            "-c",
            help=(
                "Block objects as a JSON array to append. "
                "Use '@path/to/file.json' to read from a file, or '-' for stdin. "
                'Example: \'[{"type": "paragraph", "paragraph": '
                '{"rich_text": [{"text": {"content": "Hello"}}]}}]\''
            ),
        ),
    ],
    dry_run: Annotated[bool, dry_run_option()] = False,
    fields: Annotated[str | None, fields_option()] = None,
    token: Annotated[str | None, token_option()] = None,
    timeout: Annotated[float | None, timeout_option()] = None,
) -> None:
    """Append content blocks to a page or block.

    Content is provided as a JSON array of Notion block objects. The new
    blocks are added after existing children.

    Examples:
        notion block append abc123 --children '[{"type": "paragraph", "paragraph": {"rich_text": [{"text": {"content": "Hello"}}]}}]'
        notion block append abc123 -c @blocks.json
    """
    from notion_cli.parsing import parse_fields, parse_json

    resolved_token = resolve_token(token=token)
    fields_set = parse_fields(fields)
    pid = extract_id(parent_id)
    raw = read_content(children)
    block_list = parse_json(raw, expected_type=list, label="--children")
    if not block_list:
        typer.echo(format_error("empty_input", "--children must be a non-empty list."), err=True)
        raise SystemExit(ExitCode.BAD_ARGS)

    if dry_run:
        echo_dry_run("block append", {"parent_id": pid, "children": block_list})

    from notion_client import AsyncClient

    from notion_cli._block_utils import APPEND_BATCH_SIZE

    async with AsyncClient(auth=resolved_token) as client:
        result: dict[str, object] = {}
        appended = 0
        try:
            for i in range(0, len(block_list), APPEND_BATCH_SIZE):
                batch = block_list[i : i + APPEND_BATCH_SIZE]
                result = await await_with_timeout(
                    client.blocks.children.append(pid, children=batch), timeout
                )
                appended += len(batch)
        except Exception as append_exc:
            from notion_client.errors import NotionClientErrorBase

            is_network_or_api = isinstance(
                append_exc, (NotionClientErrorBase, TimeoutError, OSError)
            )
            if appended > 0 and is_network_or_api:
                typer.echo(
                    format_error(
                        "partial_append",
                        f"Appended {appended}/{len(block_list)} blocks before failure.",
                    ),
                    err=True,
                )
                raise SystemExit(ExitCode.ERROR)
            raise
    typer.echo(format_json(project_fields(result, fields_set)))
