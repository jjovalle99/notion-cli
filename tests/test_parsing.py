import pathlib

import pytest

from notion_cli.parsing import extract_id, read_content


class TestExtractId:
    def test_raw_uuid_with_dashes(self) -> None:
        assert (
            extract_id("12345678-1234-1234-1234-123456789abc")
            == "12345678-1234-1234-1234-123456789abc"
        )

    def test_raw_uuid_without_dashes(self) -> None:
        result = extract_id("123456781234123412341234567890ab")
        assert result == "12345678-1234-1234-1234-1234567890ab"

    def test_page_url(self) -> None:
        url = "https://www.notion.so/myworkspace/My-Page-Title-abc123def456abc123def456abc123de"
        result = extract_id(url)
        assert result == "abc123de-f456-abc1-23de-f456abc123de"

    def test_page_url_with_query_params(self) -> None:
        url = "https://www.notion.so/My-Page-abc123def456abc123def456abc123de?v=xyz"
        result = extract_id(url)
        assert result == "abc123de-f456-abc1-23de-f456abc123de"

    def test_database_url(self) -> None:
        url = "https://www.notion.so/myworkspace/abc123def456abc123def456abc123de?v=view"
        result = extract_id(url)
        assert result == "abc123de-f456-abc1-23de-f456abc123de"

    def test_invalid_input_raises(self) -> None:
        with pytest.raises(SystemExit):
            extract_id("not-a-valid-id")

    def test_block_url(self) -> None:
        url = "https://www.notion.so/Page-abc123def456abc123def456abc123de#block123def456abc123def456abc123de"
        result = extract_id(url)
        assert result == "abc123de-f456-abc1-23de-f456abc123de"


class TestReadContent:
    def test_plain_string(self) -> None:
        assert read_content("Hello world") == "Hello world"

    def test_at_file_path(self, tmp_path: pathlib.Path) -> None:
        f = tmp_path / "content.md"
        f.write_text("# Title\nBody text")
        assert read_content(f"@{f}") == "# Title\nBody text"

    def test_at_file_not_found_raises(self) -> None:
        with pytest.raises(SystemExit):
            read_content("@/nonexistent/file.md")

    def test_dash_reads_stdin(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import io

        monkeypatch.setattr("sys.stdin", io.StringIO("stdin content"))
        assert read_content("-") == "stdin content"
