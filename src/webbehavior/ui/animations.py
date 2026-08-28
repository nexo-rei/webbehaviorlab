"""Lightweight animation helpers.

All animations honor the ``animation`` setting (PRD 15): when disabled,
every helper degrades to a plain, instant print. Speeds map to multipliers
so slow devices can pick ``fast`` (shorter delays) or users who enjoy the
polish can pick ``slow``.
"""

from __future__ import annotations

import time
from typing import Iterable, Optional

from rich.console import Console
from rich.status import Status
from rich.text import Text

from webbehavior.ui.theme import SYMBOLS

__all__ = ["AnimationController", "animated_status", "step_sequence"]

SPEED_MULTIPLIERS = {"slow": 1.6, "normal": 1.0, "fast": 0.45}


class AnimationController:
    """Central switch + speed for every animation in the app."""

    def __init__(self, enabled: bool = True, speed: str = "normal") -> None:
        self.enabled = bool(enabled)
        self.speed = SPEED_MULTIPLIERS.get(speed, 1.0)

    @property
    def delay(self) -> float:
        return 0.05 * self.speed

    def sleep(self, units: float = 1.0) -> None:
        if self.enabled:
            time.sleep(self.delay * units)

    def line_reveal(self, console: Console, lines: Iterable[str], style: str = "primary") -> None:
        """Print lines one-by-one (skipped instantly when disabled)."""
        for line in lines:
            console.print(Text(line, style=style))
            self.sleep(0.8)

    def status(self, console: Console, message: str, spinner: str = "dots") -> "_StatusProxy":
        """Spinner context manager; instant text when animations are off."""
        return _StatusProxy(console, message, self.enabled, spinner)


class _StatusProxy:
    """Wraps rich.status.Status, degrading gracefully in non-TTY/disabled mode."""

    def __init__(self, console: Console, message: str, enabled: bool, spinner: str) -> None:
        self._console = console
        self._message = message
        self._enabled = enabled and console.is_terminal
        self._spinner = spinner
        self._status: Optional[Status] = None

    def __enter__(self) -> "_StatusProxy":
        if self._enabled:
            self._status = Status(self._message, spinner=self._spinner, console=self._console)
            self._status.start()
        else:
            self._console.print("{} {}...".format(SYMBOLS.RUNNING, self._message))
        return self

    def update(self, message: str) -> None:
        self._message = message
        if self._status is not None:
            self._status.update(message)
        else:
            self._console.print("{} {}...".format(SYMBOLS.RUNNING, message))

    def __exit__(self, *exc_info: object) -> None:
        if self._status is not None:
            self._status.stop()


def animated_status(console: Console, message: str, animations: AnimationController,
                    spinner: str = "dots") -> _StatusProxy:
    """Convenience wrapper for one-off use."""
    return animations.status(console, message, spinner=spinner)


def step_sequence(console: Console, animations: AnimationController,
                  steps: Iterable[str], done_text: Optional[str] = None) -> None:
    """Show 'Initializing... / Loading... / Done' style sequences."""
    with animations.status(console, next(iter(steps), "Working")) as status:
        for step in steps:
            status.update(step)
            animations.sleep(6)
    if done_text:
        console.print(Text("{} {}".format(SYMBOLS.SUCCESS, done_text), style="success"))
