# notionctl

[![CI](https://github.com/jjovalle99/notion-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/jjovalle99/notion-cli/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/jjovalle99/notion-cli/branch/main/graph/badge.svg)](https://codecov.io/gh/jjovalle99/notion-cli)
[![PyPI version](https://img.shields.io/pypi/v/notionctl)](https://pypi.org/project/notionctl/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)

Notion CLI built for coding agents. Compact JSON to stdout, structured errors to stderr, meaningful exit codes. Works with Claude Code, Cursor, Aider — or standalone.

```bash
# Agent reads a spec from Notion, implements it, writes results back
SPEC=$(notion block get "$PAGE_ID" --markdown)
# ... agent does work ...
notion page create -p "$PAGE_ID" -t "Implementation Notes" -c @results.md
notion page update "$ROW_ID" --properties '{"Status":{"select":{"name":"Done"}}}'
```

## Install

```bash
# Run without installing
uvx --from notionctl notion search "my page"

# Or install permanently
uv tool install notionctl
pip install notionctl
```

## Authentication

**OAuth (recommended)**

```bash
notion auth login     # opens browser, stores token locally
notion auth status    # check current auth
notion auth logout    # revoke and delete token
```

When prompted, select all pages for full workspace access. Credentials are stored in `~/.config/notion-cli/` and persist across `uvx` runs.

**API token** (for CI or headless environments)

Get a token from https://www.notion.so/my-integrations:

```bash
export NOTION_API_KEY="secret_..."
```

Or pass per command with `--token`.

## Commands

```
notion search <query>              Search pages and databases by title
notion page get <id>               Get page metadata (properties, parent, URL)
notion page create                 Create a page with markdown content
notion page update <id>            Update title, properties, icon, archive status
notion page move <id>              Move a page to a different parent
notion page duplicate <id>         Duplicate a page
notion db get <id>                 Get database schema
notion db query <id>               Query database rows with filter and sort
notion db create                   Create a database
notion db update <id>              Update database title or schema
notion block get <id>              Get page content as blocks or markdown
notion block append <id>           Append block objects (JSON) to a page
notion comment add <id>            Add a comment to a page
notion comment list <id>           List comments on a page
notion user list                   List workspace users
notion user get <id>               Get a specific user
notion user me                     Get the current bot user
notion team list                   List teamspaces
notion auth login/logout/status    OAuth authentication
```

All IDs accept Notion URLs or raw UUIDs.

## Examples

```bash
# Search
notion search "meeting notes"
notion search "roadmap" --type page --limit 5

# Read page content as markdown
notion block get <page-id> --markdown

# Create a page with markdown (inline, from file, or stdin)
notion page create -p <parent-id> -t "New Page" -c $'# Hello\nWorld'
notion page create -p <parent-id> -t "Notes" -c @notes.md
cat notes.md | notion page create -p <parent-id> -t "Notes" -c -

# Query a database
notion db query <db-id> --filter '{"property":"Status","select":{"equals":"Done"}}'

# Update a row
notion page update <row-id> --properties '{"Status":{"select":{"name":"Done"}}}'
```

## Output

Compact JSON to stdout. Errors to stderr:
```json
{"error_type":"not_found","message":"...","suggestion":"..."}
```

Exit codes: `0` ok · `1` error · `2` bad args · `3` not found · `4` permission denied · `5` rate limited

## Global options

- `--token` — Notion API token (defaults to `NOTION_API_KEY` env var)
- `--timeout` — Timeout per API request in seconds (paginated commands make multiple requests)
- `--help` — Show help for any command

## Development

```bash
git clone https://github.com/jjovalle99/notion-cli.git
cd notion-cli
uv sync
uv run pytest
uv run ruff check src/ tests/
uv run ty check src/
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for architecture, conventions, and how to add commands.
