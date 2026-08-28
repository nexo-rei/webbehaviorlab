"""Local storage layout for WebBehaviorLab.

All runtime data lives under ``~/.webbehavior`` (override with the
``WEBBEHAVIOR_HOME`` environment variable, which is also used by the test
suite to avoid touching a developer's real home directory):

    ~/.webbehavior/
        config/    user settings (settings.json)
        logs/      application + diagnostic logs
        reports/   generated JSON / TXT reports
        history.json  index of previous tests
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

APP_DIR_NAME = ".webbehavior"

_SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def app_dir() -> Path:
    """Return the application data directory (created lazily)."""
    override = os.environ.get("WEBBEHAVIOR_HOME")
    base = Path(override).expanduser() if override else Path.home() / APP_DIR_NAME
    return base


def ensure_dirs() -> Path:
    """Create the full storage directory tree and return the app dir."""
    base = app_dir()
    for sub in (base, config_dir(), logs_dir(), reports_dir()):
        sub.mkdir(parents=True, exist_ok=True)
    return base


def config_dir() -> Path:
    return app_dir() / "config"


def logs_dir() -> Path:
    return app_dir() / "logs"


def reports_dir() -> Path:
    return app_dir() / "reports"


def diagnostics_dir() -> Path:
    return logs_dir() / "diagnostics"


def history_path() -> Path:
    return app_dir() / "history.json"


def safe_filename(name: str) -> str:
    """Sanitize *name* into a filesystem-safe filename.

    Prevents path traversal (``../``), shell-unfriendly characters and
    reserved names from ever reaching the filesystem.
    """
    cleaned = _SAFE_FILENAME_RE.sub("-", name.strip()).strip(".-")
    return cleaned[:120] or "untitled"


def write_json(path: Union[str, Path], data: Any) -> Path:
    """Atomically write *data* as pretty JSON to *path*."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(target.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        os.replace(tmp_name, target)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
    return target


def read_json(path: Union[str, Path], default: Any = None) -> Any:
    """Read JSON from *path*, returning *default* when missing/corrupt."""
    target = Path(path)
    if not target.exists():
        return default
    try:
        with target.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Test history index
# ---------------------------------------------------------------------------

def load_history() -> List[Dict[str, Any]]:
    """Return the list of previous test entries (newest last)."""
    history = read_json(history_path(), default=[])
    return history if isinstance(history, list) else []


def append_history(entry: Dict[str, Any]) -> None:
    """Append *entry* to the persistent history index."""
    history = load_history()
    history.append(entry)
    # Keep the index bounded; the full reports remain on disk.
    write_json(history_path(), history[-500:])


def clear_history() -> None:
    """Remove the history index file."""
    try:
        history_path().unlink(missing_ok=True)
    except OSError:
        pass


def history_report_path(entry: Dict[str, Any], fmt: str = "json") -> Optional[Path]:
    """Return the report file referenced by a history *entry*, if present."""
    files = entry.get("report_files") or {}
    name = files.get(fmt)
    if not name:
        return None
    candidate = reports_dir() / name
    return candidate if candidate.exists() else None


def timestamp_dirname(now: Optional[datetime] = None) -> str:
    """A sortable timestamp string usable in filenames (no colons)."""
    stamp = now or datetime.now()
    return stamp.strftime("%Y%m%d-%H%M%S")
