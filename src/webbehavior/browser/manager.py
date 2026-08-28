"""Browser lifecycle management (Playwright).

``BrowserManager`` owns exactly one browser process for the whole test run
and one isolated context per session, guaranteeing cleanup even when a
session fails. It is also injectable: the engine accepts any object with
the same interface, which keeps the test suite free of real browsers.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Iterator

from webbehavior.browser.launcher import BrowserError, build_launch_options, install_hint
from webbehavior.monitoring.logger import get_logger

__all__ = ["BrowserManager"]

logger = get_logger("browser")


class BrowserManager:
    """Start once, open one page per session, always clean up."""

    def __init__(self, headless: bool = True, slow_mo_ms: int = 0) -> None:
        self.headless = headless
        self.slow_mo_ms = slow_mo_ms
        self._playwright = None
        self._browser = None
        self._contexts = []

    # -- lifecycle ---------------------------------------------------------

    @property
    def started(self) -> bool:
        return self._browser is not None and self._browser.is_connected()

    def start(self) -> None:
        """Launch the test browser (raises :class:`BrowserError` on failure)."""
        if self.started:
            return
        try:
            from playwright.sync_api import sync_playwright
        except Exception as exc:
            raise BrowserError(
                "Playwright is not installed.\n" + install_hint()
            ) from exc
        logger.info("Launching browser (headless=%s)", self.headless)
        try:
            self._playwright = sync_playwright().start()
            options = build_launch_options(
                headless=self.headless, slow_mo_ms=self.slow_mo_ms
            )
            self._browser = self._playwright.chromium.launch(**options)
        except BrowserError:
            raise
        except Exception as exc:
            self.stop()
            raise BrowserError(
                "Browser initialization failed.\n" + install_hint()
            ) from exc

    def stop(self) -> None:
        """Close every context, the browser and the Playwright driver."""
        for context in list(self._contexts):
            try:
                context.close()
            except Exception:
                pass
        self._contexts = []
        if self._browser is not None:
            try:
                self._browser.close()
            except Exception:
                pass
            self._browser = None
        if self._playwright is not None:
            try:
                self._playwright.stop()
            except Exception:
                pass
            self._playwright = None
        logger.info("Browser stopped")

    def __enter__(self) -> "BrowserManager":
        self.start()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.stop()

    # -- sessions ------------------------------------------------------------

    @contextmanager
    def session(self) -> Iterator[object]:
        """Yield a fresh page in an isolated context; always closes it."""
        if not self.started:
            self.start()
        assert self._browser is not None
        context = self._browser.new_context()
        self._contexts.append(context)
        page = context.new_page()
        try:
            yield page
        finally:
            try:
                context.close()
            except Exception:
                pass
            if context in self._contexts:
                self._contexts.remove(context)

    # -- navigation helpers ---------------------------------------------------

    def load(self, page, url: str, timeout_ms: int = 30000):
        """Navigate *page* to *url* and return ``(response, elapsed_ms)``."""
        started = time.perf_counter()
        response = page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        return response, elapsed_ms
