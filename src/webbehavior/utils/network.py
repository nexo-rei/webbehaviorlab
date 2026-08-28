"""Network/URL helpers (pure stdlib, no sockets opened here)."""

from __future__ import annotations

import ipaddress
from typing import Optional, Tuple
from urllib.parse import urlsplit

LOCAL_HOSTNAMES = {"localhost", "ip6-localhost", "ip6-loopback"}
LOCAL_SUFFIXES = (".local", ".localhost", ".test", ".example", ".invalid")


def split_url(url: str) -> Tuple[str, str, Optional[int], str]:
    """Split *url* into ``(scheme, host, port, path)``.

    Returns empty strings / ``None`` for missing pieces. Never raises for
    ordinary string input.
    """
    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return "", "", None, ""
    host = parts.hostname or ""
    try:
        port = parts.port
    except ValueError:
        port = None
    path = parts.path or "/"
    return parts.scheme.lower(), host, port, path


def host_of(url: str) -> str:
    """Extract the lowercase hostname from *url* ("" when absent)."""
    return split_url(url)[1]


def default_port(scheme: str) -> Optional[int]:
    return {"http": 80, "https": 443}.get(scheme.lower())


def display_host(url: str) -> str:
    """Host[:port] label for dashboards (omits default ports)."""
    scheme, host, port, _ = split_url(url)
    if not host:
        return url
    if port and port != default_port(scheme):
        return f"{host}:{port}"
    return host


def is_local_target(url: str) -> bool:
    """True when *url* points at the local machine or a local test domain.

    Recognizes ``localhost``/``127.0.0.1``/``::1``, RFC1918/loopback/link-local
    IPs, ``*.local``/``*.test`` style dev suffixes and ``file-less`` local names.
    """
    scheme, host, _port, _path = split_url(url)
    if not host:
        return False
    lowered = host.lower().rstrip(".")
    if lowered in LOCAL_HOSTNAMES or lowered.endswith(LOCAL_SUFFIXES):
        return True
    try:
        ip = ipaddress.ip_address(lowered)
    except ValueError:
        return False
    return ip.is_loopback or ip.is_private or ip.is_link_local


def has_userinfo(url: str) -> bool:
    """True when *url* embeds ``user:pass@`` credentials (rejected by policy)."""
    try:
        return urlsplit(url.strip()).username is not None
    except ValueError:
        return False
