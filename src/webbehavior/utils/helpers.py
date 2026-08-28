"""Small dependency-free helper functions."""

from __future__ import annotations

import re
import secrets
from typing import Iterable, List, Optional

_ERROR_ID_RE = re.compile(r"[^A-Z0-9]")


def new_error_id(prefix: str = "ERR") -> str:
    """Generate a short, user-shareable diagnostic error ID (e.g. ``ERR-7A21``)."""
    return "{}-{}".format(prefix, secrets.token_hex(2).upper())


def clamp(value: int, low: int, high: int) -> int:
    """Clamp *value* into the inclusive range [*low*, *high*]."""
    return max(low, min(high, value))


def format_ms(milliseconds: Optional[float]) -> str:
    """Format milliseconds for display, handling missing values gracefully."""
    if milliseconds is None:
        return "-- ms"
    if milliseconds >= 1000:
        return "{:.2f} s".format(milliseconds / 1000.0)
    return "{:.0f} ms".format(milliseconds)


def format_seconds(seconds: Optional[float]) -> str:
    """Format a duration in seconds for display."""
    if seconds is None:
        return "-- sec"
    return "{:.2f} sec".format(seconds)


def truncate_middle(text: str, max_length: int) -> str:
    """Shorten *text* to *max_length*, keeping head+tail with an ellipsis."""
    if len(text) <= max_length:
        return text
    if max_length <= 3:
        return text[:max_length]
    keep = max_length - 3
    head = keep // 2
    tail = keep - head
    return text[:head] + "..." + text[len(text) - tail:]


def word_wrap(text: str, width: int) -> List[str]:
    """Simple deterministic word-wrap used by compact terminal layouts."""
    lines: List[str] = []
    for paragraph in text.splitlines() or [""]:
        current = ""
        for word in paragraph.split():
            candidate = f"{current} {word}".strip()
            if len(candidate) <= width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        lines.append(current)
    return lines or [""]


def first_or_none(items: Iterable) -> Optional[object]:
    """Return the first item of *items* or ``None`` when empty."""
    for item in items:
        return item
    return None


def pad_center(text: str, width: int, fill: str = " ") -> str:
    """Center *text* in exactly *width* characters."""
    if len(text) >= width:
        return text[:width]
    total = width - len(text)
    left = total // 2
    return fill * left + text + fill * (total - left)
