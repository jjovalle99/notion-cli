from typing import Annotated

import typer
from notion_client import AsyncClient

from notion_cli._async import run_async
from notion_cli.auth import resolve_token
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


def _token_option() -> typer.Option:
    return typer.Option(
        "--token",
        envvar="NOTION_API_KEY",
        help="Notion API token. Defaults to NOTION_API_KEY env var.",
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
    token: Annotated[str | None, _token_option()] = None,
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

    async with AsyncClient(auth=resolved_token) as client:
        result = await client.comments.create(
            parent={"page_id": pid},
            rich_text=[{"text": {"content": body}}],
        )
    typer.echo(format_json(result))


@comment_app.command(name="list")
@run_async
async def list_comments(
    page_id: Annotated[
        str,
        typer.Argument(help="Page ID or URL to list comments for."),
    ],
    token: Annotated[str | None, _token_option()] = None,
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

    async with AsyncClient(auth=resolved_token) as client:
        result = await client.comments.list(block_id=pid)
    typer.echo(format_json(result))
