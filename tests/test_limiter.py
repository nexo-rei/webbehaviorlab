"""Tests for the hard session limit (PRD 25: limiter).

1, 5, 10 accepted; 0, 11, 100 rejected - plus attempts to widen the
boundary, which must always fail.
"""

from __future__ import annotations

import pytest

from webbehavior.core.limiter import (
    HARD_MAX_SESSIONS,
    MIN_SESSIONS,
    SessionLimitError,
    parse_session_count,
    validate_session_count,
)


class TestAcceptedValues:
    @pytest.mark.parametrize("value", [1, 5, 10])
    def test_accepted(self, value: int) -> None:
        assert validate_session_count(value) == value

    def test_min_boundary(self) -> None:
        assert validate_session_count(MIN_SESSIONS) == MIN_SESSIONS

    def test_max_boundary(self) -> None:
        assert validate_session_count(HARD_MAX_SESSIONS) == HARD_MAX_SESSIONS


class TestRejectedValues:
    @pytest.mark.parametrize("value", [0, -1, 11, 50, 100, 1000])
    def test_rejected(self, value: int) -> None:
        with pytest.raises(SessionLimitError):
            validate_session_count(value)

    def test_error_message_mentions_maximum(self) -> None:
        with pytest.raises(SessionLimitError) as excinfo:
            validate_session_count(50)
        message = str(excinfo.value)
        assert "Maximum allowed sessions: 10" in message
        assert "between 1 and 10" in message

    def test_zero_message_mentions_minimum(self) -> None:
        with pytest.raises(SessionLimitError) as excinfo:
            validate_session_count(0)
        assert "Minimum allowed sessions" in str(excinfo.value)


class TestBoundaryCannotBeWidened:
    def test_hard_max_cannot_be_raised_via_argument(self) -> None:
        """A caller passing hard_max=99 must still be capped at 10."""
        with pytest.raises(SessionLimitError):
            validate_session_count(11, hard_max=99)

    def test_hard_max_constant(self) -> None:
        assert HARD_MAX_SESSIONS == 10

    def test_caller_may_lower_but_not_raise(self) -> None:
        assert validate_session_count(3, hard_max=5) == 3
        with pytest.raises(SessionLimitError):
            validate_session_count(7, hard_max=5)

    def test_scheduler_also_enforces(self) -> None:
        from webbehavior.core.scheduler import build_plan

        with pytest.raises(SessionLimitError):
            build_plan("http://127.0.0.1:8000/", sessions=11)

    def test_settings_cannot_raise_limit(self) -> None:
        from webbehavior.config import Settings

        settings = Settings(max_sessions=50)
        assert settings.max_sessions == 10


class TestParsing:
    def test_parse_valid(self) -> None:
        assert parse_session_count("5") == 5
        assert parse_session_count(" 10 \n") == 10

    @pytest.mark.parametrize("bad", ["", "  ", "abc", "1.5", "-3", "11", "0", "50"])
    def test_parse_invalid(self, bad: str) -> None:
        with pytest.raises(SessionLimitError):
            parse_session_count(bad)

    def test_parse_error_is_valueerror(self) -> None:
        with pytest.raises(ValueError):
            parse_session_count("nope")
