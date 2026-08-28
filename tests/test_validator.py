"""Tests for URL validation (PRD 25: validator).

valid HTTP URL, valid HTTPS URL, invalid URL, empty input and unsupported
protocol, plus credential rejection and localhost detection.
"""

from __future__ import annotations

import pytest

from webbehavior.core.validator import (
    TARGET_LABEL,
    normalize_url,
    target_info,
    validate_url,
)
from webbehavior.utils.network import is_local_target


class TestValidUrls:
    @pytest.mark.parametrize(
        "url",
        [
            "http://127.0.0.1:8000/",
            "http://localhost:8000/",
            "http://localhost:3000/",
            "https://example.com/",
            "https://my-site.example.com/some/page",
            "http://10.0.0.5:8080/app",
        ],
    )
    def test_accepted(self, url: str) -> None:
        result = validate_url(url)
        assert result.ok, result.reason

    def test_valid_http(self) -> None:
        assert validate_url("http://127.0.0.1:8000/").ok

    def test_valid_https(self) -> None:
        assert validate_url("https://example.com/").ok

    def test_result_carries_normalized_url(self) -> None:
        result = validate_url("http://example.com")
        assert result.ok
        assert result.url == "http://example.com/"


class TestInvalidUrls:
    def test_empty_input(self) -> None:
        result = validate_url("")
        assert not result.ok
        assert "valid HTTP/HTTPS URL" in result.hint

    def test_whitespace_only(self) -> None:
        assert not validate_url("   ").ok

    def test_plain_word(self) -> None:
        assert not validate_url("hello").ok

    def test_missing_host(self) -> None:
        assert not validate_url("http:///path").ok

    def test_url_with_spaces(self) -> None:
        assert not validate_url("http://exa mple.com/").ok


class TestUnsupportedProtocols:
    @pytest.mark.parametrize(
        "url",
        [
            "ftp://example.com/file",
            "file:///etc/passwd",
            "javascript:alert(1)",
            "data:text/html,hello",
            "chrome://settings",
        ],
    )
    def test_rejected(self, url: str) -> None:
        result = validate_url(url)
        assert not result.ok
        assert "protocol" in result.reason.lower() or "url" in result.reason.lower()

    def test_reason_is_unsupported_protocol(self) -> None:
        result = validate_url("ftp://example.com/")
        assert result.reason == "Unsupported protocol"


class TestCredentialsRejected:
    def test_userinfo_rejected(self) -> None:
        result = validate_url("http://user:pass@example.com/")
        assert not result.ok
        assert "credential" in result.reason.lower()


class TestNormalization:
    def test_bare_localhost_gets_http(self) -> None:
        assert normalize_url("localhost:8000") == "http://localhost:8000/"

    def test_bare_domain_gets_https(self) -> None:
        assert normalize_url("example.com") == "https://example.com/"

    def test_trailing_slash_added(self) -> None:
        assert normalize_url("http://127.0.0.1:8000") == "http://127.0.0.1:8000/"

    def test_none_for_garbage(self) -> None:
        assert normalize_url("") is None
        assert normalize_url("not a url") is None


class TestTargetInfo:
    def test_localhost_flag(self) -> None:
        info = target_info("http://127.0.0.1:8000/")
        assert info is not None
        assert info.is_local is True
        assert info.label == TARGET_LABEL

    def test_remote_flag(self) -> None:
        info = target_info("https://example.com/")
        assert info is not None
        assert info.is_local is False

    def test_display_host(self) -> None:
        info = target_info("http://localhost:8000/")
        assert info is not None
        assert info.display == "localhost:8000"


class TestLocalDetection:
    @pytest.mark.parametrize(
        "url",
        [
            "http://127.0.0.1:8000/",
            "http://localhost:3000/",
            "http://[::1]:8080/",
            "http://192.168.1.10/",
            "http://10.0.0.5:8080/",
            "http://myapp.test/",
            "http://staging.local/",
        ],
    )
    def test_local(self, url: str) -> None:
        assert is_local_target(url)

    def test_remote(self) -> None:
        assert not is_local_target("https://example.com/")
