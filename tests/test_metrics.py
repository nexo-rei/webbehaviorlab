"""Tests for metrics calculation (PRD 25: metrics)."""

from __future__ import annotations

import pytest

from webbehavior.core.session import SessionResult, SessionStatus
from webbehavior.monitoring.metrics import MetricsCollector


def make_result(index: int, latency: float = None, ok: bool = True,
                duration: float = 1.0, actions: int = 4, events: int = 6) -> SessionResult:
    return SessionResult(
        index=index,
        target="http://127.0.0.1:8000/",
        status=SessionStatus.SUCCESS if ok else SessionStatus.FAILED,
        http_status=200 if ok else None,
        response_time_ms=latency,
        page_load_ms=latency,
        duration_s=duration,
        actions_done=actions if ok else 0,
        actions_total=actions,
        events_count=events if ok else 0,
        error=None if ok else "connection refused",
    )


class TestLatencyStats:
    def test_average_latency(self) -> None:
        metrics = MetricsCollector()
        for i, latency in enumerate([100, 200, 300], start=1):
            metrics.add(make_result(i, latency=latency))
        assert metrics.avg_latency_ms == pytest.approx(200.0)

    def test_min_latency(self) -> None:
        metrics = MetricsCollector()
        for i, latency in enumerate([221, 412, 284], start=1):
            metrics.add(make_result(i, latency=latency))
        assert metrics.min_latency_ms == 221

    def test_max_latency(self) -> None:
        metrics = MetricsCollector()
        for i, latency in enumerate([221, 412, 284], start=1):
            metrics.add(make_result(i, latency=latency))
        assert metrics.max_latency_ms == 412

    def test_failed_sessions_excluded_from_latency(self) -> None:
        metrics = MetricsCollector()
        metrics.add(make_result(1, latency=100))
        metrics.add(make_result(2, latency=None, ok=False))
        assert metrics.avg_latency_ms == 100.0

    def test_empty_metrics_are_none(self) -> None:
        metrics = MetricsCollector()
        assert metrics.avg_latency_ms is None
        assert metrics.min_latency_ms is None
        assert metrics.max_latency_ms is None


class TestSessionCounts:
    def test_successful_sessions(self) -> None:
        metrics = MetricsCollector()
        for i in range(5):
            metrics.add(make_result(i + 1))
        assert metrics.success_count == 5
        assert metrics.failed_count == 0

    def test_failed_sessions(self) -> None:
        metrics = MetricsCollector()
        metrics.add(make_result(1, ok=True))
        metrics.add(make_result(2, ok=False))
        metrics.add(make_result(3, ok=False))
        assert metrics.success_count == 1
        assert metrics.failed_count == 2
        assert metrics.error_count == 2

    def test_totals(self) -> None:
        metrics = MetricsCollector()
        metrics.add(make_result(1, actions=4, events=8))
        metrics.add(make_result(2, actions=5, events=9))
        assert metrics.total_sessions == 2
        assert metrics.total_actions == 9
        assert metrics.total_events == 17


class TestStatus:
    def test_all_pass(self) -> None:
        metrics = MetricsCollector()
        metrics.add(make_result(1))
        assert metrics.status == "PASS"

    def test_partial(self) -> None:
        metrics = MetricsCollector()
        metrics.add(make_result(1, ok=True))
        metrics.add(make_result(2, ok=False))
        assert metrics.status == "PARTIAL"

    def test_all_fail(self) -> None:
        metrics = MetricsCollector()
        metrics.add(make_result(1, ok=False))
        assert metrics.status == "FAIL"

    def test_empty_is_fail(self) -> None:
        assert MetricsCollector().status == "FAIL"


class TestSummary:
    def test_summary_shape(self) -> None:
        metrics = MetricsCollector()
        metrics.start()
        metrics.add(make_result(1, latency=250.0, duration=1.5))
        metrics.finish()
        summary = metrics.summary()
        assert summary["sessions"] == 1
        assert summary["successful"] == 1
        assert summary["failed"] == 0
        assert summary["avg_latency_ms"] == 250.0
        assert summary["min_latency_ms"] == 250.0
        assert summary["max_latency_ms"] == 250.0
        assert summary["status"] == "PASS"
        assert summary["total_duration_s"] is not None

    def test_empty_summary_handles_missing_data(self) -> None:
        summary = MetricsCollector().summary()
        assert summary["sessions"] == 0
        assert summary["avg_latency_ms"] is None
        assert summary["status"] == "FAIL"
