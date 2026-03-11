import json
from pathlib import Path


def _credentials_path() -> Path:
    return Path.home() / ".config" / "notion-cli" / "credentials.json"


def load_credentials() -> dict[str, str] | None:
    """Read stored OAuth credentials, or None if absent/corrupt."""
    try:
        return json.loads(_credentials_path().read_text())
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def save_credentials(data: dict[str, str]) -> None:
    """Write credentials to disk with 0600 permissions."""
    path = _credentials_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))
    path.chmod(0o600)


def delete_credentials() -> bool:
    """Remove credentials file. Returns True if it existed."""
    try:
        _credentials_path().unlink()
        return True
    except FileNotFoundError:
        return False
