from typing import Any

_HEADING_PREFIX = {"heading_1": "# ", "heading_2": "## ", "heading_3": "### "}


def rich_text_to_md(rich_text: list[dict[str, Any]]) -> str:
    """Convert a Notion rich_text array to a Markdown string."""
    parts: list[str] = []
    for span in rich_text:
        span_type = span.get("type", "text")

        if span_type == "mention":
            mention = span.get("mention", {})
            mention_type = mention.get("type", "")
            plain = span.get("plain_text", "")
            text = f"@{plain}" if plain else f"[{mention_type} mention]"
        elif span_type == "equation":
            text = f"${span.get('equation', {}).get('expression', '')}$"
        else:
            text = span.get("text", {}).get("content", "")
            link = span.get("text", {}).get("link")
            if link:
                text = f"[{text}]({link.get('url', '')})"

        annotations = span.get("annotations", {})
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
    text = rich_text_to_md(rich_text)

    if block_type in _HEADING_PREFIX:
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
        file_data = data.get("file") or data.get("external") or {}
        url = file_data.get("url", "") if isinstance(file_data, dict) else ""
        caption = rich_text_to_md(data.get("caption", []))
        return f"![{caption}]({url})"

    if block_type == "bookmark":
        url = data.get("url", "")
        caption = rich_text_to_md(data.get("caption", []))
        return f"[{caption or url}]({url})"

    if block_type == "callout":
        icon = (data.get("icon") or {}).get("emoji", "")
        parts = [p for p in [icon, text] if p]
        return f"> {' '.join(parts)}" if parts else ">"

    if block_type == "equation":
        return f"$${data.get('expression', '')}$$"

    if block_type == "child_page":
        title = data.get("title", "")
        return f"[{title}](child_page)" if title else ""

    if block_type == "child_database":
        title = data.get("title", "")
        return f"[{title}](child_database)" if title else ""

    if block_type == "table_of_contents":
        return "[Table of Contents]"

    # Unknown block type: render as plain text if possible
    return text


def blocks_to_markdown(blocks: list[dict[str, Any]]) -> str:
    """Convert a list of Notion blocks to a Markdown string."""
    lines: list[str] = []
    numbered_counter = 0
    prev_type = ""

    for block in blocks:
        block_type = block.get("type", "")

        if block_type == "numbered_list_item":
            numbered_counter += 1
        else:
            numbered_counter = 0

        if block_type in _HEADING_PREFIX and lines:
            lines.append("")
        if prev_type in _HEADING_PREFIX and block_type not in _HEADING_PREFIX:
            lines.append("")

        line = _block_to_md(block, numbered_counter)
        lines.append(line)
        prev_type = block_type

    return "\n".join(lines) + "\n" if lines else ""
