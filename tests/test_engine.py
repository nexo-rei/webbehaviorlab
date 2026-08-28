"""Integration-style tests for the engine with an injected fake browser.

A real local HTTP server is started on 127.0.0.1 (authorized scope), and a
FakeBrowser implementing the BrowserManager interface fetches pages over
HTTP. This exercises the full engine -> tracker -> metrics -> reports path
without requiring Chromium in CI.
"""

from __future__ import annotations

import http.server
import threading
from typing import Iterator, Optional, Tuple

import pytest

from webbehavior.config import Settings
from webbehavior.core.engine import TestEngine
from webbehavior.core.limiter import SessionLimitError
from webbehavior.monitoring.tracker import LiveTracker
from webbehavior.reports.exporter import export_report
from webbehavior.reports.generator import build_report

PAGE_HTML = b"""<!doctype html>
<html><head><title>WBL test page</title></head>
<body style="height: 3000px">
<h1>WebBehaviorLab local test target</h1>
<button data-wbl-test>Test button</button>
</body></html>"""


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 - http.server API
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(PAGE_HTML)))
        self.end_headers()
        self.wfile.write(PAGE_HTML)

    def log_message(self, *args: object) -> None:
        pass


@pytest.fixture()
def local_server() -> Iterator[Tuple[str, int]]:
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield "127.0.0.1", server.server_address[1]
    server.shutdown()
    thread.join(timeout=2)


class FakeResponse:
    def __init__(self, status: int) -> None:
        self.status = status


class FakePage:
    """Minimal page double matching the engine's usage."""

    def __init__(self, url: str) -> None:
        self.url = url
        self.handlers = {}

    def on(self, event: str, handler) -> None:
        self.handlers[event] = handler

    def evaluate(self, script: str) -> float:
        return 321.5

    def goto(self, url: str, **kwargs) -> FakeResponse:
        import time
        import urllib.request

        started = time.perf_counter()
        with urllib.request.urlopen(url, timeout=5) as resp:
            resp.read()
        self.url = url
        self._elapsed = (time.perf_counter() - started) * 1000
        return FakeResponse(resp.status if hasattr(resp, "status") else 200)

    def wait_for_timeout(self, ms: int) -> None:
        import time

        time.sleep(ms / 1000.0)


class FakeBrowser:
    """Same interface as BrowserManager, without Chromium."""

    def __init__(self, fail_on: Optional[int] = None) -> None:
        self.started = False
        self.stopped = False
        self.sessions = 0
        self.fail_on = fail_on  # session index that should fail

    def start(self) -> None:
        self.started = True
        self.stopped = False

    def stop(self) -> None:
        self.stopped = True
        self.started = False

    def session(self):
        browser = self

        class _Ctx:
            def __enter__(self):
                browser.sessions += 1
                return FakePage("about:blank")

            def __exit__(self, *exc):
                return False

        return _Ctx()

    def load(self, page: FakePage, url: str, timeout_ms: int = 30000):
        import time

        # fail_on == 0 -> every session fails; N -> only session N fails.
        should_fail = self.fail_on is not None and self.fail_on in (0, self.sessions)
        if should_fail:
            raise ConnectionError("connection refused (simulated)")
        started = time.perf_counter()
        response = page.goto(url)
        elapsed = (time.perf_counter() - started) * 1000.0
        return response, elapsed


def make_settings(actions=("page_load",), sessions_delay_ms: int = 250) -> Settings:
    return Settings(
        actions=list(actions),
        action_delay_ms=100,
        inter_session_delay_ms=sessions_delay_ms,
        page_load_timeout_ms=5000,
    )


class TestEngineHappyPath:
    def test_three_sessions_succeed(self, local_server) -> None:
        host, port = local_server
        target = "http://{}:{}/".format(host, port)
        browser = FakeBrowser()
        engine = TestEngine(browser, make_settings())
        metrics = engine.run(target, 3)

        assert metrics.total_sessions == 3
        assert metrics.success_count == 3
        assert metrics.failed_count == 0
        assert all(r.http_status == 200 for r in metrics.results)
        assert metrics.avg_latency_ms is not None and metrics.avg_latency_ms > 0
        assert metrics.status == "PASS"
        # browser lifecycle respected
        assert browser.stopped is True

    def test_tracker_receives_progress(self, local_server) -> None:
        host, port = local_server
        target = "http://{}:{}/".format(host, port)
        tracker = LiveTracker(2, target)
        engine = TestEngine(FakeBrowser(), make_settings(), tracker=tracker)
        engine.run(target, 2)

        snapshot = tracker.snapshot()
        assert snapshot["done"] == 2
        assert snapshot["status"] == "FINISHED"
        assert snapshot["progress"] == 100
        assert snapshot["stages"]["browser"][0] == "done"


class TestEngineFailures:
    def test_failed_session_recorded_and_run_continues(self, local_server) -> None:
        host, port = local_server
        target = "http://{}:{}/".format(host, port)
        browser = FakeBrowser(fail_on=1)
        engine = TestEngine(browser, make_settings())
        metrics = engine.run(target, 3)

        assert metrics.total_sessions == 3
        assert metrics.success_count == 2
        assert metrics.failed_count == 1
        assert metrics.status == "PARTIAL"
        assert metrics.results[0].error is not None
        # cleanup still happened
        assert browser.stopped is True

    def test_engine_enforces_hard_limit(self, local_server) -> None:
        host, port = local_server
        target = "http://{}:{}/".format(host, port)
        engine = TestEngine(FakeBrowser(), make_settings())
        with pytest.raises(SessionLimitError):
            engine.run(target, 11)

    def test_all_failures_produce_fail_report(self, local_server) -> None:
        host, port = local_server
        target = "http://{}:{}/".format(host, port)
        engine = TestEngine(FakeBrowser(fail_on=0), make_settings())
        metrics = engine.run(target, 2)
        assert metrics.success_count == 0
        assert metrics.status == "FAIL"


class TestEngineToReports:
    def test_full_pipeline_exports_reports(self, local_server, tmp_path, monkeypatch) -> None:
        monkeypatch.setenv("WEBBEHAVIOR_HOME", str(tmp_path / "home"))
        host, port = local_server
        target = "http://{}:{}/".format(host, port)
        engine = TestEngine(FakeBrowser(), make_settings())
        metrics = engine.run(target, 2)

        report = build_report("WB-2026-0042", target, metrics)
        written = export_report(report)
        assert written["json"].exists()
        assert written["txt"].exists()
        assert report["summary"]["successful"] == 2
        assert report["meta"]["host"] == "127.0.0.1:{}".format(port)
