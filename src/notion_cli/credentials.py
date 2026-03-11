import json
import os
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
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, json.dumps(data).encode())
    finally:
        os.close(fd)


def delete_credentials() -> bool:
    """Remove credentials file. Returns True if it existed."""
    try:
        _credentials_path().unlink()
        return True
    except (FileNotFoundError, PermissionError):
        return False
