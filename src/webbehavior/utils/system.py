"""System / environment introspection helpers (Termux aware)."""

from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass
from typing import List, Optional, Tuple

MIN_PYTHON = (3, 8)


def is_termux() -> bool:
    """True when running inside a Termux environment on Android."""
    return "com.termux" in os.environ.get("PREFIX", "") or bool(
        os.environ.get("TERMUX_VERSION")
    )


def python_version_string() -> str:
    return sys.version.split()[0]


def python_supported() -> bool:
    return sys.version_info >= MIN_PYTHON


def termux_prefix() -> Optional[str]:
    prefix = os.environ.get("PREFIX", "")
    return prefix if "com.termux" in prefix else None


def terminal_size() -> Tuple[int, int]:
    """Best-effort terminal (columns, rows); safe when piped or no TTY."""
    try:
        size = shutil.get_terminal_size(fallback=(80, 24))
        return max(size.columns, 20), max(size.lines, 10)
    except Exception:  # pragma: no cover - defensive
        return 80, 24


def compact_mode(width: Optional[int] = None) -> bool:
    """True when the terminal is too narrow for the full layout.

    Small phone screens in Termux commonly report 40-60 columns; the UI
    switches to an abbreviated "compact mode" layout there.
    """
    columns = width if width is not None else terminal_size()[0]
    return columns < 70


def pretty_platform() -> str:
    return "Termux (Android)" if is_termux() else f"{sys.platform} (Linux/Unix-like)"


@dataclass
class CheckResult:
    """Outcome of a single ``webbehavior doctor`` check."""

    name: str
    ok: bool
    detail: str = ""

    @property
    def symbol(self) -> str:
        return "✓" if self.ok else "✗"


def doctor_checks() -> List[CheckResult]:
    """Run all environment health checks and return their results.

    Checks: Python version, rich, Playwright, browser availability and
    storage-directory permissions. Never raises.
    """
    results: List[CheckResult] = []

    results.append(
        CheckResult(
            "Python",
            python_supported(),
            f"v{python_version_string()} (needs >= {MIN_PYTHON[0]}.{MIN_PYTHON[1]})",
        )
    )

    try:
        from importlib.metadata import version as _pkg_version

        import rich  # noqa: F401

        results.append(CheckResult("Rich", True, f"v{_pkg_version('rich')}"))
    except Exception as exc:  # pragma: no cover - depends on environment
        results.append(CheckResult("Rich", False, str(exc)))

    try:
        from playwright.sync_api import sync_playwright  # noqa: F401

        results.append(CheckResult("Playwright", True))
        playwright_ok = True
    except Exception as exc:
        results.append(CheckResult("Playwright", False, str(exc)))
        playwright_ok = False

    if playwright_ok:
        try:
            from webbehavior.browser.launcher import find_browser_executable

            executable = find_browser_executable()
            if executable:
                results.append(CheckResult("Browser", True, executable))
            else:  # pragma: no cover - depends on environment
                results.append(
                    CheckResult("Browser", False, "no Chromium found - see docs")
                )
        except Exception as exc:  # pragma: no cover - defensive
            results.append(CheckResult("Browser", False, str(exc)))
    else:
        results.append(CheckResult("Browser", False, "Playwright unavailable"))

    try:
        from webbehavior.utils import storage

        storage.ensure_dirs()
        probe = storage.app_dir() / ".write-probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        results.append(CheckResult("Storage", True, str(storage.app_dir())))
    except Exception as exc:
        results.append(CheckResult("Storage", False, str(exc)))

    return results
