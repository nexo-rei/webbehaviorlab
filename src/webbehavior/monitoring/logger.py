"""Safe local logging.

Rules enforced here (PRD sections 23/24):

* logs live under ``~/.webbehavior/logs/``,
* sensitive values (passwords, tokens, cookies, authorization headers,
  API keys) are scrubbed before anything is written,
* diagnostic files never contain the full URL query string (may hold
  tokens) - only scheme://host:port,
* rotating files keep disk usage bounded on phones.
"""

from __future__ import annotations

import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, List, Optional

from webbehavior.utils import storage
from webbehavior.utils.helpers import new_error_id
from webbehavior.utils.network import display_host, split_url

__all__ = ["get_logger", "scrub_sensitive", "safe_url_for_log", "write_diagnostic"]

_LOGGER = logging.getLogger("webbehavior")
_configured = False

SENSITIVE_KEYS = (
    "password",
    "passwd",
    "pwd",
    "token",
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "cookies",
    "sessionid",
    "session_id",
    "session_token",
    "secret",
    "credential",
    "credentials",
    "private_key",
)

_SECRET_VALUE_RE = re.compile(r"(?i)(bearer|basic)\s+[A-Za-z0-9._~+/=-]{8,}")
_REDACTED = "[REDACTED]"


def scrub_sensitive(value: Any) -> Any:
    """Deep-copy *value* replacing sensitive keys and inline secrets."""
    if isinstance(value, dict):
        cleaned: Dict[str, Any] = {}
        for key, item in value.items():
            key_str = str(key)
            if any(marker in key_str.lower() for marker in SENSITIVE_KEYS):
                cleaned[key_str] = _REDACTED
            else:
                cleaned[key_str] = scrub_sensitive(item)
        return cleaned
    if isinstance(value, (list, tuple)):
        return [scrub_sensitive(item) for item in value]
    if isinstance(value, str):
        return _SECRET_VALUE_RE.sub(lambda m: m.group(0).split()[0] + " " + _REDACTED, value)
    return value


def safe_url_for_log(url: str) -> str:
    """Reduce *url* to ``scheme://host[:port]/path`` (query removed)."""
    scheme, host, port, path = split_url(url)
    if not host:
        return "[invalid-url]"
    port_part = f":{port}" if port else ""
    return f"{scheme}://{host}{port_part}{path}"


class _ScrubbingFilter(logging.Filter):
    """Logging filter that scrubs sensitive fragments from messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            if record.args:
                record.msg = scrub_sensitive(record.msg)
                record.msg = record.msg % scrub_sensitive(record.args) if isinstance(record.msg, str) else record.msg
                record.args = None
            elif isinstance(record.msg, str):
                record.msg = scrub_sensitive(record.msg)
        except Exception:  # pragma: no cover - logging must never crash
            pass
        return True


def get_logger(name: str = "webbehavior") -> logging.Logger:
    """Return the configured application logger (idempotent)."""
    global _configured
    logger = _LOGGER if name in ("webbehavior",) else _LOGGER.getChild(name)
    if _configured:
        return logger
    try:
        storage.ensure_dirs()
        handler = RotatingFileHandler(
            str(storage.logs_dir() / "webbehavior.log"),
            maxBytes=512 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)-7s %(name)s - %(message)s"
        ))
        handler.addFilter(_ScrubbingFilter())
        _LOGGER.addHandler(handler)
        _LOGGER.setLevel(logging.INFO)
        _configured = True
    except Exception:  # pragma: no cover - degraded env (read-only home)
        _LOGGER.addHandler(logging.NullHandler())
        _configured = True
    return logger


def write_diagnostic(exc: BaseException, context: Optional[Dict[str, Any]] = None) -> str:
    """Write a sanitized diagnostic file for an unexpected exception.

    Returns the human-friendly error ID shown to the user.
    """
    error_id = new_error_id()
    logger = get_logger("diagnostics")
    try:
        storage.ensure_dirs()
        target_dir: Path = storage.diagnostics_dir()
        target_dir.mkdir(parents=True, exist_ok=True)
        import traceback

        tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        lines: List[str] = [
            f"Error ID: {error_id}",
            f"Exception: {type(exc).__name__}",
            f"Target(host-only): {display_host(str(scrub_sensitive(context or {}).get('url', '')))}",
            "",
            "Traceback (sanitized):",
            str(scrub_sensitive(tb)),
        ]
        (target_dir / f"{error_id}.log").write_text("\n".join(lines), encoding="utf-8")
    except Exception:  # pragma: no cover - never raise from diagnostics
        logger.exception("Failed to write diagnostic %s", error_id)
    logger.error("Unexpected error %s: %s", error_id, type(exc).__name__)
    return error_id
