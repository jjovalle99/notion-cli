from typing import Annotated

import typer

from notion_cli._async import await_with_timeout, run_async
from notion_cli.auth import resolve_token
from notion_cli.options import timeout_option, token_option
from notion_cli.output import format_json
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
    token: Annotated[str | None, token_option()] = None,
    timeout: Annotated[float | None, timeout_option()] = None,
) -> None:
    """List child blocks of a page or block.

    Returns raw JSON blocks by default. Use --markdown to convert the output
    to readable Markdown text. If a child block has has_children=true, call
    this command again with that block's ID to recurse deeper.

    Examples:
        notion block get abc123
        notion block get abc123 --markdown
        notion block get https://notion.so/My-Page-abc123 -m
    """
    resolved_token = resolve_token(token=token)
    bid = extract_id(block_id)
    all_results: list[dict[str, object]] = []
    from notion_client import AsyncClient

    async with AsyncClient(auth=resolved_token) as client:
        result = await await_with_timeout(client.blocks.children.list(bid), timeout)
        all_results.extend(result["results"])

        while result.get("has_more") and result.get("next_cursor") and result.get("results"):
            result = await await_with_timeout(
                client.blocks.children.list(bid, start_cursor=result["next_cursor"]), timeout
            )
            all_results.extend(result["results"])

    if markdown:
        from notion_cli.markdown import blocks_to_markdown

        typer.echo(blocks_to_markdown(all_results), nl=False)
    else:
        result["results"] = all_results
        result["has_more"] = False
        typer.echo(format_json(result))


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
    import json as json_mod

    resolved_token = resolve_token(token=token)
    pid = extract_id(parent_id)
    raw = read_content(children)
    block_list = json_mod.loads(raw)

    from notion_client import AsyncClient

    async with AsyncClient(auth=resolved_token) as client:
        result = await await_with_timeout(
            client.blocks.children.append(pid, children=block_list), timeout
        )
    typer.echo(format_json(result))
