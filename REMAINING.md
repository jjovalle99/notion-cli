# Remaining Issues

Last updated after two rounds of 6-agent adversarial audits and fixing all actionable findings.

## Fixed Bugs

| # | Bug | Fix |
|---|-----|-----|
| 1 | `result["results"]` bracket access crashes on malformed API response | Changed to `.get("results", [])` in all 5 pagination loops |
| 2 | `page duplicate` copies read-only properties (formula, rollup, etc.) | Filters out 6 read-only property types before `pages.create()` |
| 3 | `--limit 0` sends invalid `page_size=0` to API | Added `validate_limit()` in `parsing.py`; called in `search`, `db query`, `user list` |
| 4 | `json.loads` results not type-validated | Added `parse_json()` in `parsing.py`; validates `dict` vs `list` after parsing |
| 5 | JSON parse errors exit code 1 instead of 2 | `parse_json()` catches `JSONDecodeError` → exit code 2 with `invalid_json` error type |
| 6 | `page create` hardcodes parent as `page_id` | Added `--parent-type` option (`page`/`database`, default `page`) to `page create` |
| 7 | `page create --content` sends unrecognized `content` field to API | Uses `client.request()` with `markdown` body field and API version `2026-03-11`, bypassing SDK's `pick()` filter |
| 15 | Eager command module imports in `cli.py` | `_LazyTyperGroup` subclass defers imports via `get_command()` |
| 19 | `format_json(pretty=True)` dead code | Removed `pretty` param; hardcoded compact output |
| 20 | Double env var resolution | Removed `envvar` from `options.py`; `auth.py` is the single resolver |
| 21 | Response envelope mutation after `async with` | Build fresh `envelope` dict; assemble output without mutating SDK response |
| 22 | `_HEADING_TYPES` frozenset redundant | Deleted; membership tests use `_HEADING_PREFIX` dict directly |
| 24 | `page_size` not reduced mid-pagination | Added `page_size = min(remaining, 100)` before each subsequent fetch |

### Fixed in audit round 2

| Bug | Fix |
|-----|-----|
| `user get` skips `extract_id()` — URLs broken | Added `extract_id()` call |
| Callout `icon: null` crashes `--markdown` | `(data.get("icon") or {}).get(...)` |
| `link['url']` bare KeyError in markdown | Changed to `link.get('url', '')` |
| `auth login` KeyError on missing `access_token` | Validates before access with structured error |
| `page duplicate` bare `original["properties"]` access | Safe `.get()` with defaults |
| `auth login` no port validation | Validates 1–65535 range |
| `str(exc.code)` wrong on `APIErrorCode` enum | Uses `.value` when available |
| `format_json` non-compact separators | Added `separators=(",",":")` for ~12% smaller output |
| `_READ_ONLY_TYPES` rebuilt per call | Hoisted to module level |
| Credentials TOCTOU (world-readable before chmod) | `os.open` with `0o600` from creation |
| `delete_credentials` doesn't catch `PermissionError` | Added to except clause |
| No `try/finally` for `server_close()` | Added finally block |
| `notion_client.Client` imported at module level in auth | Deferred into `login()` and `logout()` |
| OAuth client secret hardcoded in source | Build-time injection via `_oauth_secret.py` |
| `--timeout 0` exits code 1 instead of 2 | `ValueError` caught explicitly → `ExitCode.BAD_ARGS` |
| `save_credentials` OSError produces raw traceback | Wrapped with structured error |
| Redundant `format_error` re-import in `page.py` | Moved to module-level import |
| `markdown.py` module docstring violates style rule | Removed |
| `parse_json` defers `import json` unnecessarily | Moved to module-level import |
| `db create` docstring incorrectly attributes `Name` to Notion | Fixed wording |

## Fixed Test Gaps

| Gap | Tests Added |
|-----|-------------|
| Markdown block types untested | 12 tests: image, callout, equation, child_page, etc. |
| `--version` flag untested | 1 test |
| `@file` and stdin untested at CLI level | 3 tests |
| `user list --limit` not tested | 1 test |
| `RequestTimeoutError` branch not tested | 1 test |
| `restricted_resource` error code mapping not tested | 1 test |
| `read_content` error paths partially untested | 2 tests |
| `APIErrorCode` enum not tested (tests used raw strings) | 1 test with real enum |
| `auth login` `missing_code` branch untested | 1 test |
| `page move` only 1 happy-path test | 2 tests (URL extraction, parent structure) |
| Error tests use `result.output` instead of `result.stderr` | All error tests now use `result.stderr` |
| Missing OAuth secret validation untested | 1 test |
| Callout null icon untested | 1 test |
| Link missing URL untested | 1 test |

## Fixed Docs/Config

| Issue | Fix |
|-------|-----|
| CONTRIBUTING pagination template mutates SDK dict | Updated to envelope pattern + `.get()` |
| CONTRIBUTING lint command omits `tests/` | Fixed |
| CONTRIBUTING doesn't mention auth commands are sync | Added exception note |
| CONTRIBUTING doesn't explain mock_client requires lazy imports | Added note to fixture docs |
| Pre-commit config v0.9.10, deprecated `ruff` hook id | Updated to v0.15.5, `ruff-check`, removed pytest pre-push |
| No `ty` in CI/docs | Added to CI, README, CONTRIBUTING |
| No publish workflow | Added with trusted publishers (OIDC) |
| README stale "MCP parity" description | Rewritten for agent-first pitch |
| No PyPI package name (taken) | Published as `notionctl` |

---

## Remaining Unfixed

### 26. OAuth page picker forces per-page access (not workspace-wide)

Notion's OAuth consent screen for third-party public integrations always shows a page picker ("View pages you select"). Users must manually select which pages the integration can access. There is no OAuth parameter, scope, or capability setting to bypass this — it's enforced server-side by Notion based on the integration's `client_id`.

**Why the MCP integration is different:** Notion's first-party MCP server (`mcp.notion.com`) uses a privileged `client_id` that Notion has configured server-side for user-level workspace access.

**Current workaround:** The `notion auth login` command prints a tip asking users to select all pages.

**To resolve:** Contact Notion (developers@makenotion.com or Technology Partner Program) to request user-level workspace access for client_id `320d872b-594c-81ce-bd3e-003786f0191c`. Server-side change, zero code needed.

---

## Known/Accepted Tradeoffs

| Issue | Why accepted |
|-------|-------------|
| `AsyncClient` created per command function | CLI runs one command and exits. Connection pool reused within `async with` for pagination. |
| Per-request timeout (not per-command) | Documented in help text. Users can Ctrl+C for total-time limits. |
| Blocking I/O in `parsing.py` | Documented in CONTRIBUTING. Benign for single-command CLI. |
| `notion_client.errors` imported inside exception handler | Intentional deferral to keep startup fast. |
| All paginated results buffered in memory | Architectural. `--limit` exists as safety valve. |
| Typer required-option errors aren't JSON | Framework limitation. Typer emits plain text for missing required options. |
| `auth.py` stdlib imports at module level (+17ms for auth commands) | Moving them would break test patches that target `notion_cli.commands.auth.*`. |

---

## Future Work

Features identified by audit agents that would improve the CLI but are not bugs.

- **Recursive block retrieval**: `block get` only returns top-level blocks. Nested content (toggles, sub-bullets, columns) is silently dropped. A `--recursive` flag would make `block get --markdown` return the full page. This is the biggest workflow gap vs MCP.
- **Page duplicate with content**: `page duplicate` copies properties, icon, and cover but not block content. Requires fetching all blocks recursively and appending them.
- **Comment replies and rich text**: `comment add` only creates top-level page comments with plain text. The Notion API supports `discussion_id` for replies and rich text arrays for formatting.
- **Field projection**: Every command outputs the full Notion API response. A `--fields id,title,url` option would reduce output for agents that only need specific values.
- **`--limit` for `block get` and `comment list`**: These paginated commands have no limit option, unlike `search`, `db query`, and `user list`.

---

## Audit Agent Prompt

Use this prompt to run 6 adversarial audit agents against the notion-cli codebase. Each agent should run independently with no shared context. Copy this into a fresh Claude Code session.

```
I want you to launch 6 background subagents, all with opus, to adversarially audit the notion-cli project at ~/repos/notion-cli/. Each agent must read ALL source files before reporting. They must not share context. Their job is to find bugs, edge cases, and issues that would affect real users.

Launch all 6 in parallel:

1. **Speed audit**: Audit for startup speed, runtime performance, unnecessary overhead, heavy imports, redundant work, and slow paths. Measure startup times where possible.

2. **Resource audit**: Audit for resource efficiency, memory usage, error handling edge cases, and correctness. Check pagination loops for infinite loops, KeyError crashes, memory accumulation. Check file I/O, JSON parsing, and all error paths. Try to crash or confuse every command with edge-case inputs.

3. **Async audit**: Audit for async correctness and event loop safety. Check the async-to-sync bridge, timeout handling, exception hierarchy, blocking I/O inside async functions, context manager cleanup, coroutine lifecycle, and test robustness. Try to find race conditions, resource leaks, or exception paths that produce wrong behavior.

4. **Duplication audit**: Audit for code duplication, structural issues, test coverage gaps, help text inconsistencies, dead code, and documentation accuracy. Count repeated patterns. Check every command has tests for every option. Check README and CONTRIBUTING accuracy against actual code.

5. **Agent user audit**: You are a coding agent (Claude Code, Cursor, Aider) evaluating this CLI for use in your workflows. Simulate real workflows like "find and read a page", "update a database row", "create a page from markdown". Check error handling for bad inputs. What works, what's broken, what's missing? Compare to using an MCP server.

6. **Developer audit**: You are a developer who wants to contribute a new feature. Evaluate the developer experience: Can you understand how to add a command? Are the docs accurate? Is the test infrastructure sufficient? Is CI/CD complete? What would slow you down?

All agents should report with specific file:line references. Be adversarial. Do not assume anything works correctly just because tests pass.
```
