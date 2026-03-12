# Contributing

## Quick start

```bash
git clone https://github.com/jjovalle99/notion-cli.git
cd notion-cli
uv sync
uv run pre-commit install      # install hooks
uv run pytest                  # run tests
uv run ruff check src/ tests/  # lint
uv run ty check src/           # type check
```

## Adding a new command

Every command follows the same pattern. Here is the minimal template:

```python
# src/notion_cli/commands/yourmodule.py
from typing import Annotated
import typer

from notion_cli._async import await_with_timeout, run_async
from notion_cli.auth import resolve_token
from notion_cli.options import fields_option, timeout_option, token_option
from notion_cli.output import format_json, project_fields
from notion_cli.parsing import extract_id, parse_fields

your_app = typer.Typer(
    name="yourgroup",
    help="Description of your command group.",
    no_args_is_help=True,
)

@your_app.command()
@run_async
async def your_command(
    some_id: Annotated[str, typer.Argument(help="...")],
    fields: Annotated[str | None, fields_option()] = None,
    token: Annotated[str | None, token_option()] = None,
    timeout: Annotated[float | None, timeout_option()] = None,
) -> None:
    """One-line description.

    Longer explanation of what the command does.

    Examples:
        notion yourgroup yourcommand abc123
    """
    resolved_token = resolve_token(token=token)
    fields_set = parse_fields(fields)
    sid = extract_id(some_id)

    from notion_client import AsyncClient

    async with AsyncClient(auth=resolved_token) as client:
        result = await await_with_timeout(client.some.method(sid), timeout)
    typer.echo(format_json(project_fields(result, fields_set)))
```

Key conventions to follow:

### @run_async decorator

Every command function must be `async def` decorated with `@run_async`. This bridges Typer (sync) with the async Notion client. The decorator also handles all error formatting (API errors, timeouts, unexpected exceptions) so commands don't need try/except.

**Exception:** `commands/auth.py` uses plain `def` (no `@run_async`) because the OAuth flow is synchronous — it opens a browser and waits for a local HTTP callback. If your command makes no async API calls, plain `def` is fine.

### Lazy imports inside function bodies

`from notion_client import AsyncClient` goes inside the function body, not at the top of the file. This keeps CLI startup fast. When the user runs `notion --version` or `notion --help`, the Notion SDK and its HTTP dependencies are not loaded.

### await_with_timeout

Every API call must use `await_with_timeout(coroutine, timeout)` from `_async.py`. This respects the user's `--timeout` flag. Do not call `await client.method()` directly.

### Pagination

If the API endpoint is paginated (returns `has_more` and `next_cursor`), use the `paginate()` helper from `_async.py`:

```python
from notion_cli._async import paginate

async with AsyncClient(auth=resolved_token) as client:
    all_results, envelope = await paginate(client.some.list, kwargs, timeout, limit=limit)

echo_list(project_fields(all_results, fields_set), envelope, output_format)
```

`paginate()` handles `page_size` clamping, cursor tracking, `has_more`/`next_cursor`/`results` guards, and post-trim to the limit. If the API method requires positional arguments, use `functools.partial`:

```python
from functools import partial
all_results, envelope = await paginate(partial(client.data_sources.query, did), kwargs, timeout, limit=limit)
```

Do not hand-roll pagination loops — all paginated commands use this helper.

### Shared helpers

These utilities in `parsing.py` and `_block_utils.py` should be reused, not reimplemented:

| Helper | Module | Purpose |
|--------|--------|---------|
| `parse_fields(fields)` | `parsing.py` | Parse `--fields` comma string into `set[str] \| None` |
| `validate_limit(limit)` | `parsing.py` | Reject `--limit` values < 1 |
| `parse_json(value, expected_type, label)` | `parsing.py` | Parse and type-validate JSON options (`--filter`, `--properties`, etc.) |
| `resolve_rich_text(body, rich_text_json)` | `parsing.py` | Resolve `--body` / `--rich-text` mutual exclusion for comments |
| `project_fields(data, fields_set)` | `output.py` | Apply `--fields` projection to output data |
| `read_content(value)` | `parsing.py` | Read from string, `@file` path, or `-` for stdin |
| `paginate(method, kwargs, timeout, limit)` | `_async.py` | Paginate any Notion list endpoint |
| `paginate_stream(method, kwargs, timeout, limit)` | `_async.py` | Paginate yielding each page (for `--stream` NDJSON) |
| `fetch_children(client, block_id, timeout, limit)` | `_block_utils.py` | Fetch child blocks with optional limit |
| `fetch_recursive(client, block_id, timeout, max_depth)` | `_block_utils.py` | Recursively fetch nested blocks (semaphore-bounded concurrency) |
| `clean_block(block, skip_types)` | `_block_utils.py` | Strip server fields for block re-creation; filters `skip_types` recursively |
| `flatten_blocks(blocks)` | `_block_utils.py` | Flatten recursive block tree into a flat list |
| `replace_in_rich_text(rich_text, find, replace)` | `_block_utils.py` | Find/replace text in rich_text spans, preserving annotations |
| `RICH_TEXT_BLOCK_TYPES` | `_block_utils.py` | Block types that have editable `rich_text` fields |
| `SKIP_CONTENT_TYPES` | `_block_utils.py` | Block types to skip during content copy (`child_page`, `child_database`, `synced_block`, `unsupported`) |
| `parse_where(expr, prop_type)` | `parsing.py` | Parse `--where` expression into Notion filter object |
| `process_batch(lines, handler, fields)` | `_batch.py` | Process NDJSON stdin through an async handler with error handling |

### Registering the command

If your command belongs to an existing group (page, db, block, etc.), add it to the existing Typer sub-app in that file.

If it's a new group, create a new file and add an entry to the `_LAZY_GROUPS` dict in `cli.py`:

```python
_LAZY_GROUPS: dict[str, tuple[str, str]] = {
    "page": ("notion_cli.commands.page", "page_app"),
    # ...
    "yourgroup": ("notion_cli.commands.yourmodule", "your_app"),
}
```

For a standalone command (not a group), add it to `_LAZY_COMMANDS` instead:

```python
_LAZY_COMMANDS: dict[str, tuple[str, str]] = {
    "search": ("notion_cli.commands.search", "search"),
    "yourcommand": ("notion_cli.commands.yourmodule", "your_command"),
}
```

Commands are lazy-loaded — `cli.py` never imports your module at the top level. The module is only imported when a user actually invokes that command. This keeps `notion --help` and `notion --version` fast regardless of how many commands exist.

### Help text

Write help text that a coding agent can use without any other documentation:
- Argument/option `help=` strings should explain accepted formats and give a concrete example
- The command docstring should explain what it does, what it returns, and show usage examples
- Be specific ("Page ID or Notion URL") not vague ("identifier")

## Architecture notes

### Lazy command loading

`cli.py` uses a `_LazyTyperGroup` subclass that overrides Click's `get_command()`. Command modules are not imported at startup — only when the user invokes that specific command. To add a new command, you only need to add an entry to `_LAZY_GROUPS` or `_LAZY_COMMANDS`; no top-level imports required.

### One `AsyncClient` per command invocation

Each command creates its own `AsyncClient` inside an `async with` block. This is intentional. The CLI runs one command per process and exits — there is no benefit to sharing a client across commands. Within a single command, the `async with` block reuses the underlying HTTP connection pool for all API calls, including paginated loops.

### Blocking I/O in parsing

`read_content()` in `parsing.py` performs synchronous blocking I/O (`sys.stdin.read`, `Path.read_text`) inside async command bodies. This is fine for the current CLI use case (single command, no concurrent I/O). If the codebase is ever adapted for concurrent or server use, these calls should be wrapped with `asyncio.to_thread()`.

## Testing

Tests use `pytest` with shared fixtures from `conftest.py`:

- `runner` provides a `typer.testing.CliRunner`
- `mock_client` provides an `AsyncMock` that patches `notion_client.AsyncClient`. This works because commands import `AsyncClient` inside the function body (lazy import). If you move the import to module level, the mock won't intercept it.

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
- `ruff` for linting, `ty` for type checking (both configured in pyproject.toml)
- No classes unless truly needed, prefer functions
- No docstrings on modules, only on public functions that need explanation

## Pre-commit and CI

Pre-commit hooks run `ruff check --fix` and `ruff format` automatically on commit. Install with:

```bash
uv run pre-commit install
```

`ty` has no official pre-commit hook yet (tracked at [astral-sh/ty#269](https://github.com/astral-sh/ty/issues/269)). Run it manually before committing:

```bash
uv run ty check src/
```

CI enforces all three checks (ruff, ty, pytest). If pre-commit is skipped locally, CI catches it.
