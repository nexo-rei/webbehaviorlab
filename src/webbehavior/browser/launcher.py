"""Browser/Playwright environment detection and launch options.

Termux cannot use Playwright's bundled Chromium downloads, so the launcher
also detects a distribution Chromium (``pkg install chromium``) and honors
the ``WEBBEHAVIOR_BROWSER_PATH`` environment variable. On desktop Linux the
standard Playwright Chromium is used.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional

__all__ = [
    "BrowserError",
    "playwright_available",
    "find_browser_executable",
    "build_launch_options",
    "install_hint",
]


class BrowserError(RuntimeError):
    """Raised when the test browser cannot be started.

    The message is beginner-friendly and never contains a raw traceback.
    """


def _candidate_executables() -> List[str]:
    candidates: List[str] = []
    env_path = os.environ.get("WEBBEHAVIOR_BROWSER_PATH", "").strip()
    if env_path:
        candidates.append(env_path)
    prefix = os.environ.get("PREFIX", "")
    if "com.termux" in prefix:
        candidates += [
            os.path.join(prefix, "bin", "chromium"),
            os.path.join(prefix, "bin", "chromium-browser"),
            os.path.join(prefix, "bin", "chrome"),
        ]
    candidates += [
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/snap/bin/chromium",
    ]
    return candidates


def find_browser_executable() -> Optional[str]:
    """Return the first existing Chromium/Chrome executable, else ``None``.

    Prefers an explicit env override, then Termux packages, then distro
    packages, then Playwright's own downloaded Chromium.
    """
    for candidate in _candidate_executables():
        if candidate and shutil.which(candidate):
            return candidate
        if candidate and Path(candidate).is_file() and os.access(candidate, os.X_OK):
            return candidate
    return playwright_chromium_path()


def playwright_chromium_path() -> Optional[str]:
    """Locate Playwright's downloaded Chromium without starting a driver.

    Purely filesystem-based so ``webbehavior doctor`` stays quiet and fast.
    """
    roots = []
    env_override = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "").strip()
    if env_override:
        roots.append(Path(env_override))
    cache = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    roots.append(Path(cache) / "ms-playwright")
    for root in roots:
        if not root.is_dir():
            continue
        for chromium_dir in sorted(root.glob("chromium*"), reverse=True):
            for rel in ("chrome-linux/chrome", "chrome-linux/headless_shell",
                        "chrome-android/chrome", "chrome-android/headless_shell"):
                candidate = chromium_dir / rel
                if candidate.is_file() and os.access(str(candidate), os.X_OK):
                    return str(candidate)
    return None


def playwright_available() -> bool:
    """True when the ``playwright`` package imports cleanly."""
    try:
        import playwright  # noqa: F401
        from playwright.sync_api import sync_playwright  # noqa: F401

        return True
    except Exception:
        return False


def install_hint() -> str:
    """Platform-appropriate hint shown when the browser is missing."""
    from webbehavior.utils.system import is_termux

    if is_termux():
        return (
            "Playwright's bundled browser cannot be downloaded inside Termux.\n"
            "Install Chromium instead:\n"
            "  pkg install chromium\n"
            "Then re-run: webbehavior doctor"
        )
    return "Run:\n  playwright install chromium\nThen re-run: webbehavior doctor"


def build_launch_options(
    headless: bool = True,
    slow_mo_ms: int = 0,
    executable: Optional[str] = None,
) -> Dict[str, object]:
    """Build Chromium launch options.

    Safety notes:
      * no proxy configuration is ever passed (no proxy rotation),
      * no ``--disable-blink-features=AutomationControlled`` or similar
        anti-detection flags are used - the browser honestly identifies
        itself as automated,
      * a modest viewport keeps rendering deterministic.
    """
    options: Dict[str, object] = {
        "headless": bool(headless),
        "args": [
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-extensions",
            "--disable-background-networking",
        ],
    }
    resolved = executable or find_browser_executable()
    if resolved:
        options["executable_path"] = resolved
    if slow_mo_ms > 0:
        options["slow_mo"] = slow_mo_ms
    return options
