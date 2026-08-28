# Configuration

WebBehaviorLab is configured in layers; later layers override earlier
ones:

1. **Built-in defaults** — compiled into the app (always present).
2. **Repository defaults** — [`config/default.json`](../config/default.json)
   in the project root.
3. **User settings** — `~/.webbehavior/config/settings.json`, written by
   the `[5] Settings` menu (and editable by hand).

## Reference

| Setting | Type | Default | Meaning |
|---|---|---|---|
| `max_sessions` | int | `10` | Default session cap for prompts (1–10) |
| `animation` | bool | `true` | Spinners/animated transitions ON/OFF |
| `animation_speed` | string | `"normal"` | `slow` · `normal` · `fast` |
| `theme` | string | `"default"` | `default` · `high-contrast` · `minimal` |
| `browser.headless` | bool | `true` | Run the browser without a window |
| `timeouts.page_load_ms` | int | `30000` | Max wait for a page to load (2 000–120 000) |
| `pacing.inter_session_delay_ms` | int | `800` | Pause between sessions (floor 250) |
| `pacing.action_delay_ms` | int | `400` | Pause between actions (floor 100) |
| `actions` | list | see below | Ordered list of test actions |

## Example user settings

```json
{
  "max_sessions": 5,
  "animation": true,
  "animation_speed": "fast",
  "theme": "minimal",
  "browser": { "headless": true },
  "timeouts": { "page_load_ms": 20000 },
  "pacing": { "inter_session_delay_ms": 1000, "action_delay_ms": 300 },
  "actions": ["page_load", "wait", "scroll_down", "page_end", "return_to_top"]
}
```

## Test actions

Available actions (in the order you define them):

| Action | What it does |
|---|---|
| `page_load` | (Re)load the target URL |
| `wait` | Short fixed pause — good for observing timing |
| `scroll_down` | Scroll down one viewport step |
| `scroll_up` | Scroll up a step |
| `click_test_element` | Click the page's test button (see below) |
| `return_to_top` | Scroll back to the top |
| `page_end` | Jump to the bottom of the page |

Unknown action names are dropped safely (with a log entry), never crash
the run.

### Making your page test-friendly

`click_test_element` looks for, in order:

1. `#wbl-test-button`
2. any element with `[data-wbl-test]`
3. `#test-button`
4. the first `<button>`

Add `<button data-wbl-test>Run test</button>` to your page so tests have
something deterministic to click. If nothing is found, the action is
recorded as *skipped*, not failed.

## The hard session limit (read this)

`max_sessions` only changes the **default shown in prompts**. The real
ceiling is:

```python
HARD_MAX_SESSIONS = 10   # src/webbehavior/core/limiter.py
```

Every path — settings files, config/default.json, CLI arguments, the
engine itself — validates against this constant. Editing your settings
file to `"max_sessions": 500` simply results in `10`. This is intentional:
the tool must stay an educational lab, not a traffic generator.

## Where things live

| Path | Purpose |
|---|---|
| `~/.webbehavior/config/settings.json` | your settings |
| `~/.webbehavior/reports/` | generated reports |
| `~/.webbehavior/logs/` | app log + sanitized diagnostics |
| `~/.webbehavior/history.json` | test history index |

Set the `WEBBEHAVIOR_HOME` environment variable to relocate all of it
(also used by the test suite).

## Environment variables

| Variable | Effect |
|---|---|
| `WEBBEHAVIOR_HOME` | Relocate the data directory |
| `WEBBEHAVIOR_BROWSER_PATH` | Explicit Chromium/Chrome executable |
| `PLAYWRIGHT_BROWSERS_PATH` | Where Playwright browsers live |
