"""Thread-safe live state tracking for the dashboard.

The engine publishes state changes here; the dashboard subscribes and
renders. Keeping them decoupled means the UI can be disabled (non-TTY,
piped output) without touching the engine.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Callable, Dict, List

from webbehavior.utils.helpers import clamp

__all__ = ["Stage", "LiveTracker"]

STAGE_LABELS = {
    "browser": "Browser",
    "page_load": "Page Load",
    "response": "Response",
    "actions": "Test Actions",
    "events": "Events",
    "duration": "Duration",
}


@dataclass
class Stage:
    """One line of the 'Current Session' dashboard section."""

    key: str
    state: str = "pending"  # pending | running | done | failed | info
    text: str = ""

    @property
    def symbol(self) -> str:
        return {
            "pending": "○",
            "running": "→",
            "done": "✓",
            "failed": "✗",
            "info": "•",
        }[self.state]


class LiveTracker:
    """Holds the live snapshot of a test run (thread-safe)."""

    def __init__(self, total_sessions: int, target: str) -> None:
        self.total_sessions = max(total_sessions, 1)
        self.target = target
        self.sessions_done = 0
        self.status = "STARTING"  # STARTING | RUNNING | FINISHED | ABORTED
        self.stages: Dict[str, Stage] = {}
        self.metrics_snapshot: Dict[str, object] = {}
        self.message: str = ""
        self._lock = threading.Lock()
        self._subscribers: List[Callable[[], None]] = []

    # -- subscriptions ----------------------------------------------------

    def subscribe(self, callback: Callable[[], None]) -> None:
        """Register a callback fired on every state change (dashboard)."""
        self._subscribers.append(callback)

    def _publish(self) -> None:
        for callback in list(self._subscribers):
            try:
                callback()
            except Exception:
                pass

    # -- engine API ---------------------------------------------------------

    def set_status(self, status: str, message: str = "") -> None:
        with self._lock:
            self.status = status
            self.message = message
        self._publish()

    def begin_session(self, index: int) -> None:
        with self._lock:
            self.status = "RUNNING"
            self.current_index = index  # type: ignore[attr-defined]
            self.stages = {key: Stage(key) for key in STAGE_LABELS}
        self._publish()

    def stage(self, key: str, state: str = "done", text: str = "") -> None:
        with self._lock:
            self.stages[key] = Stage(key, state, text)
        self._publish()

    def update_metrics(self, snapshot: Dict[str, object]) -> None:
        with self._lock:
            self.metrics_snapshot = dict(snapshot)
        self._publish()

    def end_session(self) -> None:
        with self._lock:
            self.sessions_done = clamp(getattr(self, "sessions_done", 0) + 1, 0, self.total_sessions)
            for stage in self.stages.values():
                if stage.state in ("pending", "running"):
                    stage.state = "done"
        self._publish()

    # -- read helpers -----------------------------------------------------------

    @property
    def progress_percent(self) -> int:
        done = getattr(self, "sessions_done", 0)
        return int(100.0 * done / self.total_sessions)

    @property
    def current_index(self) -> int:
        return getattr(self, "_current_index", 1)

    @current_index.setter
    def current_index(self, value: int) -> None:
        self._current_index = value

    def snapshot(self) -> Dict[str, object]:
        """Immutable-ish snapshot for renderers."""
        with self._lock:
            return {
                "target": self.target,
                "total": self.total_sessions,
                "done": self.sessions_done,
                "status": self.status,
                "current_index": self.current_index,
                "stages": {k: (s.state, s.text) for k, s in self.stages.items()},
                "metrics": dict(self.metrics_snapshot),
                "message": self.message,
                "progress": self.progress_percent,
            }
