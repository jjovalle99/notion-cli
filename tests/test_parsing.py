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

    def test_at_directory_raises(self, tmp_path: pathlib.Path) -> None:
        with pytest.raises(SystemExit):
            read_content(f"@{tmp_path}")

    def test_at_binary_file_raises(self, tmp_path: pathlib.Path) -> None:
        f = tmp_path / "binary.bin"
        f.write_bytes(b"\x80\x81\x82\xff\xfe")
        with pytest.raises(SystemExit):
            read_content(f"@{f}")

    def test_at_permission_denied_raises(self, tmp_path: pathlib.Path) -> None:
        f = tmp_path / "secret.txt"
        f.write_text("secret")
        f.chmod(0o000)
        try:
            with pytest.raises(SystemExit):
                read_content(f"@{f}")
        finally:
            f.chmod(0o644)


class TestParseJson:
    def test_valid_dict(self) -> None:
        from notion_cli.parsing import parse_json

        result = parse_json('{"key": "value"}', expected_type=dict, label="--test")
        assert result == {"key": "value"}

    def test_valid_list(self) -> None:
        from notion_cli.parsing import parse_json

        result = parse_json("[1, 2, 3]", expected_type=list, label="--test")
        assert result == [1, 2, 3]

    def test_invalid_json_raises(self) -> None:
        from notion_cli.parsing import parse_json

        with pytest.raises(SystemExit):
            parse_json("{bad}", expected_type=dict, label="--test")

    def test_wrong_type_raises(self) -> None:
        from notion_cli.parsing import parse_json

        with pytest.raises(SystemExit):
            parse_json('["array"]', expected_type=dict, label="--test")


class TestValidateLimit:
    def test_valid_limit(self) -> None:
        from notion_cli.parsing import validate_limit

        validate_limit(5)  # should not raise

    def test_none_passes(self) -> None:
        from notion_cli.parsing import validate_limit

        validate_limit(None)  # should not raise

    def test_zero_raises(self) -> None:
        from notion_cli.parsing import validate_limit

        with pytest.raises(SystemExit):
            validate_limit(0)

    def test_negative_raises(self) -> None:
        from notion_cli.parsing import validate_limit

        with pytest.raises(SystemExit):
            validate_limit(-1)
