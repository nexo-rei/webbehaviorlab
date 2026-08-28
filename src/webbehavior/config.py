"""Configuration loading and persistence.

Layered configuration (later wins):

1. Built-in defaults (mirrored in ``config/default.json`` in the repository),
2. the repository's ``config/default.json`` when present,
3. user settings at ``~/.webbehavior/config/settings.json``.

SAFETY: the hard maximum session count (10) lives in
``webbehavior.core.limiter`` and can NEVER be raised through configuration -
``Settings.max_sessions`` is clamped to the hard maximum on every load and
save. Configuration may only *lower* the default.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from webbehavior.core.limiter import HARD_MAX_SESSIONS, MIN_SESSIONS
from webbehavior.utils import storage

__all__ = ["Settings", "Config", "DEFAULT_ACTIONS", "ANIMATION_SPEEDS", "THEMES"]

ANIMATION_SPEEDS = ("slow", "normal", "fast")
THEMES = ("default", "high-contrast", "minimal")

DEFAULT_ACTIONS: List[str] = [
    "page_load",
    "wait",
    "scroll_down",
    "scroll_up",
    "return_to_top",
]

_REPO_DEFAULT_JSON = Path(__file__).resolve().parents[2] / "config" / "default.json"

_BUILTIN_DEFAULTS: Dict[str, Any] = {
    "max_sessions": HARD_MAX_SESSIONS,
    "animation": True,
    "animation_speed": "normal",
    "theme": "default",
    "browser": {"headless": True},
    "timeouts": {"page_load_ms": 30000},
    "pacing": {"inter_session_delay_ms": 800, "action_delay_ms": 400},
    "actions": list(DEFAULT_ACTIONS),
}


@dataclass
class Settings:
    """Typed application settings."""

    max_sessions: int = HARD_MAX_SESSIONS
    animation: bool = True
    animation_speed: str = "normal"
    theme: str = "default"
    browser_headless: bool = True
    page_load_timeout_ms: int = 30000
    inter_session_delay_ms: int = 800
    action_delay_ms: int = 400
    actions: List[str] = field(default_factory=lambda: list(DEFAULT_ACTIONS))

    def __post_init__(self) -> None:
        self.clamp()

    def clamp(self) -> None:
        """Enforce safety boundaries and normalize enum-ish values.

        Out-of-range values are *silently clamped* here (never raised) so a
        hand-edited settings file can never crash the app or widen the
        session limit.
        """
        # The hard maximum cannot be exceeded even if a settings file was
        # hand-edited to say otherwise.
        try:
            requested = int(self.max_sessions)
        except (TypeError, ValueError):
            requested = HARD_MAX_SESSIONS
        self.max_sessions = max(MIN_SESSIONS, min(requested, HARD_MAX_SESSIONS))

        self.animation_speed = (
            self.animation_speed if self.animation_speed in ANIMATION_SPEEDS else "normal"
        )
        self.theme = self.theme if self.theme in THEMES else "default"
        self.browser_headless = bool(self.browser_headless)
        self.page_load_timeout_ms = max(2000, min(int(self.page_load_timeout_ms), 120000))
        self.inter_session_delay_ms = max(250, min(int(self.inter_session_delay_ms), 60000))
        self.action_delay_ms = max(100, min(int(self.action_delay_ms), 10000))
        seen: List[str] = []
        for action in self.actions:
            if action not in seen:
                seen.append(action)
        self.actions = seen

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Settings":
        """Build settings from a (possibly partial/unknown-key) mapping."""
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        cleaned = {k: v for k, v in (data or {}).items() if k in known}
        settings = cls(**cleaned)
        settings.clamp()
        return settings


class Config:
    """Load / save / reset user settings."""

    def __init__(self, settings_path: Optional[Path] = None) -> None:
        self.settings_path = settings_path or storage.config_dir() / "settings.json"
        self.settings = self.load()

    # -- loading --------------------------------------------------------

    def _defaults(self) -> Dict[str, Any]:
        merged = dict(_BUILTIN_DEFAULTS)
        if _REPO_DEFAULT_JSON.exists():
            try:
                merged.update(json.loads(_REPO_DEFAULT_JSON.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                pass
        return merged

    def load(self) -> Settings:
        """Load settings; corrupt or unsafe files fall back to defaults."""
        merged = self._defaults()
        user = storage.read_json(self.settings_path, default={})
        if isinstance(user, dict):
            merged.update(user)
        settings = Settings.from_dict(self._flatten(merged))
        settings.clamp()
        return settings

    @staticmethod
    def _flatten(data: Dict[str, Any]) -> Dict[str, Any]:
        """Flatten nested repo-config style JSON into Settings fields."""
        flat: Dict[str, Any] = {
            "max_sessions": data.get("max_sessions"),
            "animation": data.get("animation"),
            "animation_speed": data.get("animation_speed", data.get("animation", None)),
            "theme": data.get("theme"),
        }
        browser = data.get("browser") or {}
        if "headless" in browser:
            flat["browser_headless"] = browser["headless"]
        timeouts = data.get("timeouts") or {}
        if "page_load_ms" in timeouts or "page_load" in timeouts:
            flat["page_load_timeout_ms"] = timeouts.get("page_load_ms", timeouts.get("page_load"))
        pacing = data.get("pacing") or {}
        if "inter_session_delay_ms" in pacing:
            flat["inter_session_delay_ms"] = pacing["inter_session_delay_ms"]
        if "action_delay_ms" in pacing:
            flat["action_delay_ms"] = pacing["action_delay_ms"]
        if isinstance(data.get("actions"), list):
            flat["actions"] = data["actions"]
        return {k: v for k, v in flat.items() if v is not None}

    # -- persistence ----------------------------------------------------

    def save(self) -> Path:
        """Persist current settings to the user settings file."""
        payload = {
            "max_sessions": self.settings.max_sessions,
            "animation": self.settings.animation,
            "animation_speed": self.settings.animation_speed,
            "theme": self.settings.theme,
            "browser": {"headless": self.settings.browser_headless},
            "timeouts": {"page_load_ms": self.settings.page_load_timeout_ms},
            "pacing": {
                "inter_session_delay_ms": self.settings.inter_session_delay_ms,
                "action_delay_ms": self.settings.action_delay_ms,
            },
            "actions": list(self.settings.actions),
        }
        return storage.write_json(self.settings_path, payload)

    def reset(self) -> Settings:
        """Reset user settings to defaults and persist them."""
        try:
            self.settings_path.unlink(missing_ok=True)
        except OSError:
            pass
        self.settings = Settings.from_dict(self._flatten(self._defaults()))
        self.save()
        return self.settings
