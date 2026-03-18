# notionctl

[![CI](https://github.com/jjovalle99/notion-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/jjovalle99/notion-cli/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/jjovalle99/notion-cli/branch/main/graph/badge.svg)](https://codecov.io/gh/jjovalle99/notion-cli)
[![PyPI version](https://img.shields.io/pypi/v/notionctl)](https://pypi.org/project/notionctl/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)

Notion CLI built for coding agents. Compact JSON to stdout, structured errors to stderr, meaningful exit codes. Works with Claude Code, Codex, Mistral Vibe or standalone.

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
uvx notionctl search "my page"

# Or install permanently
uv tool install notionctl   # installs both `notionctl` and `notion` commands
pipx install notionctl
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
notion page get <id>               Get page metadata (--full for blocks + comments)
notion page create                 Create a page with markdown content (--stdin for batch)
notion page update <id>            Update title, properties, icon, archive/unarchive
notion page move <id>              Move a page to a different parent (--stdin for batch)
notion page duplicate <id>         Duplicate a page (with optional content copy)
notion page edit <id>              Find and replace text across page content
notion page grep <id> <pattern>    Search page content with literal or regex patterns
notion db get <id>                 Get database schema
notion db query <id>               Query database rows (--where for human-friendly filters)
notion db create                   Create a database
notion db update <id>              Update database title or schema
notion block get <id>              Get page content as blocks or markdown
notion block append <id>           Append block objects (JSON) to a page
notion block update <id>           Update a block's content or properties
notion block delete <id>           Delete (archive) a block
notion api <METHOD> <path>         Raw API passthrough to any Notion endpoint
notion comment add <id>            Add a comment to a page (plain text or rich text)
notion comment reply <disc-id>     Reply to a comment thread
notion comment list <id>           List comments on a page
notion user list                   List workspace users
notion user get <id>               Get a specific user
notion user me                     Get the current bot user
notion team list                   List teamspaces
notion schema <command>            Introspect CLI command schemas (for agents)
notion auth login/logout/status    OAuth authentication
```

All IDs accept Notion URLs or raw UUIDs.

## Examples

```bash
# Search
notion search "meeting notes"
notion search "roadmap" --type page --limit 5

# Read page content as markdown (with recursive nested blocks)
notion block get <page-id> --markdown
notion block get <page-id> --recursive --markdown
notion block get <page-id> --recursive --depth 2 --markdown

# Create a page with markdown (inline, from file, or stdin)
notion page create -p <parent-id> -t "New Page" -c $'# Hello\nWorld'
notion page create -p <parent-id> -t "Notes" -c @notes.md
notion page create -p <db-id> -t "Row" --parent-type database --icon "📝"

# Duplicate a page (with content and to a different parent)
notion page duplicate <page-id> --with-content
notion page duplicate <page-id> --destination <parent-id>
notion page duplicate <page-id> --destination <db-id> --destination-type database

# Find and replace across page content
notion page edit <page-id> --find "old name" --replace "new name"
notion page edit <page-id> --find "TODO" --replace "DONE" --dry-run

# Search page content (literal or regex)
notion page grep <page-id> "search term"
notion page grep <page-id> "\d{4}-\d{2}-\d{2}" --regex

# Get page with all content and comments in one call
notion page get <page-id> --full

# Query a database (human-friendly or raw JSON filter)
notion db query <db-id> --where "Status = Done"
notion db query <db-id> --where "Status = Done" --where "Priority > 3"
notion db query <db-id> --filter '{"property":"Status","select":{"equals":"Done"}}'

# Update a row
notion page update <row-id> --properties '{"Status":{"select":{"name":"Done"}}}'

# Block CRUD
notion block update <block-id> --body '{"paragraph":{"rich_text":[{"text":{"content":"new"}}]}}'
notion block delete <block-id>

# Raw API passthrough
notion api GET pages/<page-id>
notion api POST pages --body @payload.json

# Batch operations via NDJSON stdin
echo '{"parent":"abc","title":"A"}' | notion page create --stdin
cat moves.ndjson | notion page move --stdin

# Comments (plain text or rich text JSON)
notion comment add <page-id> --body "Looks good!"
notion comment reply <discussion-id> --rich-text '[{"text":{"content":"bold"},"annotations":{"bold":true}}]'

# Project output to specific fields
notion page get <page-id> --fields id,url,properties
notion db query <db-id> --fields id,properties --limit 10
```

## Output

Compact JSON to stdout. Errors to stderr:
```json
{"error_type":"not_found","message":"...","suggestion":"..."}
```

Exit codes: `0` ok · `1` error · `2` bad args · `3` not found · `4` permission denied · `5` rate limited

## Global options

- `--fields`, `-f` — Comma-separated list of fields to include in output (e.g. `--fields id,url`)
- `--dry-run` — Show what would be sent to the API without making changes (mutating commands)
- `--output-format json|ndjson` — Output format for list commands
- `--token` — Notion API token (defaults to `NOTION_API_KEY` env var)
- `--timeout` — Timeout per API request in seconds
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
