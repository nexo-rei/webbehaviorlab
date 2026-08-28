"""Test engine: executes the authorized test workflow.

The engine coordinates one :class:`BrowserManager`, the action executor,
event recording and metrics collection across every session of a run. It is
deliberately UI-agnostic: progress is published through callbacks, so the
same engine powers the live dashboard, plain piped output and the test
suite (with a fake browser injected).
"""

from __future__ import annotations

import time
from typing import Callable, Dict, List, Optional

from webbehavior.browser.actions import ActionExecutor
from webbehavior.browser.events import EventRecorder
from webbehavior.browser.launcher import BrowserError
from webbehavior.core.limiter import validate_session_count
from webbehavior.core.scheduler import SessionPlan, build_plan
from webbehavior.core.session import SessionResult, SessionStatus
from webbehavior.monitoring.logger import get_logger
from webbehavior.monitoring.metrics import MetricsCollector
from webbehavior.monitoring.tracker import LiveTracker
from webbehavior.utils.network import display_host

__all__ = ["TestEngine", "EngineSummary"]

logger = get_logger("engine")

ProgressCallback = Callable[[str, Dict[str, object]], None]


class TestEngine:
    """Run a pre-validated, pre-authorized :class:`SessionPlan`."""

    def __init__(
        self,
        browser_manager,
        settings,
        tracker: Optional[LiveTracker] = None,
        on_event: Optional[ProgressCallback] = None,
    ) -> None:
        self.browser = browser_manager
        self.settings = settings
        self.tracker = tracker
        self.on_event = on_event
        self.executor = ActionExecutor(action_delay_ms=getattr(settings, "action_delay_ms", 400))
        self.actions: List[str] = list(getattr(settings, "actions", []) or [])

    # -- public API ---------------------------------------------------------

    def run(self, target: str, sessions: int) -> MetricsCollector:
        """Execute every session of the test and return collected metrics.

        ``sessions`` is re-validated here (backend enforcement): a value
        above the hard maximum raises :class:`SessionLimitError` no matter
        what the UI allowed.
        """
        plan: SessionPlan = build_plan(
            target,
            validate_session_count(sessions),
            inter_session_delay_s=getattr(self.settings, "inter_session_delay_ms", 800) / 1000.0,
        )
        metrics = MetricsCollector()
        tracker = self.tracker or LiveTracker(plan.sessions, target)
        tracker.total_sessions = plan.sessions

        self._emit("test_start", {"target": target, "sessions": plan.sessions})
        metrics.start()
        tracker.set_status("RUNNING", "Starting browser...")

        try:
            self.browser.start()
        except BrowserError as exc:
            tracker.set_status("ABORTED", str(exc))
            metrics.finish()
            self._emit("test_error", {"stage": "browser", "error": str(exc)})
            raise

        aborted = False
        try:
            for index in plan:
                tracker.begin_session(index)
                self._emit("session_start", {"index": index})
                result = self._run_session(index, target, tracker)
                metrics.add(result)
                tracker.update_metrics(metrics.summary())
                tracker.end_session()
                self._emit(
                    "session_end",
                    {"index": index, "ok": result.ok, "http_status": result.http_status,
                     "duration_s": result.duration_s},
                )
        except KeyboardInterrupt:
            aborted = True
            tracker.set_status("ABORTED", "Test stopped by user")
            logger.info("Test aborted by user (Ctrl+C)")
        finally:
            self._safe_stop_browser()
            metrics.finish()
            if not aborted:
                tracker.set_status("FINISHED", "")
            self._emit("test_end", dict(metrics.summary(), aborted=aborted))

        return metrics

    # -- one session -----------------------------------------------------------

    def _run_session(
        self,
        index: int,
        target: str,
        tracker: LiveTracker,
    ) -> SessionResult:
        result = SessionResult(index=index, target=target)
        timer_start = time.perf_counter()
        recorder = EventRecorder()
        timeout_ms = getattr(self.settings, "page_load_timeout_ms", 30000)

        tracker.stage("browser", "done", "ready")
        try:
            with self.browser.session() as page:
                recorder.attach(page)
                tracker.stage("page_load", "running")
                response, elapsed_ms = self.browser.load(page, target, timeout_ms=timeout_ms)
                result.response_time_ms = round(elapsed_ms, 1)
                tracker.stage("page_load", "done", "{:.2f}s".format(elapsed_ms / 1000.0))

                if response is not None:
                    status_code = response.status
                    result.http_status = status_code
                    ok = 200 <= status_code < 400
                    tracker.stage(
                        "response",
                        "done" if ok else "failed",
                        "{} {}".format(status_code, "OK" if ok else "ERR"),
                    )
                else:
                    tracker.stage("response", "failed", "no response")

                result.page_load_ms = self._navigation_timing_ms(page)

                tracker.stage("actions", "running")
                outcomes = self.executor.run(page, self.actions, target=target)
                executed = [o for o in outcomes if o.executed]
                result.actions_done = len(executed)
                result.actions_total = len(outcomes)
                tracker.stage("actions", "done", "{}/{}".format(len(executed), len(outcomes)))

                tracker.stage("events", "info", str(recorder.total))
                result.events_count = recorder.total
                result.status = SessionStatus.SUCCESS
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            result.status = SessionStatus.FAILED
            result.error = self._short_error(exc)
            logger.warning("Session %s failed: %s", index, result.error)
            for key in ("page_load", "actions"):
                if key not in tracker.stages or tracker.stages[key].state == "running":
                    tracker.stage(key, "failed", "")

        result.duration_s = round(time.perf_counter() - timer_start, 2)
        tracker.stage("duration", "info", "{:.2f} sec".format(result.duration_s))
        return result

    @staticmethod
    def _navigation_timing_ms(page) -> Optional[float]:
        """Read the page's own navigation timing (loadEventEnd - startTime)."""
        scripts = (
            "performance.getEntriesByType('navigation')[0].loadEventEnd",
            "performance.getEntriesByType('navigation')[0].domContentLoadedEventEnd",
        )
        for script in scripts:
            try:
                value = page.evaluate(script)
                if isinstance(value, (int, float)) and value > 0:
                    return round(float(value), 1)
            except Exception:
                continue
        return None

    @staticmethod
    def _short_error(exc: BaseException) -> str:
        """One-line, sanitized error summary safe to show and store."""
        name = type(exc).__name__
        text = " ".join(str(exc).split())[:160]
        return "{}: {}".format(name, text) if text else name

    def _safe_stop_browser(self) -> None:
        try:
            self.browser.stop()
        except Exception:
            logger.warning("Browser cleanup raised; continuing", exc_info=True)

    def _emit(self, event: str, data: Dict[str, object]) -> None:
        if self.on_event is None:
            return
        try:
            self.on_event(event, data)
        except Exception:
            logger.debug("progress callback failed for %s", event, exc_info=True)


class EngineSummary:
    """Convenience wrapper for displaying a finished run."""

    def __init__(self, test_id: str, target: str, metrics: MetricsCollector) -> None:
        self.test_id = test_id
        self.target = target
        self.metrics = metrics

    @property
    def host(self) -> str:
        return display_host(self.target)
