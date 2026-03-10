import pytest

from notion_cli.auth import resolve_token


def test_resolve_token_from_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NOTION_API_KEY", raising=False)
    assert resolve_token(token="secret_abc") == "secret_abc"


def test_resolve_token_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NOTION_API_KEY", "secret_env")
    assert resolve_token(token=None) == "secret_env"


def test_resolve_token_explicit_overrides_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NOTION_API_KEY", "secret_env")
    assert resolve_token(token="secret_flag") == "secret_flag"


def test_resolve_token_missing_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NOTION_API_KEY", raising=False)
    with pytest.raises(SystemExit):
        resolve_token(token=None)
