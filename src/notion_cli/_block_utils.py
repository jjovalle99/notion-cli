import asyncio
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any

from notion_cli._async import await_with_timeout

if TYPE_CHECKING:
    from notion_client import AsyncClient

_BLOCK_SERVER_FIELDS = frozenset(
    {
        "id",
        "created_time",
        "last_edited_time",
        "created_by",
        "last_edited_by",
        "has_children",
        "archived",
        "object",
        "parent",
        "in_trash",
    }
)

_SKIP_RECURSE_TYPES = frozenset({"child_page", "child_database", "synced_block"})
SKIP_CONTENT_TYPES = _SKIP_RECURSE_TYPES | frozenset({"unsupported"})

APPEND_BATCH_SIZE = 100


async def fetch_children(
    client: "AsyncClient",
    block_id: str,
    timeout: float | None,
    *,
    limit: int | None = None,
) -> tuple[list[dict[str, Any]], dict[str, object]]:
    """Fetch all child blocks of a block, with optional limit.

    Returns:
        A tuple of (blocks, envelope) where envelope is API response metadata.
    """
    kwargs: dict[str, object] = {}
    if limit is not None:
        kwargs["page_size"] = min(limit, 100)

    result = await await_with_timeout(client.blocks.children.list(block_id, **kwargs), timeout)
    all_blocks: list[dict[str, Any]] = list(result.get("results") or [])

    while (
        result.get("has_more")
        and result.get("next_cursor")
        and result.get("results")
        and (limit is None or len(all_blocks) < limit)
    ):
        kwargs["start_cursor"] = result["next_cursor"]
        if limit is not None:
            kwargs["page_size"] = min(limit - len(all_blocks), 100)
        result = await await_with_timeout(client.blocks.children.list(block_id, **kwargs), timeout)
        all_blocks.extend(result.get("results") or [])

    if limit is not None:
        all_blocks = all_blocks[:limit]
    envelope: dict[str, object] = {
        k: v for k, v in result.items() if k not in ("results", "has_more")
    }
    return all_blocks, envelope


async def fetch_recursive(
    client: "AsyncClient",
    block_id: str,
    timeout: float | None,
    *,
    max_depth: int = 5,
    _depth: int = 0,
    _semaphore: asyncio.Semaphore | None = None,
) -> list[dict[str, Any]]:
    """Fetch all blocks recursively, attaching children to parent blocks."""
    semaphore = _semaphore if _semaphore is not None else asyncio.Semaphore(3)

    async def _guarded_list(bid: str) -> dict[str, Any]:
        async with semaphore:
            return await await_with_timeout(client.blocks.children.list(bid), timeout)

    result = await _guarded_list(block_id)
    blocks: list[dict[str, Any]] = list(result.get("results") or [])

    while result.get("has_more") and result.get("next_cursor") and result.get("results"):
        async with semaphore:
            result = await await_with_timeout(
                client.blocks.children.list(block_id, start_cursor=result["next_cursor"]),
                timeout,
            )
        blocks.extend(result.get("results") or [])

    if _depth + 1 >= max_depth:
        return blocks

    recurse_indices = [
        i
        for i, b in enumerate(blocks)
        if b.get("has_children") and b.get("id") and b.get("type") not in _SKIP_RECURSE_TYPES
    ]

    if not recurse_indices:
        return blocks

    child_results = await asyncio.gather(
        *(
            fetch_recursive(
                client,
                blocks[i]["id"],
                timeout,
                max_depth=max_depth,
                _depth=_depth + 1,
                _semaphore=semaphore,
            )
            for i in recurse_indices
        )
    )

    for idx, children in zip(recurse_indices, child_results):
        blocks[idx]["children"] = children

    return blocks


RICH_TEXT_BLOCK_TYPES = frozenset(
    {
        "paragraph",
        "heading_1",
        "heading_2",
        "heading_3",
        "bulleted_list_item",
        "numbered_list_item",
        "to_do",
        "toggle",
        "quote",
        "callout",
        "code",
        "template",
    }
)


def replace_in_rich_text(
    rich_text: list[dict[str, Any]], find: str, replace: str
) -> tuple[list[dict[str, Any]], bool]:
    """Replace text within rich_text spans, preserving annotations and links.

    Returns:
        A tuple of (new_rich_text, changed). If no match found, returns the
        original list unchanged with changed=False.
    """
    changed = False
    result: list[dict[str, Any]] = []
    for span in rich_text:
        if span.get("type") != "text":
            result.append(span)
            continue
        text_data = span.get("text")
        if not isinstance(text_data, dict):
            result.append(span)
            continue
        content = text_data.get("content", "")
        if find not in content:
            result.append(span)
            continue
        changed = True
        new_span = {**span, "text": {**span["text"], "content": content.replace(find, replace)}}
        result.append(new_span)
    if not changed:
        return rich_text, False
    return result, True


def flatten_blocks(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flatten a recursive block tree into a flat list."""

    def _walk(items: list[dict[str, Any]]) -> Iterator[dict[str, Any]]:
        for block in items:
            yield block
            children = block.get("children")
            if children:
                yield from _walk(children)

    return list(_walk(blocks))


_MAX_CLEAN_DEPTH = 50


def clean_block(
    block: dict[str, Any], *, skip_types: frozenset[str] | None = None, _depth: int = 0
) -> dict[str, Any]:
    """Strip server-assigned fields from a block for re-creation via append."""
    if _depth > _MAX_CLEAN_DEPTH:
        msg = f"Block nesting exceeds maximum depth ({_MAX_CLEAN_DEPTH})"
        raise ValueError(msg)
    cleaned = {k: v for k, v in block.items() if k not in _BLOCK_SERVER_FIELDS}
    if "children" in cleaned:
        cleaned["children"] = [
            clean_block(c, skip_types=skip_types, _depth=_depth + 1)
            for c in cleaned["children"]
            if skip_types is None or c.get("type") not in skip_types
        ]
    return cleaned
