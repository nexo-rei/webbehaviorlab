"""Themes, colors and consistent status symbols.

Accessibility (PRD 32): every state is communicated by a *symbol* as well
as a color, so the UI never depends on color alone. The ``high-contrast``
and ``minimal`` themes further reduce decoration.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from rich.theme import Theme

__all__ = ["SYMBOLS", "ThemeManager", "build_rich_theme"]


class SYMBOLS:  # noqa: N801 - constant-style container
    """Consistent status glyphs used across the entire UI."""

    SUCCESS = "✓"
    ERROR = "✗"
    WARNING = "⚠"
    RUNNING = "→"
    PENDING = "○"
    INFO = "•"
    BULLET = "›"
    PROGRESS_DONE = "━"
    PROGRESS_TODO = "░"


@dataclass
class ThemeManager:
    """Named color palettes for panels and states."""

    name: str = "default"

    PALETTES: Dict[str, Dict[str, str]] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.PALETTES is None:
            self.PALETTES = {
                "default": {
                    "primary": "cyan",
                    "accent": "bright_cyan",
                    "success": "green",
                    "error": "bright_red",
                    "warning": "yellow",
                    "running": "bright_blue",
                    "muted": "grey62",
                    "panel_border": "cyan",
                    "banner": "bright_cyan",
                },
                "high-contrast": {
                    "primary": "bright_white",
                    "accent": "bright_white",
                    "success": "bright_green",
                    "error": "bright_red",
                    "warning": "bright_yellow",
                    "running": "bright_white",
                    "muted": "white",
                    "panel_border": "bright_white",
                    "banner": "bright_white",
                },
                "minimal": {
                    "primary": "white",
                    "accent": "white",
                    "success": "white",
                    "error": "bright_red",
                    "warning": "white",
                    "running": "white",
                    "muted": "grey50",
                    "panel_border": "white",
                    "banner": "white",
                },
            }
        if self.name not in self.PALETTES:
            self.name = "default"

    @property
    def colors(self) -> Dict[str, str]:
        return self.PALETTES[self.name]

    def style(self, key: str) -> str:
        return self.colors.get(key, "white")

    def success(self, text: str) -> str:
        return "{} {}".format(SYMBOLS.SUCCESS, text)

    def error(self, text: str) -> str:
        return "{} {}".format(SYMBOLS.ERROR, text)

    def warning(self, text: str) -> str:
        return "{} {}".format(SYMBOLS.WARNING, text)

    def running(self, text: str) -> str:
        return "{} {}".format(SYMBOLS.RUNNING, text)


def build_rich_theme(manager: ThemeManager) -> Theme:
    """Translate a ThemeManager palette into a rich ``Theme``.

    Rich only resolves theme keys for *whole* style strings, so the
    compound styles used across the UI (``accent bold`` etc.) get their
    own theme entries.
    """
    c = manager.colors
    return Theme(
        {
            "primary": c["primary"],
            "accent": c["accent"],
            "accent bold": "bold " + c["accent"],
            "success": c["success"],
            "error": c["error"],
            "warning": c["warning"],
            "running": c["running"],
            "muted": c["muted"],
            "panel.border": c["panel_border"],
            "banner": c["banner"],
            "banner bold": "bold " + c["banner"],
            "info": c["primary"],
        }
    )
