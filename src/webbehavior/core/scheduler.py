"""Session plan / pacing for a test run.

The scheduler yields session numbers 1..N (N already limited by
:class:`webbehavior.core.limiter`) and inserts a small, fixed pause between
sessions so a test remains gentle on the target even at the maximum of 10
sessions. This pacing is intentional and cannot be reduced to zero via
configuration.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Iterator

from webbehavior.core.limiter import HARD_MAX_SESSIONS, MIN_SESSIONS, validate_session_count

MIN_INTER_SESSION_DELAY_S = 0.25  # safety pacing floor


@dataclass
class SessionPlan:
    """An immutable, pre-validated plan for a test run."""

    target: str
    sessions: int
    inter_session_delay_s: float

    def __post_init__(self) -> None:
        self.sessions = validate_session_count(self.sessions)
        self.inter_session_delay_s = max(self.inter_session_delay_s, MIN_INTER_SESSION_DELAY_S)

    def __iter__(self) -> Iterator[int]:
        for index in range(1, self.sessions + 1):
            yield index
            if index < self.sessions:
                time.sleep(self.inter_session_delay_s)

    @property
    def summary(self) -> str:
        return "{} session(s) against {}".format(self.sessions, self.target)


def build_plan(target: str, sessions: int, inter_session_delay_s: float = 0.5) -> SessionPlan:
    """Create a validated :class:`SessionPlan`.

    ``sessions`` is re-validated here (backend enforcement) even if the UI
    already checked it.
    """
    return SessionPlan(
        target=target,
        sessions=validate_session_count(sessions, hard_max=HARD_MAX_SESSIONS),
        inter_session_delay_s=inter_session_delay_s,
    )
