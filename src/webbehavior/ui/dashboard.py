"""Live test dashboard (PRD 8).

Renders a real-time panel from :class:`LiveTracker` snapshots while the
engine runs. Two rendering strategies keep terminals happy:

* TTY      -> ``rich.live.Live`` at a modest 4 fps (smooth, no flicker),
* non-TTY  -> one plain line per session (safe for pipes and CI).

Compact mode trims decoration on narrow phone screens.
"""

from __future__ import annotations

from typing import Optional

from rich.console import Console, Group, RenderableType
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.tree import Tree

from webbehavior.monitoring.tracker import STAGE_LABELS, LiveTracker
from webbehavior.ui.progress import text_bar
from webbehavior.ui.theme import SYMBOLS, ThemeManager
from webbehavior.utils.helpers import format_ms
from webbehavior.utils.system import compact_mode

__all__ = ["LiveDashboard", "render_snapshot"]

_STATE_STYLES = {
    "pending": "muted",
    "running": "running",
    "done": "success",
    "failed": "error",
    "info": "primary",
}

_STATE_SYMBOLS = {
    "pending": SYMBOLS.PENDING,
    "running": SYMBOLS.RUNNING,
    "done": SYMBOLS.SUCCESS,
    "failed": SYMBOLS.ERROR,
    "info": SYMBOLS.INFO,
}


def render_snapshot(snapshot: dict, manager: ThemeManager, width: Optional[int] = None) -> RenderableType:
    """Build the dashboard renderable from a tracker snapshot."""
    compact = compact_mode(width)
    body_lines: list[Text] = []

    body_lines.append(Text.assemble(
        ("Target", "muted"), ("       : " if not compact else ": "), (str(snapshot.get("target", "--")), "primary")
    ))
    done = int(snapshot.get("done", 0))
    total = int(snapshot.get("total", 0))
    body_lines.append(Text.assemble(
        ("Sessions", "muted"), ("     : ",), ("{:02d} / {:02d}".format(done, total), "accent bold")
    ))
    status = str(snapshot.get("status", ""))
    body_lines.append(Text.assemble(
        ("Status", "muted"), ("      : ",), (status, "success" if status == "FINISHED" else "running")
    ))
    body_lines.append(Text(""))

    # progress
    percent = int(snapshot.get("progress", 0))
    bar_width = 18 if compact else 26
    body_lines.append(Text.assemble(
        (text_bar(percent, width=bar_width), "success" if percent >= 100 else "running"),
        (" {:d}%".format(percent), "accent bold"),
    ))
    body_lines.append(Text(""))

    # current session tree
    session_tree = Tree(Text("Current Session", style="accent bold"), guide_style="muted")
    stages = snapshot.get("stages", {}) or {}
    for key, label in STAGE_LABELS.items():
        state, text = stages.get(key, ("pending", ""))
        symbol = _STATE_SYMBOLS.get(state, SYMBOLS.PENDING)
        style = _STATE_STYLES.get(state, "muted")
        parts = [(" ├─ " if key != "duration" else " └─ ", "muted"), (label.ljust(12 if not compact else 9), "primary"), (symbol + " ", style)]
        if text:
            parts.append((text, style))
        session_tree.add(Text.assemble(*parts))

    metrics_tree = Tree(Text("Metrics", style="accent bold"), guide_style="muted")
    metrics = snapshot.get("metrics", {}) or {}

    def metric_line(label: str, value: str) -> Text:
        return Text.assemble((" ├─ ", "muted"), (label.ljust(12 if not compact else 9), "primary"), (value, "accent"))

    metrics_tree.add(metric_line("Avg Latency", format_ms(metrics.get("avg_latency_ms"))))
    metrics_tree.add(metric_line("Success", str(metrics.get("successful", 0))))
    metrics_tree.add(Text.assemble((" └─ ", "muted"), ("Failed".ljust(12 if not compact else 9), "primary"), (str(metrics.get("failed", 0)), "accent")))

    message = str(snapshot.get("message", "") or "")
    header = " LIVE TEST "
    panel = Panel(
        Group(*body_lines, session_tree, Text(""), metrics_tree, Text(message, style="warning") if message else Text("")),
        title=header,
        border_style=manager.style("panel_border"),
        expand=False,
        highlight=False,
    )
    return panel


class LiveDashboard:
    """Context manager that displays the live dashboard during a run."""

    def __init__(
        self,
        console: Console,
        manager: ThemeManager,
        animations_enabled: bool = True,
    ) -> None:
        self.console = console
        self.manager = manager
        self.animations_enabled = animations_enabled
        self._live: Optional[Live] = None
        self._tracker: Optional[LiveTracker] = None
        self._interactive = console.is_terminal and animations_enabled

    # -- context manager ----------------------------------------------------

    def __enter__(self) -> "LiveDashboard":
        if self._interactive:
            self._live = Live(
                console=self.console,
                refresh_per_second=4,
                transient=False,
                get_renderable=self._renderable,
            )
            self._live.start()
        return self

    def __exit__(self, *exc_info: object) -> None:
        if self._live is not None:
            try:
                self._live.stop()
            except Exception:
                pass
            self._live = None

    # -- wiring ---------------------------------------------------------------

    def attach(self, tracker: LiveTracker) -> None:
        """Subscribe to tracker updates."""
        self._tracker = tracker
        tracker.subscribe(self.refresh)
        if not self._interactive:
            self.console.print(
                Text("→ starting test against {}".format(tracker.target), style="running")
            )

    def refresh(self) -> None:
        """Called by the tracker on every state change."""
        if self._live is not None and self._tracker is not None:
            self._live.update(self._renderable())
        elif self._tracker is not None:
            # Non-interactive (piped) output: one concise line per finished
            # session instead of a live panel.
            snapshot = self._tracker.snapshot()
            done = int(snapshot.get("done", 0))
            if done > 0 and done != getattr(self, "_last_reported", -1):
                self._last_reported = done
                metrics = snapshot.get("metrics", {}) or {}
                self.console.print(
                    Text.assemble(
                        ("{} session ".format(SYMBOLS.RUNNING), "running"),
                        ("{}/{}".format(done, snapshot.get("total", "?")), "primary"),
                        ("  ok=", "muted"), (str(metrics.get("successful", 0)), "success"),
                        ("  failed=", "muted"), (str(metrics.get("failed", 0)), "error"),
                        ("  avg=", "muted"), (format_ms(metrics.get("avg_latency_ms")), "accent"),
                    )
                )

    def _renderable(self) -> RenderableType:
        if self._tracker is None:
            return Text("waiting...")
        return render_snapshot(self._tracker.snapshot(), self.manager)
