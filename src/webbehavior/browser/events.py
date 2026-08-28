"""Safe browser event recording.

Only anonymous *counts* of standard browser events are recorded (loads,
console messages, requests, responses, page errors). No request headers, no
cookies, no response bodies and no page content are ever captured.
"""

from __future__ import annotations

import time
from collections import Counter
from typing import Dict, List

__all__ = ["EventRecorder", "SAFE_EVENT_TYPES"]

SAFE_EVENT_TYPES = (
    "domcontentloaded",
    "load",
    "console",
    "request",
    "response",
    "pageerror",
    "framenavigated",
)


class EventRecorder:
    """Attach to a Playwright page and count safe browser events."""

    def __init__(self) -> None:
        self.counts: Counter[str] = Counter()
        self.timeline: List[Dict[str, object]] = []
        self._attached = False

    # -- attachment -------------------------------------------------------

    def attach(self, page) -> None:
        """Hook the safe event handlers onto *page* (idempotent)."""
        if self._attached:
            return
        started = time.perf_counter()

        def record(event: str, detail: str = "") -> None:
            self.counts[event] += 1
            self.timeline.append(
                {"event": event, "at_ms": round((time.perf_counter() - started) * 1000), "detail": detail}
            )

        page.on("domcontentloaded", lambda _page: record("domcontentloaded"))
        page.on("load", lambda _page: record("load"))
        page.on("console", lambda msg: record("console", msg.type))
        page.on("request", lambda _req: record("request"))
        page.on("response", lambda _resp: record("response"))
        page.on("pageerror", lambda _err: record("pageerror"))
        page.on("framenavigated", lambda frame: record("framenavigated", frame.name or "main"))
        self._attached = True

    # -- results ----------------------------------------------------------

    @property
    def total(self) -> int:
        """Total number of recorded events."""
        return sum(self.counts.values())

    def snapshot(self) -> Dict[str, object]:
        """JSON-friendly snapshot of the safe event counters."""
        return {"total": self.total, "by_type": dict(self.counts)}
