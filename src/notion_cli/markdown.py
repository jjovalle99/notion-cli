from typing import Any

_HEADING_PREFIX = {"heading_1": "# ", "heading_2": "## ", "heading_3": "### "}
_LAYOUT_CONTAINERS = frozenset({"column_list", "column"})


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

        annotations = span.get("annotations") or {}
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


def _block_to_md(block: dict[str, Any], number: int, depth: int = 0) -> str:
    block_type = block.get("type", "")
    data = block.get(block_type, {})
    rich_text = data.get("rich_text", [])
    text = rich_text_to_md(rich_text)
    indent = "    " * depth

    if block_type in _HEADING_PREFIX:
        return _HEADING_PREFIX[block_type] + text

    if block_type == "paragraph":
        return f"{indent}{text}"

    if block_type == "bulleted_list_item":
        return f"{indent}- {text}"

    if block_type == "numbered_list_item":
        return f"{indent}{number}. {text}"

    if block_type == "to_do":
        check = "x" if data.get("checked") else " "
        return f"{indent}- [{check}] {text}"

    if block_type == "code":
        lang = data.get("language", "")
        indented_text = text.replace("\n", f"\n{indent}")
        return f"{indent}```{lang}\n{indent}{indented_text}\n{indent}```"

    if block_type == "quote":
        return f"{indent}> {text}"

    if block_type == "divider":
        return f"{indent}---"

    if block_type == "image":
        file_data = data.get("file") or data.get("external") or {}
        url = file_data.get("url", "") if isinstance(file_data, dict) else ""
        caption = rich_text_to_md(data.get("caption", []))
        return f"{indent}![{caption}]({url})"

    if block_type in ("video", "audio", "pdf", "file"):
        file_data = data.get("file") or data.get("external") or {}
        url = file_data.get("url", "") if isinstance(file_data, dict) else ""
        caption = rich_text_to_md(data.get("caption", []))
        return f"{indent}[{caption or block_type}]({url})"

    if block_type == "embed":
        url = data.get("url", "")
        caption = rich_text_to_md(data.get("caption", []))
        return f"{indent}[{caption or block_type}]({url})"

    if block_type == "bookmark":
        url = data.get("url", "")
        caption = rich_text_to_md(data.get("caption", []))
        return f"{indent}[{caption or url}]({url})"

    if block_type == "callout":
        icon = (data.get("icon") or {}).get("emoji", "")
        parts = [p for p in [icon, text] if p]
        return f"{indent}> {' '.join(parts)}" if parts else f"{indent}>"

    if block_type == "equation":
        return f"{indent}$${data.get('expression', '')}$$"

    if block_type == "child_page":
        title = data.get("title", "")
        return f"{indent}[{title}](child_page)" if title else ""

    if block_type == "child_database":
        title = data.get("title", "")
        return f"{indent}[{title}](child_database)" if title else ""

    if block_type == "table":
        rows = block.get("children", [])
        if not rows:
            return ""
        lines: list[str] = []
        for i, row in enumerate(rows):
            cells = row.get("table_row", {}).get("cells", [])
            cols = [rich_text_to_md(c) for c in cells]
            lines.append(f"{indent}| {' | '.join(cols)} |")
            if i == 0:
                lines.append(f"{indent}| {' | '.join('---' for _ in cols)} |")
        return "\n".join(lines)

    if block_type == "table_row":
        cells = data.get("cells", [])
        cols = [rich_text_to_md(c) for c in cells]
        return f"{indent}| {' | '.join(cols)} |"

    if block_type == "table_of_contents":
        return f"{indent}[Table of Contents]"

    if block_type == "toggle":
        return f"{indent}- **{text}**" if text else ""

    return f"{indent}{text}"


def blocks_to_markdown(blocks: list[dict[str, Any]], depth: int = 0) -> str:
    """Convert a list of Notion blocks to a Markdown string."""
    lines: list[str] = []
    numbered_counter = 0
    prev_type = ""

    for block in blocks:
        block_type = block.get("type", "")

        if block_type in _LAYOUT_CONTAINERS:
            children = block.get("children", [])
            if children:
                child_md = blocks_to_markdown(children, depth).rstrip("\n")
                if child_md:
                    lines.append(child_md)
            continue

        if block_type == "numbered_list_item":
            numbered_counter += 1
        else:
            numbered_counter = 0

        if block_type in _HEADING_PREFIX and lines:
            lines.append("")
        if prev_type in _HEADING_PREFIX and block_type not in _HEADING_PREFIX:
            lines.append("")

        line = _block_to_md(block, numbered_counter, depth)
        lines.append(line)

        if block_type != "table":
            children = block.get("children", [])
            if children:
                child_md = blocks_to_markdown(children, depth + 1).rstrip("\n")
                if child_md:
                    lines.append(child_md)

        prev_type = block_type

    return "\n".join(lines) + "\n" if lines else ""
