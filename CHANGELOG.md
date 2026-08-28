# Changelog

All notable changes to WebBehaviorLab are documented here.
The format follows [Semantic Versioning](https://semver.org/) ideas:
`MAJOR.MINOR.PATCH`, with Added / Changed / Fixed / Removed / Security
sections per release.

## [1.0.0] — 2026-08-28

First public release.

### Added

- **Termux CLI** — `webbehavior` command with interactive menu and
  subcommands (`start`, `history`, `reports`, `settings`, `help`,
  `version`, `doctor`)
- **Browser testing** — Playwright-based test browser with lifecycle
  management, honest automation (no anti-bot evasion), per-session
  isolated contexts and guaranteed cleanup
- **Predefined test actions** — `page_load`, `wait`, `scroll_down`,
  `scroll_up`, `click_test_element`, `return_to_top`, `page_end`;
  configurable via `config/default.json`
- **Live dashboard** — real-time panel with progress bar, current-session
  stages, response status, events and latency metrics; compact mode for
  narrow terminals; graceful plain-text fallback when piped
- **Reports** — JSON and TXT exports with sequential test IDs
  (`WB-YYYY-NNNN`), stored under `~/.webbehavior/reports/`
- **Test history** — persistent index with PASS/PARTIAL/FAIL status and
  in-app report viewer
- **Safety limits** — hard maximum of 10 sessions per run, enforced in
  backend code (`core/limiter.py`); cannot be raised via settings, config
  files, or CLI arguments
- **Target validation & authorization** — HTTP/HTTPS-only URL validation,
  credential-in-URL rejection, localhost/private-network detection, and a
  mandatory TARGET SAFETY CHECK confirmation
- **Configuration system** — layered defaults (`config/default.json`) and
  user settings (`~/.webbehavior/config/settings.json`) with safety
  clamping
- **Settings UI** — theme, animation speed, default session limit,
  browser mode (headless/visible), reset
- **Animations** — spinners, progress bars and step sequences, all
  optional (can be disabled for slow devices)
- **Doctor** — environment health check (Python, rich, Playwright,
  browser, storage)
- **Safe logging** — rotating local logs with password/token/cookie
  scrubbing and sanitized `ERR-XXXX` diagnostic files
- **Installer/uninstaller** — idempotent `install.sh` with Termux
  detection, `uninstall.sh` with confirmation prompts, and `run.sh`
- **Documentation** — README, SECURITY, CONTRIBUTING, this changelog,
  custom restrictive LICENSE, and the `docs/` guide set
- **Test suite** — 115 pytest tests covering the limiter, validator,
  configuration, metrics, reports, log scrubbing, and the full engine
  pipeline against a real localhost server

[1.0.0]: https://github.com/nexo-rei/webbehaviorlab/releases/tag/v1.0.0
