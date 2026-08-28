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
    # Resolve theme keys to concrete styles so the panel renders correctly
    # on any console, themed or not.
    c = {k: manager.style(k) for k in
         ("primary", "accent", "success", "error", "running", "muted", "warning", "panel_border")}
    label_w = 8   # header labels ("Sessions")
    stage_w = 12  # stage labels ("Test Actions")
    pad = " "
    body: list[Text] = []

    def field(label: str, value: str, value_style: str) -> None:
        body.append(Text.assemble(
            (label.ljust(label_w), c["muted"]), (": ", c["muted"]), (value, value_style)
        ))

    field("Target", str(snapshot.get("target", "--")), c["primary"])
    done = int(snapshot.get("done", 0))
    total = int(snapshot.get("total", 0))
    field("Sessions", "{:02d} / {:02d}".format(done, total), "bold " + c["accent"])
    status = str(snapshot.get("status", ""))
    field("Status", status, c["success"] if status == "FINISHED" else c["running"])
    body.append(Text(""))

    # progress
    percent = int(snapshot.get("progress", 0))
    bar_width = 18 if compact else 26
    body.append(Text.assemble(
        (text_bar(percent, width=bar_width), c["success"] if percent >= 100 else c["running"]),
        (" {:d}%".format(percent), "bold " + c["accent"]),
    ))
    body.append(Text(""))

    def branch(is_last: bool) -> str:
        return " └─ " if is_last else " ├─ "

    def stage_line(label: str, state: str, text: str, is_last: bool = False) -> None:
        style = {"pending": c["muted"], "running": c["running"], "done": c["success"],
                 "failed": c["error"], "info": c["primary"]}.get(state, c["muted"])
        symbol = _STATE_SYMBOLS.get(state, SYMBOLS.PENDING)
        parts = [
            (branch(is_last), c["muted"]),
            (label.ljust(stage_w) + pad, c["primary"]),
            (symbol, style),
        ]
        if text:
            parts.append((" " + text, style))
        body.append(Text.assemble(*parts))

    body.append(Text("Current Session", style="bold " + c["accent"]))
    stages = snapshot.get("stages", {}) or {}
    keys = list(STAGE_LABELS.keys())
    for pos, key in enumerate(keys):
        state, text = stages.get(key, ("pending", ""))
        stage_line(STAGE_LABELS[key], state, text, is_last=(pos == len(keys) - 1))
    body.append(Text(""))

    def metric_line(label: str, value: str, is_last: bool = False) -> None:
        body.append(Text.assemble(
            (branch(is_last), c["muted"]),
            (label.ljust(stage_w) + pad, c["primary"]),
            (value, c["accent"]),
        ))

    metrics = snapshot.get("metrics", {}) or {}
    body.append(Text("Metrics", style="bold " + c["accent"]))
    metric_line("Avg Latency", format_ms(metrics.get("avg_latency_ms")))
    metric_line("Success", str(metrics.get("successful", 0)))
    metric_line("Failed", str(metrics.get("failed", 0)), is_last=True)

    message = str(snapshot.get("message", "") or "")
    panel = Panel(
        Group(*body, Text(message, style=c["warning"]) if message else Text("")),
        title=" LIVE TEST ",
        border_style=c["panel_border"],
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
