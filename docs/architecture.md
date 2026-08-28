# Architecture

WebBehaviorLab is a modular Python application: one responsibility per
module, no circular imports, and a strict safety core that the UI cannot
bypass.

```text
src/webbehavior/
├── main.py               entry point, CLI routing, global error handling
├── __main__.py           python -m webbehavior
├── config.py             layered settings + safety clamping
├── version.py            single source of the version
│
├── core/                 the safety + orchestration core
│   ├── validator.py      URL validation, protocol rules, authorization
│   ├── limiter.py        HARD_MAX_SESSIONS = 10 (the safety boundary)
│   ├── session.py        SessionResult, SessionStatus, timers
│   ├── scheduler.py      session plan + mandatory pacing
│   └── engine.py         the test workflow orchestrator
│
├── browser/              Playwright integration
│   ├── manager.py        browser lifecycle, one context per session
│   ├── launcher.py       executable detection (Termux-aware), options
│   ├── actions.py        the predefined safe test actions
│   └── events.py         safe event counting (no content capture)
│
├── ui/                   rich terminal interface
│   ├── banner.py         startup banner
│   ├── menu.py           interactive flows (start, history, settings…)
│   ├── theme.py          palettes + status symbols
│   ├── animations.py     spinners/sequences, disableable
│   ├── progress.py       progress bars
│   ├── tables.py         history/report tables (compact-aware)
│   └── dashboard.py      the live test dashboard
│
├── monitoring/
│   ├── tracker.py        thread-safe live state + subscriptions
│   ├── metrics.py        latency/success/failure statistics
│   └── logger.py         secret-scrubbing logger + diagnostics
│
├── reports/
│   ├── generator.py      report dict + WB-YYYY-NNNN ids
│   ├── exporter.py       JSON/TXT writers, safe filenames
│   └── templates.py      plain-text layout
│
└── utils/
    ├── network.py        URL parsing helpers, localhost detection
    ├── system.py         platform/terminal detection, doctor checks
    ├── storage.py        ~/.webbehavior layout, history index
    └── helpers.py        small pure helpers
```

## The test workflow

```text
menu / CLI
   │ validated URL + confirmed authorization + session count (1–10)
   ▼
TestEngine.run(target, sessions)
   │  build_plan()          → re-validates the count against the hard max
   │  BrowserManager.start() → one Chromium for the whole run
   │  for session in plan:  (paced; ≥0.25 s between sessions)
   │     ├─ new isolated context + page
   │     ├─ EventRecorder.attach(page)          (counts only)
   │     ├─ browser.load(url) → status + response time
   │     ├─ ActionExecutor.run(page, actions)   (configurable, safe set)
   │     ├─ navigation timing from the page itself
   │     └─ SessionResult → MetricsCollector
   │  BrowserManager.stop()                     (always, even on error)
   ▼
build_report() → export_report() → ~/.webbehavior/reports/ + history.json
```

Progress flows to the UI through two decoupled channels: the
`LiveTracker` (state snapshot, rendered by the dashboard) and optional
`on_event` callbacks. The engine never imports the UI, so it runs
headlessly in tests.

## Dependency injection

`TestEngine` accepts any object with `start/stop/session/load` — the test
suite injects a `FakeBrowser` that speaks real HTTP via urllib against a
live localhost server. That lets CI verify the entire pipeline (engine →
tracker → metrics → reports) without Chromium.

## Safety model

| Guarantee | Mechanism |
|---|---|
| Max 10 sessions | `HARD_MAX_SESSIONS` constant; every path funnels through `validate_session_count()`, which clamps any caller-supplied ceiling to 10 |
| Config can't widen it | `Settings.clamp()` runs on load *and* save |
| Authorized targets only | menu enforces the TARGET SAFETY CHECK; CLI requires `--yes` |
| http/https only | `validator.validate_url` rejects other schemes + embedded credentials |
| Gentle pacing | `scheduler.MIN_INTER_SESSION_DELAY_S = 0.25` floor |
| Honest automation | launcher passes no stealth/anti-detection flags; no proxy support exists |
| No secrets in logs | `logger.scrub_sensitive()` on every record; URLs reduced to host:port |
| No shell injection | no `os.system`/`shell=True` anywhere; filenames sanitized |
| Timeouts everywhere | page load timeout, bounded waits, cleanup in `finally` |
| Crash-safe UX | global handler writes sanitized `ERR-XXXX` diagnostics instead of tracebacks |

## Data layout

`~/.webbehavior/` (or `$WEBBEHAVIOR_HOME`):

```text
config/settings.json   user settings
logs/webbehavior.log   rotating app log (512 KB × 3)
logs/diagnostics/      ERR-XXXX files for unexpected exceptions
reports/               WB-YYYY-NNNN-*.json / *.txt
history.json           index of runs (bounded to 500 entries)
```

## Performance notes

- One browser process per run; contexts are cheap and isolated.
- The dashboard refreshes at 4 fps and prints nothing when piped.
- Logs rotate; the history index is capped; reports are plain files.
- Startup imports only stdlib + rich — Playwright is imported lazily by
  the browser layer.

## Extending safely

New **action** → add a method to `ActionExecutor`, register it in
`registry`, document it in `docs/configuration.md`, add a test. Actions
must exercise the page, never disguise traffic.

New **report format** (CSV/HTML) → implement in `exporter.py` using the
same report dict from `generator.py`; keep `templates.py` for layout.

Anything that would add proxy rotation, detection evasion, or remove a
safety check does not belong here — see SECURITY.md.
