"""Progress bar helpers (rich)."""

from __future__ import annotations

from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)

from webbehavior.ui.theme import SYMBOLS

__all__ = ["make_progress", "text_bar"]


def make_progress(animations_enabled: bool = True, compact: bool = False) -> Progress:
    """Build the standard Progress used across the app."""
    columns = []
    if animations_enabled:
        columns.append(SpinnerColumn(style="running"))
    columns.append(TextColumn("[progress.description]{task.description}", style="primary"))
    if not compact:
        columns.append(BarColumn(bar_width=None, style="running", complete_style="success"))
    columns.append(TextColumn("[progress.percentage]{task.percentage:>3.0f}%"))
    if not compact:
        columns.append(TimeElapsedColumn())
    return Progress(*columns, transient=False)


def text_bar(percent: int, width: int = 24, done: str = None, todo: str = None) -> str:
    """Render an inline unicode bar (used inside the live dashboard)."""
    done_char = done or SYMBOLS.PROGRESS_DONE
    todo_char = todo or SYMBOLS.PROGRESS_TODO
    filled = int(round(width * max(0, min(percent, 100)) / 100.0))
    return done_char * filled + todo_char * (width - filled)
