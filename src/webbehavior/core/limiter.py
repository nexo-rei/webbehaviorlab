"""Hard safety boundary for the number of test sessions.

This module is the SINGLE source of truth for the maximum number of test
sessions. The limit is a deliberate safety boundary so the tool can never be
turned into a traffic generator: no configuration file, setting or caller can
raise ``HARD_MAX_SESSIONS``. User settings may only lower it.

Example
-------
    >>> from webbehavior.core.limiter import validate_session_count
    >>> validate_session_count(5)
    5
    >>> validate_session_count(50)
    Traceback (most recent call last):
        ...
    webbehavior.core.limiter.SessionLimitError: Maximum allowed sessions: 10
"""

from __future__ import annotations

from typing import Union

__all__ = [
    "HARD_MAX_SESSIONS",
    "MIN_SESSIONS",
    "SessionLimitError",
    "validate_session_count",
    "parse_session_count",
]

# SAFETY BOUNDARY - do not change. The application must never allow more
# than HARD_MAX_SESSIONS test sessions in a single run, regardless of any
# user configuration. See PRD section 4.1 / 12 / 22.
HARD_MAX_SESSIONS = 10
MIN_SESSIONS = 1


class SessionLimitError(ValueError):
    """Raised when a requested session count is outside the allowed range."""

    def __init__(self, value: Union[int, str], reason: str) -> None:
        self.value = value
        self.reason = reason
        super().__init__(reason)


def validate_session_count(value: int, hard_max: int = HARD_MAX_SESSIONS) -> int:
    """Validate and return an allowed session count (1..hard_max).

    ``hard_max`` may only ever be <= HARD_MAX_SESSIONS; anything larger is
    clamped back to the hard maximum so callers cannot widen the boundary.

    Raises
    ------
    SessionLimitError
        With a beginner-friendly message when the value is rejected.
    """
    effective_max = min(hard_max, HARD_MAX_SESSIONS)
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise SessionLimitError(
            value, "Please enter a whole number between 1 and {}.".format(effective_max)
        ) from None

    if number < MIN_SESSIONS:
        raise SessionLimitError(
            number,
            "Minimum allowed sessions: {}\n"
            "Please enter a value between {} and {}.".format(MIN_SESSIONS, MIN_SESSIONS, effective_max),
        )
    if number > effective_max:
        raise SessionLimitError(
            number,
            "Maximum allowed sessions: {}\n"
            "Please enter a value between {} and {}.".format(effective_max, MIN_SESSIONS, effective_max),
        )
    return number


def parse_session_count(text: str, hard_max: int = HARD_MAX_SESSIONS) -> int:
    """Parse user input (a string) into an allowed session count.

    Empty input is rejected rather than defaulted, so users always make an
    explicit choice about how much testing to perform.
    """
    stripped = (text or "").strip()
    if not stripped:
        raise SessionLimitError(
            text or "",
            "Please enter a value between {} and {}.".format(MIN_SESSIONS, min(hard_max, HARD_MAX_SESSIONS)),
        )
    try:
        number = int(stripped)
    except ValueError:
        raise SessionLimitError(
            stripped, "Please enter a whole number between 1 and {}.".format(min(hard_max, HARD_MAX_SESSIONS))
        ) from None
    return validate_session_count(number, hard_max=hard_max)
