"""Interactive application menu (the ``webbehavior`` experience).

Implements the PRD main menu, Start Test flow (URL input -> TARGET SAFETY
CHECK authorization -> session count -> live dashboard -> completion panel
-> report), Test History, Reports, Settings and Help.
"""

from __future__ import annotations

import re
from typing import Dict, Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text

from webbehavior.browser.launcher import BrowserError
from webbehavior.browser.manager import BrowserManager
from webbehavior.config import ANIMATION_SPEEDS, THEMES, Config
from webbehavior.core.engine import TestEngine
from webbehavior.core.limiter import SessionLimitError, parse_session_count
from webbehavior.core.validator import TARGET_LABEL, is_authorized_scope, validate_url
from webbehavior.monitoring.tracker import LiveTracker
from webbehavior.reports.exporter import export_report, list_reports, read_report
from webbehavior.reports.generator import build_report, next_test_id
from webbehavior.ui.animations import AnimationController, step_sequence
from webbehavior.ui.banner import print_banner, section_title
from webbehavior.ui.dashboard import LiveDashboard
from webbehavior.ui.tables import history_table, report_table
from webbehavior.ui.theme import SYMBOLS, ThemeManager
from webbehavior.utils import storage
from webbehavior.utils.helpers import format_ms, format_seconds
from webbehavior.utils.system import compact_mode

__all__ = ["App"]

MENU_ITEMS = [
    ("1", "Start Test"),
    ("2", "Live Dashboard"),  # shown after/during tests; menu entry explains
    ("3", "Test History"),
    ("4", "Reports"),
    ("5", "Settings"),
    ("6", "Help"),
    ("0", "Exit"),
]


class App:
    """The interactive WebBehaviorLab application."""

    def __init__(self, console: Optional[Console] = None) -> None:
        self.console = console or Console()
        self.config = Config()
        self.theme = ThemeManager(self.config.settings.theme)
        self.animations = AnimationController(
            enabled=self.config.settings.animation,
            speed=self.config.settings.animation_speed,
        )

    # ------------------------------------------------------------------ util

    def _line(self, text: str = "", style: str = "primary") -> None:
        self.console.print(Text(text, style=style))

    def _panel(self, body, title: str = "", style: str = "panel_border") -> None:
        self.console.print(Panel(body, title=title, border_style=self.theme.style(style), expand=False))

    def error_panel(self, title: str, message: str) -> None:
        self._panel(
            Text("{} {}".format(SYMBOLS.ERROR, message), style="error"),
            title="[{}] {} ".format(SYMBOLS.ERROR, title),
            style="error",
        )

    def success_panel(self, title: str, message: str) -> None:
        self._panel(
            Text("{} {}".format(SYMBOLS.SUCCESS, message), style="success"),
            title="[{}] {} ".format(SYMBOLS.SUCCESS, title),
            style="success",
        )

    def _ask(self, prompt: str, default: Optional[str] = None) -> str:
        try:
            return Prompt.ask(
                Text(prompt, style="accent"),
                default=default if default is not None else "",
                show_default=default is not None,
                console=self.console,
            )
        except EOFError:
            raise KeyboardInterrupt from None

    def _pause(self) -> None:
        try:
            Prompt.ask(Text("Press ENTER to continue...", style="muted"), default="", console=self.console)
        except EOFError:
            raise KeyboardInterrupt from None

    # ------------------------------------------------------------------ run

    def run(self) -> int:
        """Main menu loop. Returns an exit code."""
        storage.ensure_dirs()
        print_banner(self.console, self.theme)
        while True:
            try:
                choice = self._main_menu()
                if choice is None or choice == "0":
                    self._goodbye()
                    return 0
                handlers = {
                    "1": self.start_test_flow,
                    "2": self.live_dashboard_info,
                    "3": self.history_flow,
                    "4": self.reports_flow,
                    "5": self.settings_flow,
                    "6": self.help_flow,
                }
                handler = handlers.get(choice)
                if handler is None:
                    self.error_panel("Invalid option", "Please choose a number from the menu.")
                else:
                    handler()
            except KeyboardInterrupt:
                self._goodbye()
                return 0
            except Exception as exc:  # never crash on a user-facing error
                from webbehavior.monitoring.logger import write_diagnostic

                error_id = write_diagnostic(exc, context={"url": getattr(self, "_last_target", "")})
                self.error_panel(
                    "Unexpected error",
                    "Something went wrong.\n\nError ID: {}\nA safe diagnostic log was created.".format(error_id),
                )
                # An unexpected internal error exits the app gracefully
                # instead of looping on a broken render path.
                return 1

    def _main_menu(self) -> Optional[str]:
        menu = Text()
        for key, label in MENU_ITEMS:
            menu.append("  [", "muted")
            menu.append(key, "accent bold")
            menu.append("] ", "muted")
            menu.append(label + "\n", "primary")
        self.console.print(menu)
        try:
            choice = Prompt.ask(
                Text("Choose an option", style="accent"),
                choices=[key for key, _ in MENU_ITEMS],
                show_choices=False,
                console=self.console,
            )
        except EOFError:
            return None
        return choice.strip()

    def _goodbye(self) -> None:
        self._line()
        self._line("{} Thank you for using WebBehaviorLab.".format(SYMBOLS.SUCCESS), "success")
        self._line("Authorized testing only. Goodbye!", "muted")

    # ------------------------------------------------------------- START TEST

    def start_test_flow(self, url: Optional[str] = None, sessions: Optional[int] = None,
                        assume_authorized: bool = False) -> None:
        """The complete Start Test flow (PRD 4-8)."""
        section_title(self.console, self.theme, "Start Test")
        self._panel(
            Text(
                "This test opens your authorized website and collects\n"
                "basic performance information.\n\n"
                "Maximum sessions: 10",
                style="primary",
            ),
            title=" START TEST ",
        )
        self._pause()

        target = url or self._ask_target()
        if target is None:
            return
        self._last_target = target

        if not self._confirm_authorization(target, assume_authorized=assume_authorized):
            self._line("{} Test cancelled.".format(SYMBOLS.WARNING), "warning")
            return

        count = sessions if sessions is not None else self._ask_sessions()
        if count is None:
            return

        self._run_test(target, count)

    def _ask_target(self) -> Optional[str]:
        """Prompt until a valid HTTP(S) URL is entered (or empty = cancel)."""
        while True:
            raw = self._ask("Enter authorized test URL")
            if not raw.strip():
                self._line("{} Cancelled.".format(SYMBOLS.WARNING), "warning")
                return None
            result = validate_url(raw)
            if result.ok:
                return result.url
            self.error_panel(result.reason, result.hint)

    def _confirm_authorization(self, target: str, assume_authorized: bool = False) -> bool:
        """The TARGET SAFETY CHECK (PRD 5)."""
        body = Text()
        body.append("Target:\n", style="muted")
        body.append("  {}\n".format(target), style="accent bold")
        body.append("\n{}".format(TARGET_LABEL), style="success")
        if is_authorized_scope(target):
            body.append("  (local/development target detected)\n", style="muted")
        body.append(
            "\nUse this tool only on a website you own\n"
            "or have explicit permission to test.",
            style="warning",
        )
        self._panel(body, title=" TARGET SAFETY CHECK ")

        if assume_authorized:
            self._line("{} Authorization confirmed via --yes flag.".format(SYMBOLS.INFO), "muted")
            return True
        while True:
            choice = self._ask("[1] authorized  [2] cancel")
            if choice.strip() in ("1", ""):
                return True
            if choice.strip() == "2":
                return False
            self.error_panel("Invalid choice", "Enter 1 to confirm or 2 to cancel.")

    def _ask_sessions(self) -> Optional[int]:
        """Prompt for the session count, enforcing 1-10 with clear errors."""
        cap = self.config.settings.max_sessions
        while True:
            raw = Prompt.ask(
                Text("Number of test sessions (1-{})".format(cap), style="accent"),
                console=self.console,
            )
            if not raw.strip():
                self._line("{} Cancelled.".format(SYMBOLS.WARNING), "warning")
                return None
            try:
                return parse_session_count(raw, hard_max=cap)
            except SessionLimitError as exc:
                self.error_panel("Invalid value", str(exc))

    def _run_test(self, target: str, sessions: int) -> None:
        """Run the engine under the live dashboard, then report + save."""
        step_sequence(
            self.console,
            self.animations,
            ["Initializing...", "Loading browser...", "Preparing sessions..."],
            done_text="Environment ready",
        )

        tracker = LiveTracker(sessions, target)
        browser = BrowserManager(
            headless=self.config.settings.browser_headless,
            slow_mo_ms=0,
        )
        engine = TestEngine(
            browser_manager=browser,
            settings=self.config.settings,
            tracker=tracker,
        )
        metrics = None
        try:
            with LiveDashboard(self.console, self.theme, self.animations.enabled) as dashboard:
                dashboard.attach(tracker)
                metrics = engine.run(target, sessions)
        except BrowserError as exc:
            self.error_panel("Browser initialization failed", str(exc))
            return
        finally:
            browser.stop()

        if metrics is None:
            return
        self._finish_test(target, metrics)

    def _finish_test(self, target: str, metrics) -> None:
        """Completion panel (PRD 10), report export and history entry."""
        summary = metrics.summary()
        test_id = next_test_id(storage.load_history())
        written = export_report(build_report(test_id, target, metrics, self.config.settings.actions))
        storage.append_history(
            {
                "test_id": test_id,
                "target": target,
                "sessions": summary["sessions"],
                "success": summary["successful"],
                "failed": summary["failed"],
                "status": summary["status"],
                "started_at": (metrics.started_at.isoformat(timespec="seconds") if metrics.started_at else ""),
                "finished_at": (metrics.finished_at.isoformat(timespec="seconds") if metrics.finished_at else ""),
                "report_files": {fmt: path.name for fmt, path in written.items()},
            }
        )

        compact = compact_mode()
        rows = Text()
        rows.append(" Test ID       : {}\n".format(test_id), style="accent bold")
        rows.append(" Target        : {}\n".format(target))
        rows.append(" Sessions      : {}\n".format(summary["sessions"]))
        rows.append(" Successful    : {}\n".format(summary["successful"]))
        rows.append(" Failed        : {}\n".format(summary["failed"]))
        if not compact:
            rows.append("\n")
            rows.append(" Avg Latency   : {}\n".format(format_ms(summary["avg_latency_ms"])))
            rows.append(" Max Latency   : {}\n".format(format_ms(summary["max_latency_ms"])))
            rows.append(" Min Latency   : {}\n".format(format_ms(summary["min_latency_ms"])))
        rows.append("\n Total Time    : {}\n".format(format_seconds(summary["total_duration_s"])))
        self._panel(rows, title=" TEST COMPLETE ", style="success")

        for fmt, path in written.items():
            self._line("{} Report saved: {}".format(SYMBOLS.SUCCESS, path), "muted")
        self._line()
        if summary["status"] == "FAIL":
            self._line(
                "{} All sessions failed. The target could not be reached - check it is running.".format(SYMBOLS.WARNING),
                "warning",
            )
        self._line("What next? Open [4] Reports to view details, or [3] Test History.", "muted")

    # ----------------------------------------------------------- LIVE DASHBOARD

    def live_dashboard_info(self) -> None:
        section_title(self.console, self.theme, "Live Dashboard")
        self._panel(
            Text(
                "The live dashboard appears automatically while a test\n"
                "is running (option [1] Start Test).\n\n"
                "It shows target, session progress, page status, actions,\n"
                "events and latency metrics in real time.",
                style="primary",
            ),
            title=" LIVE DASHBOARD ",
        )
        self._pause()

    # ---------------------------------------------------------------- HISTORY

    def history_flow(self) -> None:
        section_title(self.console, self.theme, "Test History")
        history = storage.load_history()
        if not history:
            self._panel(
                Text("No tests have been run yet.\n\nStart one with menu option [1].", style="muted"),
                title=" TEST HISTORY ",
            )
            return
        self.console.print(history_table(history, self.theme, compact=compact_mode()))
        self._line()
        self._line("Enter a Test ID to view its report (or press ENTER to go back).", "muted")
        test_id = self._ask("Test ID")
        if not test_id.strip():
            return
        entry = next((e for e in history if str(e.get("test_id", "")).upper() == test_id.strip().upper()), None)
        if entry is None:
            self.error_panel("Not found", "No test with ID {}.".format(test_id.strip()))
            return
        self._show_history_entry(entry)

    def _show_history_entry(self, entry: Dict) -> None:
        path = storage.history_report_path(entry, "json")
        if path is None:
            path = storage.history_report_path(entry, "txt")
        if path is None:
            self.error_panel("Report missing", "The report file for {} is no longer on disk.".format(entry.get("test_id")))
            return
        report = read_report(path) if path.suffix == ".json" else None
        if report is not None:
            summary = report.get("summary", {}) or {}
            rows = Text()
            rows.append(" Test ID     : {}\n".format(report.get("test_id")))
            rows.append(" Target      : {}\n".format((report.get("meta") or {}).get("target")))
            rows.append(" Date        : {}\n".format((report.get("meta") or {}).get("started_at")))
            rows.append(" Sessions    : {} ({} ok / {} failed)\n".format(
                summary.get("sessions"), summary.get("successful"), summary.get("failed")))
            rows.append(" Status      : {}\n".format(summary.get("status")))
            rows.append(" Avg Latency : {}\n".format(format_ms(summary.get("avg_latency_ms"))))
            rows.append(" Total Time  : {}\n".format(format_seconds(summary.get("total_duration_s"))))
            self._panel(rows, title=" REPORT ")
        else:
            self.console.print(Text(path.read_text(encoding="utf-8")))
        self._pause()

    # ---------------------------------------------------------------- REPORTS

    def reports_flow(self) -> None:
        section_title(self.console, self.theme, "Reports")
        reports = list_reports()
        if not reports:
            self._panel(
                Text("No reports yet.\n\nReports are generated automatically after each test.", style="muted"),
                title=" REPORTS ",
            )
            return
        id_re = re.compile(r"^(WB-\d{4}-\d{4})")
        rows = []
        for path, fmt in reports[:20]:
            match = id_re.match(path.name)
            rows.append({"test_id": match.group(1) if match else "--", "format": fmt.upper(), "file": path.name})
        self.console.print(report_table(rows, self.theme))
        self._line()
        self._line("Reports are stored in: {}".format(storage.reports_dir()), "muted")
        self._pause()

    # ---------------------------------------------------------------- SETTINGS

    def settings_flow(self) -> None:
        while True:
            section_title(self.console, self.theme, "Settings")
            settings = self.config.settings
            rows = Text()
            rows.append(" [1] UI Theme              : {}\n".format(settings.theme))
            rows.append(" [2] Animation Speed       : {}{}\n".format(
                settings.animation_speed, "" if settings.animation else " (animations OFF)"))
            rows.append(" [3] Default Session Limit : {} (hard max 10)\n".format(settings.max_sessions))
            rows.append(" [4] Browser Mode          : {}\n".format("headless" if settings.browser_headless else "visible"))
            rows.append(" [5] Reset Settings\n")
            rows.append(" [0] Back\n", style="muted")
            self._panel(rows, title=" SETTINGS ")
            choice = self._ask("Setting")
            if choice == "0" or not choice.strip():
                return
            if choice == "1":
                self._pick_theme()
            elif choice == "2":
                self._pick_animation()
            elif choice == "3":
                self._pick_session_limit()
            elif choice == "4":
                settings.browser_headless = not settings.browser_headless
                self.config.save()
                self.success_panel("Saved", "Browser mode: {}".format("headless" if settings.browser_headless else "visible"))
            elif choice == "5":
                self.config.reset()
                self._reload_style()
                self.success_panel("Reset", "Settings restored to defaults.")
            else:
                self.error_panel("Invalid option", "Choose 1-5 or 0 to go back.")

    def _pick_theme(self) -> None:
        names = " / ".join(THEMES)
        choice = self._ask("Theme ({})".format(names)).strip().lower()
        if choice in THEMES:
            self.config.settings.theme = choice
            self.config.save()
            self._reload_style()
            self.success_panel("Saved", "Theme set to {}.".format(choice))
        else:
            self.error_panel("Invalid theme", "Available: {}".format(names))

    def _pick_animation(self) -> None:
        choice = self._ask("Animation ON/OFF").strip().lower()
        if choice in ("on", "off"):
            self.config.settings.animation = choice == "on"
            if choice == "on":
                speed = self._ask("Speed ({})".format(" / ".join(ANIMATION_SPEEDS))).strip().lower()
                if speed in ANIMATION_SPEEDS:
                    self.config.settings.animation_speed = speed
                else:
                    self.error_panel("Invalid speed", "Using '{}'.".format(self.config.settings.animation_speed))
            self.config.save()
            # Recreate the controller so the speed string maps to a proper
            # multiplier (never assigned raw).
            self._reload_style()
            self.success_panel("Saved", "Animation: {} ({})".format(
                "ON" if self.config.settings.animation else "OFF",
                self.config.settings.animation_speed))
        else:
            self.error_panel("Invalid value", "Enter ON or OFF.")

    def _pick_session_limit(self) -> None:
        raw = self._ask("Default session limit (1-10)")
        try:
            value = parse_session_count(raw)
        except SessionLimitError as exc:
            self.error_panel("Invalid value", str(exc))
            return
        self.config.settings.max_sessions = value
        self.config.save()
        self.success_panel("Saved", "Default session limit: {} (hard maximum stays 10).".format(value))

    def _reload_style(self) -> None:
        self.theme = ThemeManager(self.config.settings.theme)
        self.animations = AnimationController(
            enabled=self.config.settings.animation,
            speed=self.config.settings.animation_speed,
        )

    # ------------------------------------------------------------------- HELP

    def help_flow(self) -> None:
        section_title(self.console, self.theme, "Help")
        body = Text()
        body.append("WebBehaviorLab is an educational web testing lab.\n\n", style="primary")
        body.append("Getting started\n", style="accent bold")
        body.append(" 1. Start a local test server (e.g. python -m http.server 8000)\n")
        body.append(" 2. Choose [1] Start Test\n")
        body.append(" 3. Enter http://127.0.0.1:8000 and confirm you are authorized\n")
        body.append(" 4. Pick 1-10 sessions and watch the live dashboard\n\n", )
        body.append("Symbols\n", style="accent bold")
        body.append(" {} Success   {} Error\n {} Warning   {} Running\n {} Pending\n\n".format(
            SYMBOLS.SUCCESS, SYMBOLS.ERROR, SYMBOLS.WARNING, SYMBOLS.RUNNING, SYMBOLS.PENDING))
        body.append("Safety\n", style="accent bold")
        body.append(" Only test websites you own or have explicit\n permission to test. Maximum 10 sessions per run.\n")
        self._panel(body, title=" HELP ")
        self._line("Commands: webbehavior start | history | reports | settings | doctor | version", "muted")
        self._line("Docs: see the docs/ folder in the repository.", "muted")
        self._pause()
