import json

from notion_cli.output import format_json, format_error, ExitCode


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


def test_format_json_pretty_when_requested() -> None:
    result = format_json({"a": 1}, pretty=True)
    assert "\n" in result


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
