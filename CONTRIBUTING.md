# Contributing

## Quick start

```bash
git clone https://github.com/youruser/notion-cli.git
cd notion-cli
uv sync
uv run pytest           # run tests
uv run ruff check src/  # lint
```

## Adding a new command

Every command follows the same pattern. Here is the minimal template:

```python
# src/notion_cli/commands/yourmodule.py
from typing import Annotated
import typer

from notion_cli._async import await_with_timeout, run_async
from notion_cli.auth import resolve_token
from notion_cli.options import timeout_option, token_option
from notion_cli.output import format_json
from notion_cli.parsing import extract_id

@your_app.command()
@run_async
async def your_command(
    some_id: Annotated[str, typer.Argument(help="...")],
    token: Annotated[str | None, token_option()] = None,
    timeout: Annotated[float | None, timeout_option()] = None,
) -> None:
    """One-line description.

    Longer explanation of what the command does.

    Examples:
        notion yourgroup yourcommand abc123
    """
    resolved_token = resolve_token(token=token)
    sid = extract_id(some_id)

    from notion_client import AsyncClient

    async with AsyncClient(auth=resolved_token) as client:
        result = await await_with_timeout(client.some.method(sid), timeout)
    typer.echo(format_json(result))
```

Key conventions to follow:

### @run_async decorator

Every command function must be `async def` decorated with `@run_async`. This bridges Typer (sync) with the async Notion client. The decorator also handles all error formatting (API errors, timeouts, unexpected exceptions) so commands don't need try/except.

### Lazy imports inside function bodies

`from notion_client import AsyncClient` goes inside the function body, not at the top of the file. This keeps CLI startup fast. When the user runs `notion --version` or `notion --help`, the Notion SDK and its HTTP dependencies are not loaded.

### await_with_timeout

Every API call must use `await_with_timeout(coroutine, timeout)` from `_async.py`. This respects the user's `--timeout` flag. Do not call `await client.method()` directly.

### Pagination

If the API endpoint is paginated (returns `has_more` and `next_cursor`), collect all pages:

```python
all_results: list[dict[str, object]] = []
async with AsyncClient(auth=resolved_token) as client:
    result = await await_with_timeout(client.some.list(...), timeout)
    all_results.extend(result["results"])

    while result.get("has_more") and result.get("next_cursor") and result.get("results"):
        result = await await_with_timeout(
            client.some.list(..., start_cursor=result["next_cursor"]), timeout
        )
        all_results.extend(result["results"])

result["results"] = all_results
result["has_more"] = False
```

The three guards (`has_more`, `next_cursor`, `results`) prevent infinite loops on malformed API responses.

### Registering the command

If your command belongs to an existing group (page, db, block, etc.), add it to the existing Typer sub-app in that file. If it's a new group, create a new file and register it in `cli.py`:

```python
from notion_cli.commands.yourmodule import your_app  # noqa: E402
app.add_typer(your_app)
```

### Help text

Write help text that a coding agent can use without any other documentation:
- Argument/option `help=` strings should explain accepted formats and give a concrete example
- The command docstring should explain what it does, what it returns, and show usage examples
- Be specific ("Page ID or Notion URL") not vague ("identifier")

## Testing

Tests use `pytest` with shared fixtures from `conftest.py`:

- `runner` provides a `typer.testing.CliRunner`
- `mock_client` provides an `AsyncMock` that patches `notion_client.AsyncClient`

```python
def test_your_command(runner: CliRunner, mock_client: AsyncMock) -> None:
    mock_client.some.method.return_value = {"id": "abc"}

    result = runner.invoke(app, ["group", "cmd", "abc"], env={"NOTION_API_KEY": "s"})

    assert result.exit_code == 0
```

Follow TDD: write the failing test first, then implement the minimum code to make it pass.

## Code style

- Python 3.12+, async-first
- `uv` for dependency management
- `ruff` for linting (configured in pyproject.toml)
- No classes unless truly needed, prefer functions
- No docstrings on modules, only on public functions that need explanation
