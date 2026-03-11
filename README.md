# notion-cli

[![CI](https://github.com/jjovalle99/notion-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/jjovalle99/notion-cli/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/jjovalle99/notion-cli/branch/main/graph/badge.svg)](https://codecov.io/gh/jjovalle99/notion-cli)
[![PyPI version](https://img.shields.io/pypi/v/notion-cli)](https://pypi.org/project/notion-cli/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)

Agent-friendly CLI for the Notion API. Outputs compact JSON to stdout, structured errors to stderr. Designed for coding agents (Claude Code, Cursor, Aider) but works for humans too.

## Install

```bash
uv tool install notion-cli
# or
pip install notion-cli
```

## Authentication

### Option 1: OAuth (recommended)

```bash
notion auth login     # opens browser, stores token locally
notion auth status    # check current auth
notion auth logout    # revoke and delete token
```

When prompted, select all pages for full workspace access.

### Option 2: API token

Get a token from https://www.notion.so/my-integrations:

```bash
export NOTION_API_KEY="secret_..."
```

Or pass it per command with `--token`.

## Commands

```
notion auth login                  Authenticate via OAuth browser flow
notion auth logout                 Revoke token and delete credentials
notion auth status                 Show current authentication method
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
notion block get <id>              Get page content blocks (use --markdown for text)
notion block append <id>           Append block objects (JSON) to a page
notion comment add <id>            Add a comment to a page
notion comment list <id>           List comments on a page
notion user list                   List workspace users
notion user get <id>               Get a specific user
notion user me                     Get the current bot user
notion team list                   List teamspaces
```

All IDs accept Notion URLs or raw UUIDs.

## Examples

Search for pages:
```bash
notion search "meeting notes"
notion search "roadmap" --type page
```

Read page content as markdown:
```bash
notion block get <page-id> --markdown
```

Create a page with markdown content:
```bash
notion page create --parent <parent-id> --title "New Page" --content $'# Hello\nWorld'
notion page create -p <parent-id> -t "Notes" -c @notes.md
notion page create -p <parent-id> -t "Notes" -c -    # read from stdin
```

Query a database with a filter:
```bash
notion db query <db-id> --filter '{"property": "Status", "select": {"equals": "Done"}}'
```

Update a database row property:
```bash
notion page update <page-id> --properties '{"Status": {"select": {"name": "Done"}}}'
```

## Output format

Every command outputs compact JSON to stdout. Errors go to stderr as:
```json
{"error_type": "not_found", "message": "...", "suggestion": "..."}
```

Exit codes: 0=ok, 1=error, 2=bad args, 3=not found, 4=permission denied, 5=rate limited.

## Options available on all commands

- `--token TEXT` Notion API token (defaults to `NOTION_API_KEY` env var)
- `--timeout FLOAT` Timeout per API request in seconds (paginated commands make multiple requests)
- `--help` Show help for any command

## Development

```bash
git clone https://github.com/jjovalle99/notion-cli.git
cd notion-cli
uv sync
uv run pytest
uv run ruff check src/ tests/
uv run ty check src/
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for details on adding features.
