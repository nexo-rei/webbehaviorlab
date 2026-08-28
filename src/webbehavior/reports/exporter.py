"""Report export to the local reports directory (JSON + TXT).

Filenames are sanitized and deterministic; JSON is written atomically.
Missing/empty data is handled gracefully (an empty run still produces a
valid report).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional

from webbehavior.reports.templates import render_txt_report
from webbehavior.utils import storage

__all__ = ["export_report", "list_reports", "read_report"]

SUPPORTED_FORMATS = ("json", "txt")


def _base_name(report: Dict) -> str:
    test_id = storage.safe_filename(str(report.get("test_id", "report")))
    stamp = storage.timestamp_dirname()
    return "{}-{}".format(test_id, stamp)


def export_report(report: Dict, formats=None) -> Dict[str, Path]:
    """Write *report* to ``~/.webbehavior/reports/`` in the given formats.

    Returns a mapping ``{"json": Path, "txt": Path}``.
    """
    wanted = [f for f in (formats or SUPPORTED_FORMATS) if f in SUPPORTED_FORMATS]
    base = _base_name(report)
    written: Dict[str, Path] = {}
    for fmt in wanted:
        path = storage.reports_dir() / "{}.{}".format(base, fmt)
        if fmt == "json":
            storage.write_json(path, report)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(render_txt_report(report), encoding="utf-8")
        written[fmt] = path
    return written


def list_reports() -> list:
    """All exported report files, newest first, as (path, fmt) tuples."""
    directory = storage.reports_dir()
    if not directory.exists():
        return []
    files = sorted(directory.glob("WB-*.*"), reverse=True)
    return [(p, p.suffix.lstrip(".").lower()) for p in files if p.is_file()]


def read_report(path: Path) -> Optional[Dict]:
    """Load a JSON report from *path* (None on failure)."""
    data = storage.read_json(path, default=None)
    return data if isinstance(data, dict) else None


def report_to_json_text(report: Dict) -> str:
    """Pretty JSON string (used in tests and previews)."""
    return json.dumps(report, indent=2, ensure_ascii=False)
