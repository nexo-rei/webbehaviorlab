"""Report data generation.

Builds the canonical report dictionary consumed by exporters, history and
the UI. Test IDs look like ``WB-2026-0001`` (sequence per year, derived
from the persisted history index).
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from webbehavior.core.session import SessionResult
from webbehavior.monitoring.logger import get_logger
from webbehavior.monitoring.metrics import MetricsCollector
from webbehavior.utils.network import display_host
from webbehavior.version import __version__

__all__ = ["next_test_id", "build_report"]

logger = get_logger("reports")


def next_test_id(history: List[Dict]) -> str:
    """Return the next sequential test ID for the current year."""
    year = datetime.now().year
    prefix = "WB-{}-".format(year)
    highest = 0
    for entry in history:
        test_id = str(entry.get("test_id", ""))
        if test_id.startswith(prefix):
            try:
                highest = max(highest, int(test_id[len(prefix):]))
            except ValueError:
                continue
    return "{}{:04d}".format(prefix, highest + 1)


def _session_entry(result: SessionResult) -> Dict:
    return {
        "index": result.index,
        "status": result.status.value,
        "http_status": result.http_status,
        "response_time_ms": result.response_time_ms,
        "page_load_ms": result.page_load_ms,
        "duration_s": result.duration_s,
        "actions_done": result.actions_done,
        "actions_total": result.actions_total,
        "events_count": result.events_count,
        "error": result.error,
    }


def build_report(
    test_id: str,
    target: str,
    metrics: MetricsCollector,
    actions: Optional[List[str]] = None,
) -> Dict:
    """Assemble the full report dictionary from collected metrics."""
    started = metrics.started_at or datetime.now()
    finished = metrics.finished_at or datetime.now()
    return {
        "test_id": test_id,
        "version": __version__,
        "meta": {
            "target": target,
            "host": display_host(target),
            "scope": "AUTHORIZED TEST TARGET",
            "started_at": started.isoformat(timespec="seconds"),
            "finished_at": finished.isoformat(timespec="seconds"),
            "actions": list(actions or []),
        },
        "summary": metrics.summary(),
        "sessions": [_session_entry(result) for result in metrics.results],
    }
