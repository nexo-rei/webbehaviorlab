"""Tests for BrowserManager lifecycle with a mocked Playwright driver.

Verifies start/session/cleanup behavior without needing Chromium:
one browser process, one isolated context per session, guaranteed
cleanup even when pages fail.
"""

from __future__ import annotations

from typing import List, Optional

import pytest

from webbehavior.browser import launcher, manager


class FakePlaywrightAPI:
    """Minimal double of playwright.sync_api used by BrowserManager.

    Mirrors the real shape: ``sync_playwright()`` returns a context
    manager whose ``.start()`` yields a driver exposing ``.chromium``.
    """

    def __init__(self, launch_error: Optional[Exception] = None) -> None:
        self.launch_error = launch_error
        self.browser = FakeBrowser()
        self.stopped = False
        self.last_launch_options: dict = {}
        self.chromium = self

    # -- playwright handle API -------------------------------------------
    def start(self) -> "FakePlaywrightAPI":
        return self

    def __enter__(self) -> "FakePlaywrightAPI":
        return self

    def __exit__(self, *exc) -> bool:
        return False

    # -- chromium-ish API ---------------------------------------------------
    def launch(self, **options):
        if self.launch_error:
            raise self.launch_error
        self.last_launch_options = options
        return self.browser

    def stop(self) -> None:
        self.stopped = True


class FakeBrowser:
    def __init__(self) -> None:
        self.contexts: List[FakeContext] = []
        self.closed = False

    def is_connected(self) -> bool:
        return not self.closed

    def new_context(self) -> "FakeContext":
        context = FakeContext()
        self.contexts.append(context)
        return context

    def close(self) -> None:
        self.closed = True
        for context in list(self.contexts):
            context.close()


class FakeContext:
    def __init__(self) -> None:
        self.pages: List[FakePage] = []
        self.closed = False

    def new_page(self) -> "FakePage":
        page = FakePage()
        self.pages.append(page)
        return page

    def close(self) -> None:
        self.closed = True


class FakePage:
    def __init__(self) -> None:
        self.handlers = {}
        self.goto_calls: List[tuple] = []

    def on(self, event, handler) -> None:
        self.handlers[event] = handler

    def goto(self, url, timeout=None, wait_until=None):
        self.goto_calls.append((url, timeout, wait_until))
        return FakeResponse(200)


class FakeResponse:
    def __init__(self, status: int) -> None:
        self.status = status


@pytest.fixture()
def patched_playwright(monkeypatch):
    api = FakePlaywrightAPI()

    class _PWHandle:
        def __enter__(self):
            return api

        def __exit__(self, *exc):
            return False

    fake_module = type("sync_api_module", (), {"sync_playwright": lambda: api})

    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "playwright.sync_api":
            return fake_module
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    return api


class TestLifecycle:
    def test_start_launches_once(self, patched_playwright) -> None:
        mgr = manager.BrowserManager(headless=True)
        mgr.start()
        mgr.start()  # idempotent
        assert patched_playwright.browser in (mgr._browser,)
        assert mgr.started

    def test_launch_options_honest(self, patched_playwright, monkeypatch) -> None:
        monkeypatch.setattr(launcher, "find_browser_executable", lambda: None)
        mgr = manager.BrowserManager(headless=True)
        mgr.start()
        options = patched_playwright.last_launch_options
        assert options["headless"] is True
        # No stealth/anti-detection flags allowed, ever.
        joined = " ".join(options.get("args", []))
        assert "AutomationControlled" not in joined
        assert "proxy" not in options

    def test_start_uses_detected_executable(self, patched_playwright, monkeypatch) -> None:
        monkeypatch.setattr(launcher, "find_browser_executable", lambda: "/usr/bin/chromium")
        mgr = manager.BrowserManager(headless=True)
        mgr.start()
        assert patched_playwright.last_launch_options.get("executable_path") == "/usr/bin/chromium"

    def test_session_creates_and_closes_context(self, patched_playwright) -> None:
        mgr = manager.BrowserManager()
        mgr.start()
        with mgr.session() as page:
            assert isinstance(page, FakePage)
        assert patched_playwright.browser.contexts[0].closed

    def test_session_closes_on_error(self, patched_playwright) -> None:
        mgr = manager.BrowserManager()
        mgr.start()
        with pytest.raises(RuntimeError):
            with mgr.session() as page:
                raise RuntimeError("boom")
        assert patched_playwright.browser.contexts[0].closed

    def test_stop_closes_everything(self, patched_playwright) -> None:
        mgr = manager.BrowserManager()
        mgr.start()
        with mgr.session():
            pass
        with mgr.session():
            pass
        mgr.stop()
        assert patched_playwright.browser.closed
        assert patched_playwright.stopped
        assert mgr.started is False
        assert all(c.closed for c in patched_playwright.browser.contexts)

    def test_launch_failure_stops_and_raises_friendly(self, patched_playwright, monkeypatch) -> None:
        monkeypatch.setattr(launcher, "find_browser_executable", lambda: None)
        patched_playwright.launch_error = RuntimeError("executable doesn't exist")
        mgr = manager.BrowserManager()
        with pytest.raises(launcher.BrowserError) as excinfo:
            mgr.start()
        assert "Browser initialization failed" in str(excinfo.value)
        # driver stopped so no orphan process remains
        assert patched_playwright.stopped

    def test_load_returns_response_and_timing(self, patched_playwright) -> None:
        mgr = manager.BrowserManager()
        mgr.start()
        with mgr.session() as page:
            response, elapsed = mgr.load(page, "http://127.0.0.1:8000/", timeout_ms=1500)
        assert response.status == 200
        assert elapsed >= 0
        assert page.goto_calls[0][0] == "http://127.0.0.1:8000/"
        assert page.goto_calls[0][1] == 1500


class TestLauncherHelpers:
    def test_env_override_wins(self, tmp_path, monkeypatch) -> None:
        exe = tmp_path / "my-chrome"
        exe.write_text("#!/bin/sh\n")
        exe.chmod(0o755)
        monkeypatch.setenv("WEBBEHAVIOR_BROWSER_PATH", str(exe))
        assert launcher.find_browser_executable() == str(exe)

    def test_no_browser_found(self, monkeypatch, tmp_path) -> None:
        monkeypatch.delenv("WEBBEHAVIOR_BROWSER_PATH", raising=False)
        monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(tmp_path / "empty"))
        monkeypatch.setattr(launcher, "_candidate_executables", lambda: [])
        assert launcher.find_browser_executable() is None

    def test_playwright_chromium_detection(self, tmp_path, monkeypatch) -> None:
        root = tmp_path / "ms-playwright" / "chromium-1234" / "chrome-linux"
        root.mkdir(parents=True)
        chrome = root / "chrome"
        chrome.write_text("#!/bin/sh\n")
        chrome.chmod(0o755)
        monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(tmp_path / "ms-playwright"))
        assert launcher.find_browser_executable() == str(chrome)

    def test_build_launch_options_no_proxy(self) -> None:
        options = launcher.build_launch_options(headless=False, slow_mo_ms=50)
        assert options["headless"] is False
        assert options["slow_mo"] == 50
        assert "proxy" not in options
