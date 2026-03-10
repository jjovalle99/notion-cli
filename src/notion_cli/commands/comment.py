from typing import Annotated

import typer

from notion_cli._async import await_with_timeout, run_async
from notion_cli.auth import resolve_token
from notion_cli.options import timeout_option, token_option
from notion_cli.output import format_json
from notion_cli.parsing import extract_id

comment_app = typer.Typer(
    name="comment",
    help=(
        "Add and list comments on Notion pages.\n\n"
        "Comments can be added at the page level. Use the page ID or URL "
        "to target a specific page."
    ),
    no_args_is_help=True,
)


@comment_app.command()
@run_async
async def add(
    page_id: Annotated[
        str,
        typer.Argument(help="Page ID or URL to comment on."),
    ],
    body: Annotated[
        str,
        typer.Option(
            "--body",
            "-b",
            help="Comment text. Plain text or rich text content.",
        ),
    ],
    token: Annotated[str | None, token_option()] = None,
    timeout: Annotated[float | None, timeout_option()] = None,
) -> None:
    """Add a comment to a Notion page.

    Creates a new comment at the page level. The comment appears in the
    page's discussion thread.

    Examples:
        notion comment add abc123 --body "Looks good, ship it!"
        notion comment add abc123 -b "Please review the budget section"
    """
    resolved_token = resolve_token(token=token)
    pid = extract_id(page_id)

    from notion_client import AsyncClient

    async with AsyncClient(auth=resolved_token) as client:
        result = await await_with_timeout(client.comments.create(
            parent={"page_id": pid},
            rich_text=[{"text": {"content": body}}],
        ), timeout)
    typer.echo(format_json(result))


@comment_app.command(name="list")
@run_async
async def list_comments(
    page_id: Annotated[
        str,
        typer.Argument(help="Page ID or URL to list comments for."),
    ],
    token: Annotated[str | None, token_option()] = None,
    timeout: Annotated[float | None, timeout_option()] = None,
) -> None:
    """List all comments on a Notion page.

    Returns comments in chronological order, including the comment author,
    timestamp, and rich text body.

    Examples:
        notion comment list abc123
        notion comment list https://notion.so/My-Page-abc123
    """
    resolved_token = resolve_token(token=token)
    pid = extract_id(page_id)

    all_results: list[object] = []
    from notion_client import AsyncClient

    async with AsyncClient(auth=resolved_token) as client:
        result = await await_with_timeout(client.comments.list(block_id=pid), timeout)
        all_results.extend(result["results"])

        while result.get("has_more"):
            result = await await_with_timeout(client.comments.list(block_id=pid, start_cursor=result["next_cursor"]), timeout)
            all_results.extend(result["results"])

    result["results"] = all_results
    result["has_more"] = False
    typer.echo(format_json(result))
