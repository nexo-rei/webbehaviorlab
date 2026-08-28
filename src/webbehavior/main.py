"""Application entry point and CLI routing.

``webbehavior``          -> interactive menu
``webbehavior start``    -> start a test (options below)
``webbehavior history``  -> show test history
``webbehavior reports``  -> list exported reports
``webbehavior settings`` -> open settings
``webbehavior help``     -> usage help
``webbehavior version``  -> print version
``webbehavior doctor``   -> environment health check
"""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from webbehavior.config import Config
from webbehavior.core.limiter import SessionLimitError, parse_session_count
from webbehavior.core.validator import validate_url
from webbehavior.monitoring.logger import write_diagnostic
from webbehavior.ui.menu import App
from webbehavior.ui.theme import SYMBOLS, ThemeManager, build_rich_theme
from webbehavior.utils import storage
from webbehavior.utils.system import doctor_checks
from webbehavior.version import __version__

__all__ = ["main", "build_parser", "run_doctor"]


def build_console() -> Console:
    """Console configured with the user's theme."""
    settings = Config().settings
    manager = ThemeManager(settings.theme)
    return Console(theme=build_rich_theme(manager))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="webbehavior",
        description="WebBehaviorLab - educational web automation & behavior testing lab",
    )
    sub = parser.add_subparsers(dest="command")

    start = sub.add_parser("start", help="start a test against an authorized target")
    start.add_argument("--url", help="authorized target URL (http/https)")
    start.add_argument("--sessions", type=int, default=None, help="number of sessions (1-10)")
    start.add_argument(
        "--yes",
        action="store_true",
        help="confirm you are authorized to test the target (skips the prompt)",
    )

    sub.add_parser("history", help="show test history")
    sub.add_parser("reports", help="list exported reports")
    sub.add_parser("settings", help="open settings")
    sub.add_parser("help", help="show usage help")
    sub.add_parser("version", help="print version")
    sub.add_parser("doctor", help="check the environment (Python, deps, browser, storage)")
    return parser


def run_doctor(console: Console) -> int:
    """The ``webbehavior doctor`` health check (PRD 17)."""
    console.print()
    console.print(Text("WebBehaviorLab Doctor", style="accent bold"))
    console.print()
    results = doctor_checks()
    failed = 0
    for result in results:
        style = "success" if result.ok else "error"
        line = Text()
        line.append("  ")
        line.append("{:<16}".format(result.name), style="primary")
        line.append("{} ".format(result.symbol), style=style)
        if result.detail and result.ok:
            line.append("({})".format(result.detail), style="muted")
        elif result.detail:
            failed += 1
            line.append(result.detail.splitlines()[0], style="muted")
        console.print(line)

    console.print()
    if any(not r.ok for r in results):
        console.print(Text("{} System is NOT ready - fix the items above.".format(SYMBOLS.ERROR), style="error"))
        console.print(Text("  Hint: bash install.sh  |  webbehavior help", style="muted"))
        return 1
    console.print(Text("{} System is ready.".format(SYMBOLS.SUCCESS), style="success"))
    return 0


def _cmd_version(console: Console) -> int:
    console.print("WebBehaviorLab v{} (Termux/Linux edition)".format(__version__))
    return 0


def _cmd_help(console: Console) -> int:
    text = Text()
    text.append("WebBehaviorLab v{}\n".format(__version__), style="accent bold")
    text.append("Educational web automation & behavior testing lab.\n\n", style="muted")
    text.append("Usage\n", style="accent bold")
    text.append("  webbehavior             interactive menu\n")
    text.append("  webbehavior start       start a test (--url URL --sessions N --yes)\n")
    text.append("  webbehavior history     show previous tests\n")
    text.append("  webbehavior reports     list exported reports\n")
    text.append("  webbehavior settings    open settings\n")
    text.append("  webbehavior doctor      check your environment\n")
    text.append("  webbehavior version     print the version\n\n")
    text.append("Safety\n", style="accent bold")
    text.append("  Use only on systems you own or are authorized to test.\n")
    text.append("  Maximum 10 sessions per run (hard limit).\n")
    console.print(Panel(text, border_style="cyan", title=" HELP "))
    return 0


def _cmd_start(console: Console, args: argparse.Namespace) -> int:
    app = App(console)
    url: Optional[str] = args.url
    if url is not None:
        result = validate_url(url)
        if not result.ok:
            app.error_panel(result.reason, result.hint)
            return 2
        url = result.url
    sessions = args.sessions
    if sessions is not None:
        try:
            sessions = parse_session_count(str(sessions))
        except SessionLimitError as exc:
            app.error_panel("Invalid value", str(exc))
            return 2
    try:
        app.start_test_flow(url=url, sessions=sessions, assume_authorized=bool(args.yes))
        return 0
    except KeyboardInterrupt:
        return 130


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point with global, beginner-friendly error handling."""
    argv = list(sys.argv[1:] if argv is None else argv)
    console = build_console()
    storage.ensure_dirs()

    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command is None:
            return App(console).run()
        if args.command == "doctor":
            return run_doctor(console)
        if args.command == "version":
            return _cmd_version(console)
        if args.command == "help":
            return _cmd_help(console)
        if args.command == "start":
            return _cmd_start(console, args)
        if args.command == "history":
            return App(console).history_flow() or 0
        if args.command == "reports":
            return App(console).reports_flow() or 0
        if args.command == "settings":
            return App(console).settings_flow() or 0
        parser.error("unknown command {!r}".format(args.command))
        return 2
    except KeyboardInterrupt:
        console.print(Text("\n{} Stopped by user.".format(SYMBOLS.WARNING), style="warning"))
        return 130
    except SystemExit:
        raise
    except Exception as exc:  # PRD 16: unexpected exceptions never crash
        error_id = write_diagnostic(exc)
        console.print()
        console.print(
            Panel(
                Text(
                    "Something went wrong.\n\nError ID: {}\nA safe diagnostic log was created.".format(error_id),
                    style="error",
                ),
                title="[{}] UNEXPECTED ERROR ".format(SYMBOLS.ERROR),
                border_style="red",
            )
        )
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
