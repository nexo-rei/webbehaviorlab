"""Predefined, authorized test actions.

Actions are small, transparent behaviors used to exercise an authorized
target: page load, wait, scroll down/up, click a test element, return to
top, jump to page end. They exist to test functionality and performance -
NOT to imitate organic visitors, inflate views or evade bot detection
(those capabilities are intentionally absent).

The action list is configurable (``config/default.json`` -> ``actions``)
and unknown names are rejected at load time.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from webbehavior.monitoring.logger import get_logger

__all__ = ["ACTION_NAMES", "ActionOutcome", "ActionExecutor", "validate_action_names"]

logger = get_logger("actions")

TEST_ELEMENT_SELECTORS = (
    "#wbl-test-button",
    "[data-wbl-test]",
    "#test-button",
    "button",
)


@dataclass
class ActionOutcome:
    """Result of executing one action in one session."""

    name: str
    executed: bool
    detail: str = ""

    @property
    def label(self) -> str:
        return self.name.replace("_", " ").upper()


def _page_url(page) -> str:  # pragma: no cover - trivial helper
    try:
        return page.url
    except Exception:
        return ""


def _safe_evaluate(page, script: str):
    """Run *script* in the page, returning None on any failure."""
    try:
        return page.evaluate(script)
    except Exception as exc:  # page may have navigated away mid-test
        logger.debug("evaluate failed (%s): %s", script[:40], type(exc).__name__)
        return None


class ActionExecutor:
    """Executes a configurable list of actions against one open page."""

    def __init__(self, action_delay_ms: int = 400) -> None:
        self.delay_s = max(action_delay_ms, 0) / 1000.0
        self.registry: Dict[str, Callable[..., ActionOutcome]] = {
            "page_load": self._action_page_load,
            "wait": self._action_wait,
            "scroll_down": self._action_scroll_down,
            "scroll_up": self._action_scroll_up,
            "click_test_element": self._action_click_test_element,
            "return_to_top": self._action_return_to_top,
            "page_end": self._action_page_end,
        }

    # -- public API -------------------------------------------------------

    def run(self, page, actions: List[str], target: Optional[str] = None) -> List[ActionOutcome]:
        """Execute *actions* in order on *page*; never raises."""
        outcomes: List[ActionOutcome] = []
        for name in actions:
            handler = self.registry.get(name)
            if handler is None:
                outcomes.append(ActionOutcome(name, False, "unknown action"))
                continue
            try:
                outcome = handler(page, target=target)
            except Exception as exc:
                outcome = ActionOutcome(name, False, type(exc).__name__)
            outcomes.append(outcome)
            if self.delay_s:
                time.sleep(self.delay_s)
        return outcomes

    # -- individual actions -------------------------------------------------

    def _action_page_load(self, page, target: Optional[str] = None) -> ActionOutcome:
        if target:
            page.goto(target, wait_until="domcontentloaded")
            return ActionOutcome("page_load", True, _page_url(page))
        return ActionOutcome("page_load", False, "no target")

    def _action_wait(self, page, target: Optional[str] = None) -> ActionOutcome:
        # A short, fixed wait - demonstrates timing measurement. Kept small
        # so tests stay quick and gentle on the target.
        page.wait_for_timeout(int(self.delay_s * 1000) or 250)
        return ActionOutcome("wait", True, "short pause")

    def _action_scroll_down(self, page, target: Optional[str] = None) -> ActionOutcome:
        height = _safe_evaluate(page, "document.body.scrollHeight")
        step = max((height or 800) // 4, 200)
        _safe_evaluate(page, f"window.scrollBy(0, {int(step)})")
        return ActionOutcome("scroll_down", True, f"+{int(step)}px")

    def _action_scroll_up(self, page, target: Optional[str] = None) -> ActionOutcome:
        _safe_evaluate(page, "window.scrollBy(0, -300)")
        return ActionOutcome("scroll_up", True, "-300px")

    def _action_click_test_element(self, page, target: Optional[str] = None) -> ActionOutcome:
        """Click the page's designated test element, if it provides one.

        Sites that want to participate can add ``<button data-wbl-test>``.
        Otherwise the generic first ``<button>`` is tried, and if the page
        has no button at all the action is *skipped* (not failed).
        """
        for selector in TEST_ELEMENT_SELECTORS:
            try:
                locator = page.locator(selector).first
                if locator.count() == 0:
                    continue
                locator.click(timeout=1500)
                return ActionOutcome("click_test_element", True, selector)
            except Exception:
                continue
        return ActionOutcome("click_test_element", False, "no test element (skipped)")

    def _action_return_to_top(self, page, target: Optional[str] = None) -> ActionOutcome:
        _safe_evaluate(page, "window.scrollTo(0, 0)")
        return ActionOutcome("return_to_top", True)

    def _action_page_end(self, page, target: Optional[str] = None) -> ActionOutcome:
        _safe_evaluate(page, "window.scrollTo(0, document.body.scrollHeight)")
        return ActionOutcome("page_end", True)


ACTION_NAMES = tuple(sorted(ActionExecutor().registry.keys()))


def validate_action_names(names: List[str]) -> List[str]:
    """Filter *names* down to known actions (unknown names dropped + logged)."""
    valid = [n for n in names if n in ActionExecutor().registry]
    dropped = [n for n in names if n not in valid]
    if dropped:
        logger.warning("Dropping unknown actions: %s", ", ".join(dropped))
    return valid
