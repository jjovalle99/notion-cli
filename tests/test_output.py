import json

from notion_cli.output import ExitCode, format_error, format_json, format_ndjson, project_fields


def test_project_fields_dict() -> None:
    data = {"id": "abc", "title": "Test", "url": "https://example.com"}
    result = project_fields(data, {"id", "url"})
    assert result == {"id": "abc", "url": "https://example.com"}


def test_project_fields_list() -> None:
    data = [{"id": "1", "name": "A"}, {"id": "2", "name": "B"}]
    result = project_fields(data, {"id"})
    assert result == [{"id": "1"}, {"id": "2"}]


def test_project_fields_list_preserves_non_dict_items() -> None:
    data = [{"id": "1", "name": "A"}, "plain-string", 42]
    result = project_fields(data, {"id"})
    assert result == [{"id": "1"}, "plain-string", 42]


def test_project_fields_none_returns_unchanged() -> None:
    data = {"id": "abc", "title": "Test"}
    assert project_fields(data, None) is data


def test_project_fields_empty_set() -> None:
    data = {"id": "abc", "title": "Test"}
    result = project_fields(data, set())
    assert result == {}


def test_format_json_dict() -> None:
    result = format_json({"id": "abc", "title": "Test"})
    parsed = json.loads(result)
    assert parsed == {"id": "abc", "title": "Test"}


def test_format_json_list() -> None:
    result = format_json([{"id": "1"}, {"id": "2"}])
    parsed = json.loads(result)
    assert parsed == [{"id": "1"}, {"id": "2"}]


def test_format_json_compact_by_default() -> None:
    result = format_json({"a": 1})
    assert "\n" not in result


def test_format_error_structure() -> None:
    result = format_error("not_found", "Page not found", suggestion="Check the page ID")
    parsed = json.loads(result)
    assert parsed["error_type"] == "not_found"
    assert parsed["message"] == "Page not found"
    assert parsed["suggestion"] == "Check the page ID"


def test_format_error_without_suggestion() -> None:
    result = format_error("rate_limited", "Too many requests")
    parsed = json.loads(result)
    assert parsed["error_type"] == "rate_limited"
    assert parsed["message"] == "Too many requests"
    assert "suggestion" not in parsed


def test_exit_code_values() -> None:
    assert ExitCode.OK == 0
    assert ExitCode.ERROR == 1
    assert ExitCode.BAD_ARGS == 2
    assert ExitCode.NOT_FOUND == 3
    assert ExitCode.PERMISSION == 4
    assert ExitCode.RATE_LIMITED == 5


def test_format_ndjson_one_line_per_item() -> None:
    items = [{"id": "1", "name": "A"}, {"id": "2", "name": "B"}]
    result = format_ndjson(items)
    lines = result.strip().split("\n")
    assert len(lines) == 2
    assert json.loads(lines[0]) == {"id": "1", "name": "A"}
    assert json.loads(lines[1]) == {"id": "2", "name": "B"}


def test_format_ndjson_compact_lines() -> None:
    result = format_ndjson([{"a": 1}])
    assert result == '{"a":1}\n'


def test_format_ndjson_empty_list() -> None:
    assert format_ndjson([]) == ""
