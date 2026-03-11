import os
import secrets
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Annotated
from urllib.parse import parse_qs, urlparse

import typer

from notion_cli.credentials import delete_credentials, load_credentials, save_credentials
from notion_cli.output import ExitCode, format_error, format_json

CLIENT_ID = "320d872b-594c-81ce-bd3e-003786f0191c"

try:
    from notion_cli._oauth_secret import CLIENT_SECRET  # ty: ignore[unresolved-import]
except ImportError:
    CLIENT_SECRET = os.environ.get("NOTION_OAUTH_CLIENT_SECRET", "")

auth_app = typer.Typer(
    name="auth",
    help="Authenticate with Notion via OAuth or check auth status.",
    no_args_is_help=True,
)


class _OAuthCallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        self.server.callback_params = parse_qs(parsed.query)
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(
            b"<html><body><h1>Authentication successful!</h1>"
            b"<p>You can close this tab.</p></body></html>"
        )

    def log_message(self, format: str, *args: object) -> None:  # noqa: ANN002
        pass  # suppress server logs


@auth_app.command()
def login(
    port: Annotated[int, typer.Option("--port", help="Local port for OAuth callback.")] = 9876,
) -> None:
    """Authenticate with Notion via OAuth browser flow.

    Opens a browser for Notion authorization. When prompted, select pages
    to share with the integration (use "Select all" for full workspace access).
    """
    if port < 1 or port > 65535:
        sys.stderr.write(
            format_error("invalid_port", f"Port must be between 1 and 65535, got {port}.") + "\n"
        )
        raise SystemExit(ExitCode.BAD_ARGS)

    state = secrets.token_urlsafe(16)
    redirect_uri = f"http://localhost:{port}/callback"
    auth_url = (
        f"https://api.notion.com/v1/oauth/authorize"
        f"?client_id={CLIENT_ID}"
        f"&response_type=code"
        f"&redirect_uri={redirect_uri}"
        f"&state={state}"
        f"&owner=user"
    )

    typer.echo("Opening browser for Notion authentication...")
    typer.echo("Tip: select all pages when prompted for full workspace access.")
    typer.echo(f"If browser doesn't open, visit: {auth_url}")

    try:
        webbrowser.open(auth_url)
    except Exception:
        pass  # URL already printed as fallback

    try:
        server = HTTPServer(("localhost", port), _OAuthCallbackHandler)
    except OSError:
        sys.stderr.write(
            format_error(
                "port_in_use",
                f"Port {port} is already in use.",
                suggestion=f"Try --port {port + 1}",
            )
            + "\n"
        )
        raise SystemExit(ExitCode.ERROR)

    server.timeout = 120
    server.callback_params = {}
    try:
        server.handle_request()
    finally:
        server.server_close()

    params = server.callback_params

    if not params:
        sys.stderr.write(
            format_error("auth_timeout", "Authentication timed out after 120 seconds.") + "\n"
        )
        raise SystemExit(ExitCode.ERROR)

    if "error" in params:
        sys.stderr.write(
            format_error("auth_denied", f"Authentication denied: {params['error'][0]}") + "\n"
        )
        raise SystemExit(ExitCode.ERROR)

    if params.get("state", [None])[0] != state:
        sys.stderr.write(
            format_error("state_mismatch", "OAuth state mismatch — possible CSRF attack.") + "\n"
        )
        raise SystemExit(ExitCode.ERROR)

    code = params.get("code", [None])[0]
    if not code:
        sys.stderr.write(format_error("missing_code", "No authorization code received.") + "\n")
        raise SystemExit(ExitCode.ERROR)

    from notion_client import Client

    client = Client(auth="")
    response = client.oauth.token(
        CLIENT_ID,
        CLIENT_SECRET,
        grant_type="authorization_code",
        code=code,
        redirect_uri=redirect_uri,
    )

    access_token = response.get("access_token")
    if not access_token:
        sys.stderr.write(
            format_error("auth_failed", "OAuth token exchange failed — no access_token received.")
            + "\n"
        )
        raise SystemExit(ExitCode.ERROR)

    cred_data: dict[str, str] = {
        "access_token": access_token,
        "workspace_id": response.get("workspace_id", ""),
        "workspace_name": response.get("workspace_name", ""),
        "bot_id": response.get("bot_id", ""),
    }
    if response.get("refresh_token"):
        cred_data["refresh_token"] = response["refresh_token"]

    save_credentials(cred_data)
    typer.echo(format_json({"status": "authenticated", **cred_data}))


@auth_app.command()
def logout() -> None:
    """Revoke OAuth token and delete stored credentials."""
    creds = load_credentials()
    if not creds:
        typer.echo(format_json({"status": "not_logged_in"}))
        return

    try:
        from notion_client import Client

        client = Client(auth="")
        client.oauth.revoke(
            CLIENT_ID,
            CLIENT_SECRET,
            token=creds["access_token"],
        )
    except Exception:
        pass  # best-effort revoke; still delete local file

    delete_credentials()
    typer.echo(format_json({"status": "logged_out"}))


@auth_app.command()
def status() -> None:
    """Show current authentication status."""
    env_token = os.environ.get("NOTION_API_KEY")
    if env_token:
        typer.echo(format_json({"source": "env", "authenticated": True}))
        return

    creds = load_credentials()
    if creds and creds.get("access_token"):
        typer.echo(
            format_json(
                {
                    "source": "oauth",
                    "authenticated": True,
                    "workspace": creds.get("workspace_name", ""),
                    "workspace_id": creds.get("workspace_id", ""),
                }
            )
        )
        return

    typer.echo(format_json({"source": "none", "authenticated": False}))
