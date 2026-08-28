"""Tests for safe logging / secret scrubbing (PRD 23/24)."""

from __future__ import annotations

from webbehavior.monitoring.logger import safe_url_for_log, scrub_sensitive
from webbehavior.utils import storage


class TestScrubSensitive:
    def test_password_key_redacted(self) -> None:
        data = {"password": "hunter2", "user": "alice"}
        cleaned = scrub_sensitive(data)
        assert cleaned["password"] == "[REDACTED]"
        assert cleaned["user"] == "alice"

    def test_token_and_cookie_redacted(self) -> None:
        cleaned = scrub_sensitive(
            {"access_token": "abc", "cookies": {"sid": 1}, "Authorization": "x"}
        )
        assert cleaned["access_token"] == "[REDACTED]"
        assert cleaned["cookies"] == "[REDACTED]"
        assert cleaned["Authorization"] == "[REDACTED]"

    def test_nested_redaction(self) -> None:
        cleaned = scrub_sensitive({"session_data": {"api_key": "k", "name": "ok"}})
        assert cleaned["session_data"]["api_key"] == "[REDACTED]"
        assert cleaned["session_data"]["name"] == "ok"
        cleaned2 = scrub_sensitive({"credentials": {"user": "u", "pass": "p"}})
        assert cleaned2["credentials"] == "[REDACTED]"

    def test_bearer_in_string_redacted(self) -> None:
        cleaned = scrub_sensitive("Authorization: Bearer abcdefghijklmno")
        assert "abcdefghijklmno" not in cleaned
        assert "[REDACTED]" in cleaned

    def test_plain_data_untouched(self) -> None:
        cleaned = scrub_sensitive({"target": "http://127.0.0.1:8000/", "sessions": 3})
        assert cleaned == {"target": "http://127.0.0.1:8000/", "sessions": 3}


class TestSafeUrl:
    def test_query_string_removed(self) -> None:
        assert safe_url_for_log("http://127.0.0.1:8000/x?token=secret") == "http://127.0.0.1:8000/x"

    def test_invalid_url(self) -> None:
        assert safe_url_for_log("not a url") == "[invalid-url]"


class TestStorageSafety:
    def test_safe_filename_blocks_traversal(self) -> None:
        assert ".." not in storage.safe_filename("../../etc/passwd")
        assert "/" not in storage.safe_filename("a/b/c")

    def test_safe_filename_fallback(self) -> None:
        assert storage.safe_filename("///") == "untitled"

    def test_history_roundtrip(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setenv("WEBBEHAVIOR_HOME", str(tmp_path))
        storage.append_history({"test_id": "WB-2026-0001", "status": "PASS"})
        history = storage.load_history()
        assert len(history) == 1
        assert history[0]["test_id"] == "WB-2026-0001"
        storage.clear_history()
        assert storage.load_history() == []
