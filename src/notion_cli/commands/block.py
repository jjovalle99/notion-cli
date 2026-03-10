from typing import Annotated

import typer

from notion_cli._async import run_async
from notion_cli.auth import resolve_token
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


def _token_option() -> typer.Option:
    return typer.Option(
        "--token",
        envvar="NOTION_API_KEY",
        help="Notion API token. Defaults to NOTION_API_KEY env var.",
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
    token: Annotated[str | None, _token_option()] = None,
) -> None:
    """List child blocks of a page or block.

    Returns the first level of children. If a child block has
    has_children=true, call this command again with that block's ID
    to recurse deeper.

    Examples:
        notion block get aabbccdd11223344556677889900aabb
        notion block get https://notion.so/My-Page-abc123
    """
    resolved_token = resolve_token(token=token)
    bid = extract_id(block_id)
    all_results: list[object] = []
    from notion_client import AsyncClient

    async with AsyncClient(auth=resolved_token) as client:
        result = await client.blocks.children.list(bid)
        all_results.extend(result["results"])

        while result.get("has_more"):
            result = await client.blocks.children.list(bid, start_cursor=result["next_cursor"])
            all_results.extend(result["results"])

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
    content: Annotated[
        str,
        typer.Option(
            "--content",
            "-c",
            help=(
                "Content as Notion-flavored Markdown to append. "
                "Use '@path/to/file.md' to read from a file, or '-' for stdin."
            ),
        ),
    ],
    token: Annotated[str | None, _token_option()] = None,
) -> None:
    """Append content blocks to a page or block.

    Content is provided as Notion-flavored Markdown. The new blocks are
    added after existing children.

    Examples:
        notion block append abc123 --content "# New section\\nSome text"
        notion block append abc123 -c @appendix.md
        echo "- item 1\\n- item 2" | notion block append abc123 -c -
    """
    resolved_token = resolve_token(token=token)
    pid = extract_id(parent_id)
    md = read_content(content)

    from notion_client import AsyncClient

    async with AsyncClient(auth=resolved_token) as client:
        result = await client.blocks.children.append(pid, markdown=md)
    typer.echo(format_json(result))
