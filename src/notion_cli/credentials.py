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
    """Write credentials to disk with 0600 permissions (atomic via temp + rename)."""
    path = _credentials_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".tmp")
    fd = os.open(tmp_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, json.dumps(data).encode())
    finally:
        os.close(fd)
    os.chmod(tmp_path, 0o600)
    try:
        tmp_path.rename(path)
    except OSError:
        tmp_path.unlink(missing_ok=True)
        raise


def delete_credentials() -> bool:
    """Remove credentials file. Returns True if it existed."""
    try:
        _credentials_path().unlink()
        return True
    except (FileNotFoundError, PermissionError):
        return False
