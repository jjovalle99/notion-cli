import json
import stat
from pathlib import Path

import pytest

from notion_cli.credentials import delete_credentials, load_credentials, save_credentials


@pytest.fixture()
def cred_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "credentials.json"
    monkeypatch.setattr("notion_cli.credentials._credentials_path", lambda: path)
    return path


class TestLoadCredentials:
    def test_returns_none_when_no_file(self, cred_path: Path) -> None:
        assert load_credentials() is None

    def test_returns_data(self, cred_path: Path) -> None:
        data = {"access_token": "tok_123", "workspace_id": "ws_1"}
        cred_path.write_text(json.dumps(data))
        assert load_credentials() == data

    def test_returns_none_on_malformed_json(self, cred_path: Path) -> None:
        cred_path.write_text("not json{{{")
        assert load_credentials() is None


class TestSaveCredentials:
    def test_creates_file_and_dirs(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        path = tmp_path / "sub" / "credentials.json"
        monkeypatch.setattr("notion_cli.credentials._credentials_path", lambda: path)
        data = {"access_token": "tok_456"}
        save_credentials(data)
        assert json.loads(path.read_text()) == data

    def test_sets_600_permissions(self, cred_path: Path) -> None:
        save_credentials({"access_token": "tok"})
        mode = stat.S_IMODE(cred_path.stat().st_mode)
        assert mode == 0o600

    def test_overwrites_existing(self, cred_path: Path) -> None:
        save_credentials({"access_token": "old"})
        save_credentials({"access_token": "new"})
        assert json.loads(cred_path.read_text())["access_token"] == "new"

    def test_atomic_write_roundtrips(self, cred_path: Path) -> None:
        save_credentials({"access_token": "test123", "workspace_id": "w"})
        loaded = load_credentials()
        assert loaded is not None
        assert loaded["access_token"] == "test123"


class TestDeleteCredentials:
    def test_returns_true_when_file_exists(self, cred_path: Path) -> None:
        cred_path.write_text("{}")
        assert delete_credentials() is True
        assert not cred_path.exists()

    def test_returns_false_when_missing(self, cred_path: Path) -> None:
        assert delete_credentials() is False
