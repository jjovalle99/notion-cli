"""Convert Notion block arrays to Markdown text."""

from typing import Any

_HEADING_PREFIX = {"heading_1": "# ", "heading_2": "## ", "heading_3": "### "}

_HEADING_TYPES = frozenset(_HEADING_PREFIX)
_LIST_TYPES = frozenset({"bulleted_list_item", "numbered_list_item", "to_do"})


def _rich_text_to_md(rich_text: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for span in rich_text:
        text = span.get("text", {}).get("content", "")
        annotations = span.get("annotations", {})
        link = span.get("text", {}).get("link")

        if link:
            text = f"[{text}]({link['url']})"
        if annotations.get("code"):
            text = f"`{text}`"
        if annotations.get("bold"):
            text = f"**{text}**"
        if annotations.get("italic"):
            text = f"*{text}*"
        if annotations.get("strikethrough"):
            text = f"~~{text}~~"

        parts.append(text)
    return "".join(parts)


def _block_to_md(block: dict[str, Any], number: int) -> str:
    block_type = block.get("type", "")
    data = block.get(block_type, {})
    rich_text = data.get("rich_text", [])
    text = _rich_text_to_md(rich_text)

    if block_type in _HEADING_TYPES:
        return _HEADING_PREFIX[block_type] + text

    if block_type == "paragraph":
        return text

    if block_type == "bulleted_list_item":
        return f"- {text}"

    if block_type == "numbered_list_item":
        return f"{number}. {text}"

    if block_type == "to_do":
        check = "x" if data.get("checked") else " "
        return f"- [{check}] {text}"

    if block_type == "code":
        lang = data.get("language", "")
        return f"```{lang}\n{text}\n```"

    if block_type == "quote":
        return f"> {text}"

    if block_type == "divider":
        return "---"

    if block_type == "image":
        url = data.get("file", data.get("external", {})).get("url", "")
        caption = _rich_text_to_md(data.get("caption", []))
        return f"![{caption}]({url})"

    if block_type == "bookmark":
        url = data.get("url", "")
        caption = _rich_text_to_md(data.get("caption", []))
        return f"[{caption or url}]({url})"

    if block_type == "callout":
        icon = data.get("icon", {}).get("emoji", "")
        return f"> {icon} {text}".strip()

    if block_type == "equation":
        return f"$${data.get('expression', '')}$$"

    # Unknown block type: render as plain text if possible
    return text


def blocks_to_markdown(blocks: list[dict[str, Any]]) -> str:
    """Convert a list of Notion blocks to a Markdown string."""
    lines: list[str] = []
    numbered_counter = 0
    prev_type = ""

    for block in blocks:
        block_type = block.get("type", "")

        # Reset numbered list counter when leaving a numbered list
        if block_type == "numbered_list_item":
            numbered_counter += 1
        else:
            numbered_counter = 0

        # Add blank line before headings and after headings
        if block_type in _HEADING_TYPES and lines:
            lines.append("")
        if prev_type in _HEADING_TYPES and block_type not in _HEADING_TYPES:
            lines.append("")

        line = _block_to_md(block, numbered_counter)
        lines.append(line)
        prev_type = block_type

    return "\n".join(lines) + "\n" if lines else ""


# Expose _rich_text_to_md for testing
blocks_to_markdown._rich_text_to_md = _rich_text_to_md  # type: ignore[attr-defined]
