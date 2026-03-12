from typing import Annotated

import typer

from notion_cli._async import await_with_timeout, run_async
from notion_cli.auth import resolve_token
from notion_cli.options import dry_run_option, fields_option, timeout_option, token_option
from notion_cli.output import echo_dry_run, format_json, project_fields
from notion_cli.parsing import extract_id, parse_fields, resolve_rich_text

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
        str | None,
        typer.Option(
            "--body",
            "-b",
            help="Comment text as plain text.",
        ),
    ] = None,
    rich_text: Annotated[
        str | None,
        typer.Option(
            "--rich-text",
            help="Rich text as a JSON array. Mutually exclusive with --body.",
        ),
    ] = None,
    dry_run: Annotated[bool, dry_run_option()] = False,
    fields: Annotated[str | None, fields_option()] = None,
    token: Annotated[str | None, token_option()] = None,
    timeout: Annotated[float | None, timeout_option()] = None,
) -> None:
    """Add a comment to a Notion page.

    Creates a new comment at the page level. Provide text via --body
    or formatted content via --rich-text (JSON array).

    Examples:
        notion comment add abc123 --body "Looks good, ship it!"
        notion comment add abc123 --rich-text '[{"text": {"content": "bold"}, "annotations": {"bold": true}}]'
    """
    resolved_token = resolve_token(token=token)
    fields_set = parse_fields(fields)
    pid = extract_id(page_id)
    rt = resolve_rich_text(body, rich_text)

    if dry_run:
        echo_dry_run("comment add", {"parent": {"page_id": pid}, "rich_text": rt})

    from notion_client import AsyncClient

    async with AsyncClient(auth=resolved_token) as client:
        result = await await_with_timeout(
            client.comments.create(parent={"page_id": pid}, rich_text=rt),
            timeout,
        )
    typer.echo(format_json(project_fields(result, fields_set)))


@comment_app.command()
@run_async
async def reply(
    discussion_id: Annotated[
        str,
        typer.Argument(help="Discussion ID to reply to (from comment list output)."),
    ],
    body: Annotated[
        str | None,
        typer.Option(
            "--body",
            "-b",
            help="Reply text as plain text.",
        ),
    ] = None,
    rich_text: Annotated[
        str | None,
        typer.Option(
            "--rich-text",
            help="Rich text as a JSON array. Mutually exclusive with --body.",
        ),
    ] = None,
    dry_run: Annotated[bool, dry_run_option()] = False,
    fields: Annotated[str | None, fields_option()] = None,
    token: Annotated[str | None, token_option()] = None,
    timeout: Annotated[float | None, timeout_option()] = None,
) -> None:
    """Reply to an existing comment thread.

    Uses the discussion_id from a comment object to add a reply to that
    thread. Provide text via --body or formatted content via --rich-text.

    Examples:
        notion comment reply disc-abc123 --body "Agreed!"
        notion comment reply disc-abc123 --rich-text '[{"text": {"content": "done"}}]'
    """
    resolved_token = resolve_token(token=token)
    fields_set = parse_fields(fields)
    did = extract_id(discussion_id)
    rt = resolve_rich_text(body, rich_text)

    if dry_run:
        echo_dry_run("comment reply", {"discussion_id": did, "rich_text": rt})

    from notion_client import AsyncClient

    async with AsyncClient(auth=resolved_token) as client:
        result = await await_with_timeout(
            client.comments.create(discussion_id=did, rich_text=rt),
            timeout,
        )
    typer.echo(format_json(project_fields(result, fields_set)))


@comment_app.command(name="list")
@run_async
async def list_comments(
    page_id: Annotated[
        str,
        typer.Argument(help="Page ID or URL to list comments for."),
    ],
    limit: Annotated[
        int | None,
        typer.Option(
            "--limit",
            "-l",
            help="Maximum number of comments to return. Omit to return all.",
        ),
    ] = None,
    fields: Annotated[str | None, fields_option()] = None,
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
    from notion_cli._async import paginate
    from notion_cli.parsing import validate_limit

    resolved_token = resolve_token(token=token)
    fields_set = parse_fields(fields)
    pid = extract_id(page_id)
    validate_limit(limit)

    from notion_client import AsyncClient

    async with AsyncClient(auth=resolved_token) as client:
        all_results, envelope = await paginate(
            client.comments.list, {"block_id": pid}, timeout, limit=limit
        )

    typer.echo(
        format_json(
            {**envelope, "results": project_fields(all_results, fields_set), "has_more": False}
        )
    )
