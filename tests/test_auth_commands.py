import json
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from notion_cli.commands.auth import auth_app


# ---------------------------------------------------------------------------
# login
# ---------------------------------------------------------------------------
class TestLoginMissingSecret:
    @patch("notion_cli.commands.auth.CLIENT_SECRET", "")
    def test_missing_secret_exits_with_error(self, runner: CliRunner) -> None:
        result = runner.invoke(auth_app, ["login"])
        assert result.exit_code != 0
        out = json.loads(result.stderr.strip())
        assert out["error_type"] == "missing_secret"


@patch("notion_cli.commands.auth.CLIENT_SECRET", "test_secret")
class TestLogin:
    @patch("notion_cli.commands.auth.save_credentials")
    @patch("notion_client.Client")
    @patch("http.server.HTTPServer")
    @patch("webbrowser.open")
    @patch("notion_cli.commands.auth.secrets.token_urlsafe", return_value="fixed_state")
    def test_success(
        self,
        _mock_state: MagicMock,
        _mock_browser: MagicMock,
        mock_server_cls: MagicMock,
        mock_client_cls: MagicMock,
        mock_save: MagicMock,
        runner: CliRunner,
    ) -> None:
        server = MagicMock()
        mock_server_cls.return_value = server

        def _set_callback() -> None:
            server.callback_params = {"code": ["abc"], "state": ["fixed_state"]}
            server.got_callback = True

        server.handle_request.side_effect = _set_callback

        mock_client_cls.return_value.oauth.token.return_value = {
            "access_token": "ntn_tok",
            "workspace_id": "ws_1",
            "workspace_name": "Test WS",
            "bot_id": "bot_1",
            "refresh_token": None,
        }

        result = runner.invoke(auth_app, ["login"])
        assert result.exit_code == 0
        out = json.loads(result.output.splitlines()[-1])
        assert out["status"] == "authenticated"
        assert "access_token" not in out
        assert out["workspace_name"] == "Test WS"
        mock_save.assert_called_once()
        saved = mock_save.call_args[0][0]
        assert saved["access_token"] == "ntn_tok"

    @patch("http.server.HTTPServer")
    @patch("webbrowser.open")
    @patch("notion_cli.commands.auth.secrets.token_urlsafe", return_value="s")
    def test_port_in_use(
        self,
        _mock_state: MagicMock,
        _mock_browser: MagicMock,
        mock_server_cls: MagicMock,
        runner: CliRunner,
    ) -> None:
        mock_server_cls.side_effect = OSError("Address already in use")
        result = runner.invoke(auth_app, ["login"])
        assert result.exit_code != 0

    def test_port_zero_rejected(self, runner: CliRunner) -> None:
        result = runner.invoke(auth_app, ["login", "--port", "0"])
        assert result.exit_code != 0
        out = json.loads(result.stderr.strip())
        assert out["error_type"] == "invalid_port"

    def test_port_negative_rejected(self, runner: CliRunner) -> None:
        result = runner.invoke(auth_app, ["login", "--port", "-1"])
        assert result.exit_code != 0
        out = json.loads(result.stderr.strip())
        assert out["error_type"] == "invalid_port"

    @patch("http.server.HTTPServer")
    @patch("webbrowser.open")
    @patch("notion_cli.commands.auth.secrets.token_urlsafe", return_value="s")
    def test_timeout(
        self,
        _mock_state: MagicMock,
        _mock_browser: MagicMock,
        mock_server_cls: MagicMock,
        runner: CliRunner,
    ) -> None:
        server = MagicMock()
        mock_server_cls.return_value = server
        # handle_request does nothing → callback_params stays empty
        result = runner.invoke(auth_app, ["login"])
        assert result.exit_code != 0

    @patch("http.server.HTTPServer")
    @patch("webbrowser.open")
    @patch("notion_cli.commands.auth.secrets.token_urlsafe", return_value="s")
    def test_access_denied(
        self,
        _mock_state: MagicMock,
        _mock_browser: MagicMock,
        mock_server_cls: MagicMock,
        runner: CliRunner,
    ) -> None:
        server = MagicMock()
        mock_server_cls.return_value = server

        def _set_denied() -> None:
            server.callback_params = {"error": ["access_denied"]}
            server.got_callback = True

        server.handle_request.side_effect = _set_denied
        result = runner.invoke(auth_app, ["login"])
        assert result.exit_code != 0

    @patch("http.server.HTTPServer")
    @patch("webbrowser.open")
    @patch("notion_cli.commands.auth.secrets.token_urlsafe", return_value="expected")
    def test_state_mismatch(
        self,
        _mock_state: MagicMock,
        _mock_browser: MagicMock,
        mock_server_cls: MagicMock,
        runner: CliRunner,
    ) -> None:
        server = MagicMock()
        mock_server_cls.return_value = server

        def _set_wrong_state() -> None:
            server.callback_params = {"code": ["abc"], "state": ["wrong"]}
            server.got_callback = True

        server.handle_request.side_effect = _set_wrong_state
        result = runner.invoke(auth_app, ["login"])
        assert result.exit_code != 0

    @patch("http.server.HTTPServer")
    @patch("webbrowser.open")
    @patch("notion_cli.commands.auth.secrets.token_urlsafe", return_value="fixed_state")
    def test_missing_code_in_callback(
        self,
        _mock_state: MagicMock,
        _mock_browser: MagicMock,
        mock_server_cls: MagicMock,
        runner: CliRunner,
    ) -> None:
        server = MagicMock()
        mock_server_cls.return_value = server

        def _set_no_code() -> None:
            server.callback_params = {"state": ["fixed_state"]}
            server.got_callback = True

        server.handle_request.side_effect = _set_no_code

        result = runner.invoke(auth_app, ["login"])
        assert result.exit_code != 0
        out = json.loads(result.stderr.strip())
        assert out["error_type"] == "missing_code"

    @patch("notion_client.Client")
    @patch("http.server.HTTPServer")
    @patch("webbrowser.open")
    @patch("notion_cli.commands.auth.secrets.token_urlsafe", return_value="fixed_state")
    def test_missing_access_token(
        self,
        _mock_state: MagicMock,
        _mock_browser: MagicMock,
        mock_server_cls: MagicMock,
        mock_client_cls: MagicMock,
        runner: CliRunner,
    ) -> None:
        server = MagicMock()
        mock_server_cls.return_value = server

        def _set_callback() -> None:
            server.callback_params = {"code": ["abc"], "state": ["fixed_state"]}
            server.got_callback = True

        server.handle_request.side_effect = _set_callback
        mock_client_cls.return_value.oauth.token.return_value = {"error": "invalid_grant"}

        result = runner.invoke(auth_app, ["login"])
        assert result.exit_code != 0
        out = json.loads(result.stderr.strip())
        assert out["error_type"] == "auth_failed"

    @patch("notion_cli.commands.auth.save_credentials")
    @patch("notion_client.Client")
    @patch("http.server.HTTPServer")
    @patch("webbrowser.open")
    @patch("notion_cli.commands.auth.secrets.token_urlsafe", return_value="s")
    def test_custom_port(
        self,
        _mock_state: MagicMock,
        _mock_browser: MagicMock,
        mock_server_cls: MagicMock,
        mock_client_cls: MagicMock,
        _mock_save: MagicMock,
        runner: CliRunner,
    ) -> None:
        server = MagicMock()
        mock_server_cls.return_value = server

        def _set_port_callback() -> None:
            server.callback_params = {"code": ["c"], "state": ["s"]}
            server.got_callback = True

        server.handle_request.side_effect = _set_port_callback
        mock_client_cls.return_value.oauth.token.return_value = {
            "access_token": "t",
            "workspace_id": "",
            "workspace_name": "",
            "bot_id": "",
            "refresh_token": None,
        }

        result = runner.invoke(auth_app, ["login", "--port", "9877"])
        assert result.exit_code == 0
        # Verify server was bound to custom port
        mock_server_cls.assert_called_once()
        assert mock_server_cls.call_args[0][0] == ("localhost", 9877)


# ---------------------------------------------------------------------------
# logout
# ---------------------------------------------------------------------------
class TestLogout:
    @patch("notion_cli.commands.auth.delete_credentials", return_value=True)
    @patch("notion_client.Client")
    @patch("notion_cli.commands.auth.load_credentials")
    def test_success(
        self,
        mock_load: MagicMock,
        mock_client_cls: MagicMock,
        _mock_delete: MagicMock,
        runner: CliRunner,
    ) -> None:
        mock_load.return_value = {"access_token": "ntn_tok"}
        result = runner.invoke(auth_app, ["logout"])
        assert result.exit_code == 0
        out = json.loads(result.output)
        assert out["status"] == "logged_out"
        mock_client_cls.return_value.oauth.revoke.assert_called_once()

    @patch("notion_cli.commands.auth.load_credentials", return_value=None)
    def test_not_logged_in(self, _mock_load: MagicMock, runner: CliRunner) -> None:
        result = runner.invoke(auth_app, ["logout"])
        assert result.exit_code == 0
        out = json.loads(result.output)
        assert out["status"] == "not_logged_in"

    @patch("notion_cli.commands.auth.delete_credentials", return_value=True)
    @patch("notion_client.Client")
    @patch("notion_cli.commands.auth.load_credentials")
    def test_revoke_fails_still_deletes(
        self,
        mock_load: MagicMock,
        mock_client_cls: MagicMock,
        mock_delete: MagicMock,
        runner: CliRunner,
    ) -> None:
        mock_load.return_value = {"access_token": "ntn_tok"}
        mock_client_cls.return_value.oauth.revoke.side_effect = Exception("network error")
        result = runner.invoke(auth_app, ["logout"])
        assert result.exit_code == 0
        mock_delete.assert_called_once()


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------
class TestStatus:
    def test_env_var(self, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("NOTION_API_KEY", "secret_env")
        result = runner.invoke(auth_app, ["status"])
        assert result.exit_code == 0
        out = json.loads(result.output)
        assert out["source"] == "env"
        assert out["authenticated"] is True

    @patch("notion_cli.commands.auth.load_credentials")
    def test_oauth(
        self,
        mock_load: MagicMock,
        runner: CliRunner,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("NOTION_API_KEY", raising=False)
        mock_load.return_value = {
            "access_token": "ntn_tok",
            "workspace_name": "My WS",
            "workspace_id": "ws_1",
        }
        result = runner.invoke(auth_app, ["status"])
        assert result.exit_code == 0
        out = json.loads(result.output)
        assert out["source"] == "oauth"
        assert out["workspace"] == "My WS"

    @patch("notion_cli.commands.auth.load_credentials", return_value=None)
    def test_none(
        self, _mock_load: MagicMock, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("NOTION_API_KEY", raising=False)
        result = runner.invoke(auth_app, ["status"])
        assert result.exit_code == 0
        out = json.loads(result.output)
        assert out["source"] == "none"
        assert out["authenticated"] is False
