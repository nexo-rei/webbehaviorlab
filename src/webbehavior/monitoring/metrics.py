"""Metrics aggregation for test runs.

Collects only safe, non-sensitive measurements: latencies, durations,
success/failure counts, action counts and event counts. No page content,
cookies, headers or credentials are ever recorded.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from webbehavior.core.session import SessionResult, SessionStatus

__all__ = ["MetricsCollector", "RunMetrics"]


def _mean(values: List[float]) -> Optional[float]:
    return sum(values) / len(values) if values else None


class MetricsCollector:
    """Accumulates :class:`SessionResult` objects and computes statistics."""

    def __init__(self) -> None:
        self._results: List[SessionResult] = []
        self.started_at: Optional[datetime] = None
        self.finished_at: Optional[datetime] = None
        self.error_count: int = 0

    # -- collection -----------------------------------------------------

    def start(self) -> None:
        self.started_at = datetime.now()

    def finish(self) -> None:
        self.finished_at = datetime.now()

    def add(self, result: SessionResult) -> None:
        """Record one finished session."""
        self._results.append(result)
        if result.status is SessionStatus.FAILED:
            self.error_count += 1

    # -- statistics -----------------------------------------------------

    @property
    def results(self) -> List[SessionResult]:
        return list(self._results)

    @property
    def total_sessions(self) -> int:
        return len(self._results)

    @property
    def success_count(self) -> int:
        return sum(1 for r in self._results if r.ok)

    @property
    def failed_count(self) -> int:
        return sum(1 for r in self._results if not r.ok)

    @property
    def latencies_ms(self) -> List[float]:
        return [r.response_time_ms for r in self._results if r.response_time_ms is not None]

    @property
    def avg_latency_ms(self) -> Optional[float]:
        return _mean(self.latencies_ms)

    @property
    def min_latency_ms(self) -> Optional[float]:
        return min(self.latencies_ms) if self.latencies_ms else None

    @property
    def max_latency_ms(self) -> Optional[float]:
        return max(self.latencies_ms) if self.latencies_ms else None

    @property
    def total_actions(self) -> int:
        return sum(r.actions_done for r in self._results)

    @property
    def total_events(self) -> int:
        return sum(r.events_count for r in self._results)

    @property
    def total_duration_s(self) -> Optional[float]:
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        durations = [r.duration_s for r in self._results if r.duration_s is not None]
        return sum(durations) if durations else None

    @property
    def success_rate(self) -> Optional[float]:
        if not self._results:
            return None
        return 100.0 * self.success_count / self.total_sessions

    @property
    def status(self) -> str:
        """Overall run status: PASS / PARTIAL / FAIL (mirrors history)."""
        if not self._results:
            return "FAIL"
        if self.success_count == self.total_sessions:
            return "PASS"
        if self.success_count == 0:
            return "FAIL"
        return "PARTIAL"

    def summary(self) -> Dict[str, object]:
        """Flat, JSON-friendly summary used by reports and dashboards."""
        return {
            "sessions": self.total_sessions,
            "successful": self.success_count,
            "failed": self.failed_count,
            "errors": self.error_count,
            "avg_latency_ms": self.avg_latency_ms,
            "min_latency_ms": self.min_latency_ms,
            "max_latency_ms": self.max_latency_ms,
            "total_actions": self.total_actions,
            "total_events": self.total_events,
            "total_duration_s": self.total_duration_s,
            "success_rate": self.success_rate,
            "status": self.status,
        }


class RunMetrics(MetricsCollector):
    """Alias kept for readability at call sites (a *run* of sessions)."""

    __doc__ = MetricsCollector.__doc__
