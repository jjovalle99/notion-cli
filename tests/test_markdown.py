from notion_cli.markdown import blocks_to_markdown, rich_text_to_md


class TestRichText:
    def test_plain_text(self) -> None:
        rich_text = [{"type": "text", "text": {"content": "Hello world"}, "annotations": {}}]
        assert rich_text_to_md(rich_text) == "Hello world"

    def test_bold(self) -> None:
        rich_text = [{"type": "text", "text": {"content": "bold"}, "annotations": {"bold": True}}]
        assert rich_text_to_md(rich_text) == "**bold**"

    def test_italic(self) -> None:
        rich_text = [
            {"type": "text", "text": {"content": "italic"}, "annotations": {"italic": True}}
        ]
        assert rich_text_to_md(rich_text) == "*italic*"

    def test_code_inline(self) -> None:
        rich_text = [{"type": "text", "text": {"content": "code"}, "annotations": {"code": True}}]
        assert rich_text_to_md(rich_text) == "`code`"

    def test_strikethrough(self) -> None:
        rich_text = [
            {
                "type": "text",
                "text": {"content": "removed"},
                "annotations": {"strikethrough": True},
            }
        ]
        assert rich_text_to_md(rich_text) == "~~removed~~"

    def test_link(self) -> None:
        rich_text = [
            {
                "type": "text",
                "text": {"content": "click", "link": {"url": "https://example.com"}},
                "annotations": {},
            }
        ]
        assert rich_text_to_md(rich_text) == "[click](https://example.com)"

    def test_mixed(self) -> None:
        rich_text = [
            {"type": "text", "text": {"content": "normal "}, "annotations": {}},
            {"type": "text", "text": {"content": "bold"}, "annotations": {"bold": True}},
            {"type": "text", "text": {"content": " end"}, "annotations": {}},
        ]
        assert rich_text_to_md(rich_text) == "normal **bold** end"

    def test_mention(self) -> None:
        rich_text = [
            {
                "type": "mention",
                "mention": {"type": "user", "user": {"id": "abc"}},
                "plain_text": "John",
                "annotations": {},
            }
        ]
        assert rich_text_to_md(rich_text) == "@John"

    def test_equation_span(self) -> None:
        rich_text = [{"type": "equation", "equation": {"expression": "E=mc^2"}, "annotations": {}}]
        assert rich_text_to_md(rich_text) == "$E=mc^2$"


class TestBlocks:
    def test_paragraph(self) -> None:
        blocks = [
            {
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {"type": "text", "text": {"content": "Hello"}, "annotations": {}}
                    ]
                },
            }
        ]
        assert blocks_to_markdown(blocks) == "Hello\n"

    def test_headings(self) -> None:
        blocks = [
            {
                "type": "heading_1",
                "heading_1": {
                    "rich_text": [{"type": "text", "text": {"content": "H1"}, "annotations": {}}]
                },
            },
            {
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "H2"}, "annotations": {}}]
                },
            },
            {
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [{"type": "text", "text": {"content": "H3"}, "annotations": {}}]
                },
            },
        ]
        assert blocks_to_markdown(blocks) == "# H1\n\n## H2\n\n### H3\n"

    def test_bulleted_list(self) -> None:
        blocks = [
            {
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [
                        {"type": "text", "text": {"content": "item 1"}, "annotations": {}}
                    ]
                },
            },
            {
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [
                        {"type": "text", "text": {"content": "item 2"}, "annotations": {}}
                    ]
                },
            },
        ]
        assert blocks_to_markdown(blocks) == "- item 1\n- item 2\n"

    def test_numbered_list(self) -> None:
        blocks = [
            {
                "type": "numbered_list_item",
                "numbered_list_item": {
                    "rich_text": [
                        {"type": "text", "text": {"content": "first"}, "annotations": {}}
                    ]
                },
            },
            {
                "type": "numbered_list_item",
                "numbered_list_item": {
                    "rich_text": [
                        {"type": "text", "text": {"content": "second"}, "annotations": {}}
                    ]
                },
            },
        ]
        assert blocks_to_markdown(blocks) == "1. first\n2. second\n"

    def test_todo(self) -> None:
        blocks = [
            {
                "type": "to_do",
                "to_do": {
                    "rich_text": [
                        {"type": "text", "text": {"content": "done"}, "annotations": {}}
                    ],
                    "checked": True,
                },
            },
            {
                "type": "to_do",
                "to_do": {
                    "rich_text": [
                        {"type": "text", "text": {"content": "pending"}, "annotations": {}}
                    ],
                    "checked": False,
                },
            },
        ]
        assert blocks_to_markdown(blocks) == "- [x] done\n- [ ] pending\n"

    def test_code_block(self) -> None:
        blocks = [
            {
                "type": "code",
                "code": {
                    "rich_text": [
                        {"type": "text", "text": {"content": "print('hi')"}, "annotations": {}}
                    ],
                    "language": "python",
                },
            }
        ]
        assert blocks_to_markdown(blocks) == "```python\nprint('hi')\n```\n"

    def test_quote(self) -> None:
        blocks = [
            {
                "type": "quote",
                "quote": {
                    "rich_text": [
                        {"type": "text", "text": {"content": "wise words"}, "annotations": {}}
                    ]
                },
            }
        ]
        assert blocks_to_markdown(blocks) == "> wise words\n"

    def test_divider(self) -> None:
        blocks = [{"type": "divider", "divider": {}}]
        assert blocks_to_markdown(blocks) == "---\n"

    def test_empty_paragraph(self) -> None:
        blocks = [{"type": "paragraph", "paragraph": {"rich_text": []}}]
        assert blocks_to_markdown(blocks) == "\n"

    def test_multiple_blocks(self) -> None:
        blocks = [
            {
                "type": "heading_1",
                "heading_1": {
                    "rich_text": [
                        {"type": "text", "text": {"content": "Title"}, "annotations": {}}
                    ]
                },
            },
            {
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {"type": "text", "text": {"content": "Body text."}, "annotations": {}}
                    ]
                },
            },
        ]
        assert blocks_to_markdown(blocks) == "# Title\n\nBody text.\n"
