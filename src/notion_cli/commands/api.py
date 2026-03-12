from typing import Annotated

import typer

from notion_cli._async import await_with_timeout, run_async
from notion_cli.auth import resolve_token
from notion_cli.options import dry_run_option, fields_option, timeout_option, token_option
from notion_cli.output import ExitCode, echo_dry_run, format_error, format_json, project_fields

_VALID_METHODS = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE"})


@run_async
async def api(
    method: Annotated[
        str,
        typer.Argument(help="HTTP method: GET, POST, PUT, PATCH, or DELETE."),
    ],
    path: Annotated[
        str,
        typer.Argument(help="API path, e.g. /pages/abc123 or /databases."),
    ],
    body: Annotated[
        str | None,
        typer.Option(
            "--body",
            "-b",
            help=(
                "Request body as JSON. "
                "Use '@path/to/file.json' to read from a file, or '-' for stdin."
            ),
        ),
    ] = None,
    dry_run: Annotated[bool, dry_run_option()] = False,
    fields: Annotated[str | None, fields_option()] = None,
    token: Annotated[str | None, token_option()] = None,
    timeout: Annotated[float | None, timeout_option()] = None,
) -> None:
    """Send a raw request to the Notion API.

    Bypasses the typed commands and talks directly to any Notion API endpoint.
    The base URL (https://api.notion.com/v1) and auth header are added automatically.

    Examples:
        notion api GET /pages/abc123
        notion api POST /pages --body '{"parent": {"page_id": "x"}, "properties": {}}'
        notion api PATCH /blocks/abc123 -b @update.json
        notion api DELETE /blocks/abc123
    """
    from notion_cli.parsing import parse_fields

    upper_method = method.upper()
    if upper_method not in _VALID_METHODS:
        typer.echo(
            format_error(
                "invalid_args",
                f"Invalid HTTP method: {method!r}. Must be one of: {', '.join(sorted(_VALID_METHODS))}.",
            ),
            err=True,
        )
        raise SystemExit(ExitCode.BAD_ARGS)

    resolved_token = resolve_token(token=token)
    fields_set = parse_fields(fields)
    clean_path = path.lstrip("/")

    parsed_body: dict[str, object] | None = None
    if body is not None:
        from notion_cli.parsing import parse_json, read_content

        raw = read_content(body)
        parsed_body = parse_json(raw, expected_type=dict, label="--body")  # ty: ignore[invalid-assignment]

    if dry_run:
        payload: dict[str, object] = {"method": upper_method, "path": path}
        if parsed_body is not None:
            payload["body"] = parsed_body
        echo_dry_run("api", payload)

    from notion_client import AsyncClient

    async with AsyncClient(auth=resolved_token) as client:
        if parsed_body is not None:
            result = await await_with_timeout(
                client.request(path=clean_path, method=upper_method, body=parsed_body), timeout
            )
        else:
            result = await await_with_timeout(
                client.request(path=clean_path, method=upper_method), timeout
            )
    typer.echo(format_json(project_fields(result, fields_set)))
