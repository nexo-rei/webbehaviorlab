"""Table builders (history, reports, metrics) with compact-mode support."""

from __future__ import annotations

from typing import Dict, List, Sequence

from rich.table import Table

from webbehavior.ui.theme import SYMBOLS, ThemeManager
from webbehavior.utils.helpers import truncate_middle

__all__ = ["history_table", "status_badge", "report_table", "menu_table"]


def status_badge(status: str) -> str:
    """Map PASS/PARTIAL/FAIL to symbol + text (color-free meaning)."""
    return {
        "PASS": "{} PASS".format(SYMBOLS.SUCCESS),
        "PARTIAL": "{} PARTIAL".format(SYMBOLS.WARNING),
        "FAIL": "{} FAIL".format(SYMBOLS.ERROR),
        "RUNNING": "{} RUNNING".format(SYMBOLS.RUNNING),
    }.get(status.upper(), status)


def history_table(entries: List[Dict], manager: ThemeManager, compact: bool = False) -> Table:
    """Build the Test History table (PRD 11).

    In compact mode the table drops to ID / target / status so it fits a
    narrow phone screen.
    """
    table = Table(
        title="Test History" if not compact else None,
        border_style=manager.style("panel_border"),
        expand=True,
        pad_edge=False,
    )
    table.add_column("ID", style="accent bold", no_wrap=True)
    table.add_column("Target", style="primary", overflow="ellipsis")
    if not compact:
        table.add_column("Sessions", justify="center")
        table.add_column("Status", justify="center")
        table.add_column("Date", style="muted")
    else:
        table.add_column("St.", justify="center")

    for entry in reversed(entries[-25:]):
        target = str(entry.get("target", ""))
        shown = truncate_middle(target, 26) if compact else truncate_middle(target, 40)
        if compact:
            table.add_row(
                str(entry.get("test_id", "--")),
                shown,
                status_badge(str(entry.get("status", "")))[:2],
            )
        else:
            table.add_row(
                str(entry.get("test_id", "--")),
                shown,
                "{}/{}".format(int(entry.get("success", 0)), int(entry.get("sessions", 0))),
                status_badge(str(entry.get("status", ""))),
                str(entry.get("finished_at", "--"))[:16],
            )
    return table


def report_table(reports: Sequence[Dict], manager: ThemeManager) -> Table:
    """Table of exported report files."""
    table = Table(border_style=manager.style("panel_border"), expand=True)
    table.add_column("Test ID", style="accent bold")
    table.add_column("Format", justify="center")
    table.add_column("File", style="primary", overflow="fold")
    for item in reports:
        table.add_row(str(item.get("test_id", "--")), str(item.get("format", "--")), str(item.get("file", "--")))
    return table


def menu_table(options: Sequence[Dict[str, str]], manager: ThemeManager) -> Table:
    """Simple two-column menu used by submenus (keyboard friendly)."""
    table = Table(show_header=False, box=None, expand=True, pad_edge=False)
    table.add_column("key", style="accent bold", justify="right", width=4)
    table.add_column("label", style="primary")
    for option in options:
        table.add_row(option["key"], option["label"])
    return table
