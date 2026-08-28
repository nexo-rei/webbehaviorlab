"""Tests for report generation/export (PRD 25: reports).

JSON creation, TXT creation and missing-data handling.
"""

from __future__ import annotations

import json

import pytest

from webbehavior.core.session import SessionResult, SessionStatus
from webbehavior.monitoring.metrics import MetricsCollector
from webbehavior.reports.exporter import export_report, read_report
from webbehavior.reports.generator import build_report, next_test_id
from webbehavior.reports.templates import render_txt_report


@pytest.fixture()
def isolated_home(tmp_path, monkeypatch):
    home = tmp_path / "webbehavior-home"
    monkeypatch.setenv("WEBBEHAVIOR_HOME", str(home))
    return home


def sample_metrics() -> MetricsCollector:
    metrics = MetricsCollector()
    metrics.start()
    metrics.add(SessionResult(
        index=1, target="http://127.0.0.1:8000/", status=SessionStatus.SUCCESS,
        http_status=200, response_time_ms=250.0, page_load_ms=300.0,
        duration_s=1.2, actions_done=4, actions_total=4, events_count=8,
    ))
    metrics.add(SessionResult(
        index=2, target="http://127.0.0.1:8000/", status=SessionStatus.SUCCESS,
        http_status=200, response_time_ms=350.0, page_load_ms=400.0,
        duration_s=1.4, actions_done=4, actions_total=4, events_count=9,
    ))
    metrics.finish()
    return metrics


class TestJsonExport:
    def test_json_created(self, isolated_home) -> None:
        report = build_report("WB-2026-0001", "http://127.0.0.1:8000/", sample_metrics())
        written = export_report(report, formats=["json"])
        assert written["json"].exists()
        data = json.loads(written["json"].read_text(encoding="utf-8"))
        assert data["test_id"] == "WB-2026-0001"
        assert data["summary"]["sessions"] == 2
        assert data["meta"]["scope"] == "AUTHORIZED TEST TARGET"

    def test_json_readable_back(self, isolated_home) -> None:
        report = build_report("WB-2026-0002", "http://localhost:3000/", sample_metrics())
        written = export_report(report, formats=["json"])
        loaded = read_report(written["json"])
        assert loaded is not None
        assert loaded["summary"]["successful"] == 2


class TestTxtExport:
    def test_txt_created(self, isolated_home) -> None:
        report = build_report("WB-2026-0003", "http://127.0.0.1:8000/", sample_metrics())
        written = export_report(report, formats=["txt"])
        assert written["txt"].exists()
        text = written["txt"].read_text(encoding="utf-8")
        assert "TEST COMPLETE" in text
        assert "WB-2026-0003" in text
        assert "Avg Latency" in text

    def test_txt_contains_session_lines(self, isolated_home) -> None:
        report = build_report("WB-2026-0004", "http://localhost/", sample_metrics())
        written = export_report(report, formats=["txt"])
        text = written["txt"].read_text(encoding="utf-8")
        assert "✓ Session  1" in text
        assert "✓ Session  2" in text


class TestMissingData:
    def test_empty_metrics_still_export(self, isolated_home) -> None:
        metrics = MetricsCollector()
        metrics.start()
        metrics.finish()
        report = build_report("WB-2026-0005", "http://127.0.0.1:9999/", metrics)
        written = export_report(report)
        assert written["json"].exists()
        assert written["txt"].exists()
        data = json.loads(written["json"].read_text(encoding="utf-8"))
        assert data["summary"]["sessions"] == 0
        assert data["summary"]["avg_latency_ms"] is None

    def test_txt_missing_data_placeholder(self) -> None:
        text = render_txt_report(build_report("WB-2026-0006", "http://x.local/", MetricsCollector()))
        assert "no session data" in text
        assert "-- ms" in text

    def test_failed_session_rendered(self, isolated_home) -> None:
        metrics = MetricsCollector()
        metrics.start()
        metrics.add(SessionResult(index=1, target="http://127.0.0.1:9/",
                                  status=SessionStatus.FAILED, error="TimeoutError: x"))
        metrics.finish()
        report = build_report("WB-2026-0007", "http://127.0.0.1:9/", metrics)
        text = export_report(report, formats=["txt"])["txt"].read_text(encoding="utf-8")
        assert "✗ Session  1" in text


class TestTestIds:
    def test_first_id(self) -> None:
        assert next_test_id([]).startswith("WB-")
        assert next_test_id([]).endswith("-0001")

    def test_sequence_increments(self) -> None:
        from datetime import datetime

        year = datetime.now().year
        history = [
            {"test_id": "WB-{}-0001".format(year)},
            {"test_id": "WB-{}-0002".format(year)},
        ]
        assert next_test_id(history) == "WB-{}-0003".format(year)

    def test_ignores_other_years(self) -> None:
        assert next_test_id([{"test_id": "WB-1999-0099"}]).endswith("-0001")
