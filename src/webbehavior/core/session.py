"""Session lifecycle model: status, timing and per-session results."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class SessionStatus(str, Enum):
    """Lifecycle states of a single test session."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"

    @property
    def symbol(self) -> str:
        return {
            SessionStatus.PENDING: "○",
            SessionStatus.RUNNING: "→",
            SessionStatus.SUCCESS: "✓",
            SessionStatus.FAILED: "✗",
        }[self]


@dataclass
class SessionResult:
    """Everything safely collected during one browser session.

    Deliberately excludes cookies, headers, tokens and page content - only
    timing/counting data needed for education and reporting is stored.
    """

    index: int
    target: str
    status: SessionStatus = SessionStatus.PENDING
    http_status: Optional[int] = None
    response_time_ms: Optional[float] = None
    page_load_ms: Optional[float] = None
    duration_s: Optional[float] = None
    actions_done: int = 0
    actions_total: int = 0
    events_count: int = 0
    error: Optional[str] = None
    started_at: Optional[float] = None
    finished_at: Optional[float] = None

    @property
    def ok(self) -> bool:
        return self.status is SessionStatus.SUCCESS

    @property
    def http_label(self) -> str:
        if self.http_status is None:
            return "--"
        label = "{} {}".format(self.http_status, "OK" if self.http_status < 400 else "ERR")
        return label


class SessionTimer:
    """Context-friendly wall-clock timer for one session."""

    def __init__(self) -> None:
        self._start: Optional[float] = None
        self.elapsed: Optional[float] = None

    def start(self) -> "SessionTimer":
        self._start = time.perf_counter()
        return self

    def stop(self) -> Optional[float]:
        if self._start is not None:
            self.elapsed = time.perf_counter() - self._start
        return self.elapsed

    def __enter__(self) -> "SessionTimer":
        return self.start()

    def __exit__(self, *exc_info: object) -> None:
        self.stop()
