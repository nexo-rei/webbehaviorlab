"""Application banner and title panels."""

from __future__ import annotations

from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from webbehavior.ui.theme import SYMBOLS, ThemeManager
from webbehavior.utils.system import compact_mode

__all__ = ["render_banner", "print_banner", "section_title"]

_APP_TITLE = "W E B B E H A V I O R   L A B"
_APP_SUBTITLE = "T E R M U X   E D I T I O N"
_APP_TAGLINE = "Educational Testing Environment"


def render_banner(manager: ThemeManager, width: Optional[int] = None) -> Panel:
    """Build the startup banner as a rich Panel."""
    compact = compact_mode(width)
    title = "WEBBEHAVIOR LAB" if compact else _APP_TITLE
    lines = [Text(title, style="bold " + manager.style("banner"))]
    if not compact:
        lines.append(Text(_APP_SUBTITLE, style=manager.style("primary")))
        lines.append(Text(""))
    lines.append(Text(_APP_TAGLINE, style=manager.style("muted")))
    body = Text("\n").join(lines)
    return Panel(
        body,
        border_style=manager.style("panel_border"),
        expand=False,
        padding=(0, 4),
    )


def print_banner(console: Console, manager: ThemeManager) -> None:
    """Print the banner centered on the terminal."""
    console.print()
    console.print(render_banner(manager), justify="center" if not compact_mode() else "left")
    console.print()


def section_title(console: Console, manager: ThemeManager, text: str) -> None:
    """Print a compact section header."""
    console.print()
    console.print(
        Text("{} {}".format(SYMBOLS.BULLET, text.upper()), style="accent bold"),
    )
