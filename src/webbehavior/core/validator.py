"""Target validation and authorization checks.

Every test starts here. The validator ensures that:

* the URL is well formed,
* only ``http``/``https`` targets are accepted (no ``file:``, ``ftp:``,
  ``javascript:`` or other schemes),
* URLs do not embed credentials (``user:pass@host``),
* the user has explicitly confirmed they are authorized to test the target.

The validator never opens network connections - it is pure parsing.
"""

from __future__ import annotations
from typing import Optional
from urllib.parse import urlsplit

from webbehavior.utils.network import (
    display_host,
    has_userinfo,
    is_local_target,
    split_url,
)

__all__ = [
    "ALLOWED_SCHEMES",
    "TARGET_LABEL",
    "ValidationResult",
    "TargetInfo",
    "normalize_url",
    "validate_url",
    "target_info",
    "is_authorized_scope",
]

ALLOWED_SCHEMES = ("http", "https")
TARGET_LABEL = "AUTHORIZED TEST TARGET"
MAX_URL_LENGTH = 2048


class ValidationResult:
    """Outcome of validating a raw URL string."""

    def __init__(self, ok: bool, url: str = "", reason: str = "", hint: str = "") -> None:
        self.ok = ok
        self.url = url
        self.reason = reason
        self.hint = hint

    def __bool__(self) -> bool:  # allows ``if result:``
        return self.ok

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return "ValidationResult(ok={!r}, url={!r}, reason={!r})".format(self.ok, self.url, self.reason)


class TargetInfo:
    """Normalized summary of a validated target."""

    def __init__(self, url: str) -> None:
        self.url = url
        self.scheme, self.host, self.port, self.path = split_url(url)
        self.is_local = is_local_target(url)

    @property
    def display(self) -> str:
        return display_host(self.url)

    @property
    def label(self) -> str:
        return TARGET_LABEL


_INVALID = "Please enter a valid HTTP/HTTPS URL."


def normalize_url(raw: str) -> Optional[str]:
    """Apply beginner-friendly normalization to *raw* user input.

    * trims whitespace,
    * adds a scheme (``https://`` for names, ``http://`` for local addresses)
    * adds a trailing ``/`` when the path is empty.

    Returns ``None`` when the input is empty or not URL-like.
    """
    text = (raw or "").strip()
    if not text or len(text) > MAX_URL_LENGTH:
        return None
    if "://" not in text:
        candidate = text.split("/", 1)[0]
        if "." not in candidate and ":" not in candidate and candidate.lower() != "localhost":
            return None
        scheme = "http" if is_local_target("http://" + candidate) else "https"
        text = f"{scheme}://{text}"
    parts = urlsplit(text)
    if not parts.scheme or not parts.netloc:
        return None
    if not parts.path:
        text += "/"
    return text


def validate_url(raw: str) -> ValidationResult:
    """Validate a raw URL string.

    Returns a :class:`ValidationResult`; on failure ``reason`` holds the
    headline (e.g. ``Invalid URL``) and ``hint`` explains what to do next.
    """
    text = (raw or "").strip()
    if not text:
        return ValidationResult(False, "", "Empty input", _INVALID)

    normalized = normalize_url(text)
    if normalized is None:
        return ValidationResult(False, text, "Invalid URL", _INVALID)

    scheme, host, _port, _path = split_url(normalized)
    if scheme not in ALLOWED_SCHEMES:
        return ValidationResult(
            False,
            normalized,
            "Unsupported protocol",
            "Only HTTP and HTTPS URLs are supported.\nExample: http://127.0.0.1:8000",
        )
    if not host:
        return ValidationResult(False, normalized, "Invalid URL", _INVALID + "\nThe host name is missing.")
    if "." not in host and host.lower() not in ("localhost",) and ":" not in host:
        return ValidationResult(
            False, normalized, "Invalid URL", _INVALID + "\nExample: http://127.0.0.1:8000"
        )
    if has_userinfo(normalized):
        return ValidationResult(
            False,
            normalized,
            "Credentials rejected",
            "URLs with user:password@ are not allowed for safety.",
        )
    if any(ch.isspace() for ch in normalized):
        return ValidationResult(False, normalized, "Invalid URL", _INVALID)

    return ValidationResult(True, normalized)


def target_info(url: str) -> Optional[TargetInfo]:
    """Return :class:`TargetInfo` for a *validated* URL, else ``None``."""
    result = validate_url(url)
    return TargetInfo(result.url) if result.ok else None


def is_authorized_scope(url: str) -> bool:
    """Heuristic: is *url* clearly a local/development target?

    Local targets are treated as in-scope by default; remote targets always
    require the explicit authorization confirmation from the user.
    """
    return is_local_target(url)


def redact_url_for_display(url: str) -> str:
    """URL display form with any query string truncated (may hold tokens)."""
    parts = urlsplit(url)
    if parts.query:
        return parts._replace(query="…").geturl()
    return url

