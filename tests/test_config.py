"""Tests for configuration loading and safety clamping (PRD 22)."""

from __future__ import annotations

import json

import pytest

from webbehavior.config import Config, Settings
from webbehavior.core.limiter import HARD_MAX_SESSIONS


@pytest.fixture()
def isolated_home(tmp_path, monkeypatch):
    """Point storage at a temp HOME so tests never touch real user data."""
    home = tmp_path / "webbehavior-home"
    monkeypatch.setenv("WEBBEHAVIOR_HOME", str(home))
    return home


class TestDefaults:
    def test_defaults_load(self, isolated_home) -> None:
        config = Config()
        assert config.settings.max_sessions == HARD_MAX_SESSIONS
        assert config.settings.animation is True
        assert config.settings.browser_headless is True
        assert config.settings.page_load_timeout_ms == 30000
        assert "page_load" in config.settings.actions

    def test_actions_are_usable(self, isolated_home) -> None:
        from webbehavior.browser.actions import ACTION_NAMES

        settings = Config().settings
        assert set(settings.actions) <= set(ACTION_NAMES)


class TestSafetyClamping:
    def test_max_sessions_never_exceeds_hard_limit(self, isolated_home) -> None:
        settings = Settings(max_sessions=999)
        assert settings.max_sessions == HARD_MAX_SESSIONS == 10

    def test_hand_edited_settings_file_cannot_raise_limit(self, isolated_home) -> None:
        from webbehavior.utils import storage

        storage.ensure_dirs()
        path = isolated_home / "config" / "settings.json"
        path.write_text(json.dumps({"max_sessions": 100}), encoding="utf-8")
        config = Config()
        assert config.settings.max_sessions == 10

    def test_settings_file_can_lower_limit(self, isolated_home) -> None:
        from webbehavior.utils import storage

        storage.ensure_dirs()
        path = isolated_home / "config" / "settings.json"
        path.write_text(json.dumps({"max_sessions": 3}), encoding="utf-8")
        config = Config()
        assert config.settings.max_sessions == 3

    def test_invalid_values_fall_back(self, isolated_home) -> None:
        settings = Settings(max_sessions=0)
        assert settings.max_sessions == 1

    def test_timeout_clamped(self, isolated_home) -> None:
        settings = Settings(page_load_timeout_ms=999999)
        assert settings.page_load_timeout_ms <= 120000

    def test_unknown_theme_falls_back(self, isolated_home) -> None:
        assert Settings(theme="neon").theme == "default"


class TestPersistence:
    def test_save_and_reload_roundtrip(self, isolated_home) -> None:
        config = Config()
        config.settings.animation = False
        config.settings.theme = "minimal"
        config.save()
        reloaded = Config().settings
        assert reloaded.animation is False
        assert reloaded.theme == "minimal"

    def test_corrupt_settings_fall_back_to_defaults(self, isolated_home) -> None:
        from webbehavior.utils import storage

        storage.ensure_dirs()
        (isolated_home / "config" / "settings.json").write_text("{not json", encoding="utf-8")
        config = Config()
        assert config.settings.max_sessions == 10

    def test_reset(self, isolated_home) -> None:
        config = Config()
        config.settings.animation = False
        config.settings.max_sessions = 2
        config.save()
        restored = config.reset()
        assert restored.animation is True
        assert restored.max_sessions == 10
