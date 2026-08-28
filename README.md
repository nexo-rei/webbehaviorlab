# WebBehaviorLab

**An educational web automation & behavior testing lab for Termux and Linux.**

```text
╭────────────────────────────────────────────╮
│                                            │
│       W E B   B E H A V I O R   L A B      │
│              TERMUX EDITION                │
│                                            │
│       Educational Testing Environment      │
│                                            │
╰────────────────────────────────────────────╯
```

> ⚠️ **Disclaimer**
> WebBehaviorLab is intended for **educational purposes and authorized
> testing only**. Do not use it against websites or systems without
> permission.

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Features](#2-features)
3. [Screenshots](#3-screenshots)
4. [Installation](#4-installation)
5. [Quick Start](#5-quick-start)
6. [Commands](#6-commands)
7. [Configuration](#7-configuration)
8. [Architecture](#8-architecture)
9. [Safety & Authorized Use](#9-safety--authorized-use)
10. [Troubleshooting](#10-troubleshooting)
11. [Contributing](#11-contributing)
12. [License](#12-license)

---

## 1. Introduction

WebBehaviorLab is a **beginner-friendly, terminal-based laboratory** for
learning how websites behave. It helps you understand, hands-on:

- HTTP requests and response codes
- Browser automation (with Playwright)
- Page loading and navigation timing
- Browser events (loads, console messages, requests)
- Session behavior and response times
- Basic web performance testing
- How automation appears to a website (detection *concepts* — not evasion)
- Logging, metrics and reporting

You do **not** need to know Python to use it. Type `webbehavior`, pick an
option from the menu, and follow the prompts. Everything is explained as
it happens: what is happening, why it is happening, and what to do next.

### Who is this for?

- Students learning how the web works
- Developers testing **their own** local or staging sites
- Self-learners exploring browser automation safely
- Teachers demonstrating web performance concepts

### What it is NOT

This is **not** a traffic bot, view inflator, CAPTCHA solver, proxy
rotator, or anti-bot evasion tool — and it will never become one. Those
functions are intentionally absent. See [Safety](#9-safety--authorized-use).

---

## 2. Features

| Feature | Description |
|---|---|
| **Guided test runs** | Menu-driven flow from URL entry to final report |
| **Hard safety limit** | Maximum **10 sessions per run**, enforced in backend code — cannot be raised via settings |
| **Authorization check** | Every test requires an explicit "I am authorized" confirmation |
| **Local-first** | Built for `localhost` / `127.0.0.1` test servers and staging targets you own |
| **Live dashboard** | Real-time progress, per-session status, latency metrics |
| **Metrics** | HTTP status, response time, page-load duration, success/failure counts, events |
| **Reports** | JSON + TXT reports saved locally, with test IDs like `WB-2026-0001` |
| **History** | Browse previous runs, view past reports |
| **Settings** | Themes, animation speed, session limit, browser mode |
| **Doctor** | One-command environment health check |
| **Animations** | Spinners and progress that can be turned OFF for slow devices |
| **Responsive UI** | Compact mode for small phone screens |
| **Safe logging** | Passwords, tokens, cookies and credentials are scrubbed from all logs |

---

## 3. Screenshots

The interface is rendered with [rich](https://github.com/Textualize/rich).
See [`assets/screenshots/`](assets/screenshots/) for captured examples.

```text
╭────────────── LIVE TEST ──────────────╮

 Target       : localhost:8000
 Sessions     : 03 / 05
 Status       : RUNNING

 Progress:
━━━━━━━━━━━━━━━━━━━━━━░░░░ 60%

 Current Session
 ├─ Browser        ✓
 ├─ Page Load      ✓
 ├─ Response       200 OK
 ├─ Test Actions   ✓
 ├─ Events         8
 └─ Duration       4.31 sec

 Metrics
 ├─ Avg Latency    284 ms
 ├─ Success        3
 └─ Failed         0

╰───────────────────────────────────────╯
```

---

## 4. Installation

### Termux (Android)

```bash
pkg update && pkg install python git
git clone https://github.com/nexo-rei/webbehaviorlab.git
cd webbehaviorlab
bash install.sh
```

The installer detects Termux, installs Chromium via `pkg`, and creates the
`webbehavior` command.

### Linux

```bash
git clone https://github.com/nexo-rei/webbehaviorlab.git
cd webbehaviorlab
bash install.sh
```

Requirements: **Python 3.8+** and pip. Everything else is handled for you.
The installer is **idempotent** — you can run it again safely; it will only
repair what is missing.

After installing:

```text
╭──────────────────────────────╮
│   Installation Complete ✓    │
╰──────────────────────────────╯
```

More detail: [`docs/installation.md`](docs/installation.md)

---

## 5. Quick Start

**1. Start a local test website** (any of these works):

```bash
python -m http.server 8000        # serves the current folder
# or use the bundled demo page:
python -m http.server 8000 --directory assets/demo
```

**2. Launch WebBehaviorLab:**

```bash
webbehavior
```

**3. Choose `[1] Start Test` and follow the prompts:**

```text
Enter authorized test URL:
> http://127.0.0.1:8000/

TARGET SAFETY CHECK
────────────────────
Target:
  http://127.0.0.1:8000/
AUTHORIZED TEST TARGET  (local/development target detected)

Use this tool only on a website you own
or have explicit permission to test.

[1] I am authorized to test this target
[2] Cancel
```

**4. Pick the number of sessions (1–10):**

```text
Number of test sessions (1-10):
> 5
```

Asking for 50 is rejected with a clear message:

```text
✗ Invalid value
Maximum allowed sessions: 10
Please enter a value between 1 and 10.
```

**5. Watch the live dashboard, then read the completion panel:**

```text
╭──────────── TEST COMPLETE ────────────╮

 Test ID       : WB-2026-0001
 Sessions      : 5
 Successful    : 5
 Failed        : 0

 Avg Latency   : 284 ms
 Max Latency   : 412 ms
 Min Latency   : 221 ms

 Total Time    : 24.6 sec

╰───────────────────────────────────────╯
```

Reports are saved to `~/.webbehavior/reports/`. Open `[3] Test History`
or `[4] Reports` in the menu to review them.

Full walkthrough: [`docs/getting-started.md`](docs/getting-started.md)

---

## 6. Commands

| Command | What it does |
|---|---|
| `webbehavior` | Open the interactive menu |
| `webbehavior start` | Start a test (add `--url URL --sessions N --yes`) |
| `webbehavior history` | Show previous tests |
| `webbehavior reports` | List generated reports |
| `webbehavior settings` | Open settings (theme, animations, limits) |
| `webbehavior help` | Usage help |
| `webbehavior version` | Print the version |
| `webbehavior doctor` | Check Python, dependencies, browser, storage |

Example of a one-line authorized local test:

```bash
webbehavior start --url http://127.0.0.1:8000/ --sessions 3 --yes
```

(`--yes` confirms you are authorized; the interactive menu always asks.)

---

## 7. Configuration

Defaults live in [`config/default.json`](config/default.json):

```json
{
  "max_sessions": 10,
  "animation": true,
  "browser": { "headless": true },
  "timeouts": { "page_load_ms": 30000 }
}
```

Your personal settings are saved to `~/.webbehavior/config/settings.json`
(from the `[5] Settings` menu). You can also edit the file directly.

**Important:** the maximum session count can never be raised above 10
through configuration. The hard limit lives in the code
(`src/webbehavior/core/limiter.py`) and clamps every setting, file, or
command-line value back to 10.

Details: [`docs/configuration.md`](docs/configuration.md)

---

## 8. Architecture

```text
src/webbehavior/
├── main.py            entry point + CLI routing
├── config.py          layered settings with safety clamping
├── core/              validator, limiter (hard max), sessions, scheduler, engine
├── browser/           Playwright manager, launcher, actions, safe events
├── ui/                banner, menu, theme, animations, progress, tables, dashboard
├── monitoring/        live tracker, metrics, secret-scrubbing logger
├── reports/           generator (WB-IDs), exporter (JSON/TXT), templates
└── utils/             network, system, storage, helpers
```

Key safety decisions:

- `core/limiter.py` — the single source of truth for the 10-session ceiling
- `core/validator.py` — HTTP/HTTPS only, credentials rejected, localhost detection
- `monitoring/logger.py` — sensitive values are scrubbed before writing
- `browser/` — honest automation; no fingerprint spoofing or detection evasion

Deep dive: [`docs/architecture.md`](docs/architecture.md)

---

## 9. Safety & Authorized Use

**Use WebBehaviorLab only on:**

- localhost and local test servers
- staging environments you control
- websites you own
- websites whose owners gave you explicit permission to test

**Never use it to:**

- inflate views, clicks, or analytics on third-party sites
- bypass CAPTCHA or bot detection
- attack systems or perform credential attacks
- hide automated traffic from anyone

The tool enforces its own guardrails: a hard 10-session limit, mandatory
authorization confirmation, URL validation, request pacing, and no
proxy/stealth features. Attempting to use it against systems you are not
authorized to test may be **illegal** in your jurisdiction.

If you believe you found a security issue in WebBehaviorLab itself, see
[`SECURITY.md`](SECURITY.md) for responsible disclosure.

---

## 10. Troubleshooting

| Symptom | Fix |
|---|---|
| `✗ Browser initialization failed` | Run `webbehavior doctor`. On Termux: `pkg install chromium`. On Linux: `playwright install chromium` |
| `✗ Invalid URL` | Use full `http://` or `https://` URLs, e.g. `http://127.0.0.1:8000` |
| `✗ Connection failed` / all sessions fail | The target is not running. Start it and test again |
| `webbehavior: command not found` | Re-run `bash install.sh`, or use `bash run.sh` |
| UI feels slow / flickery | `[5] Settings → [2] Animation Speed → OFF`, or pick a minimal theme |
| Weird layout on a small screen | The UI auto-enables compact mode below 70 columns; rotate or reduce font |
| `System is NOT ready` (doctor) | Follow the hint printed next to the failing check |

More: [`docs/troubleshooting.md`](docs/troubleshooting.md) and
[`docs/faq.md`](docs/faq.md)

---

## 11. Contributing

Contributions are welcome — especially documentation improvements, new
**safe** test actions, and Termux compatibility fixes.

```bash
git clone https://github.com/nexo-rei/webbehaviorlab.git
cd webbehaviorlab
bash install.sh
source .venv/bin/activate
pytest              # run the test suite
```

Read [`CONTRIBUTING.md`](CONTRIBUTING.md) for the workflow, coding
standards, and the safety review every PR goes through.

---

## 12. License

WebBehaviorLab uses a **custom restrictive license** — it is *not* MIT,
Apache, or GPL.

In short: personal use, educational use, running the software, authorized
testing, and learning from the code are all allowed. Selling, commercial
redistribution, publishing modified versions, rebranding, and removing
attribution are **not allowed** without written permission from the
copyright holder.

👉 **Read the actual license text: [`LICENSE`](LICENSE)** — this summary is
not a substitute for the license itself. The license has not been reviewed
by a lawyer; no claim is made that it is enforceable in every jurisdiction.

---

*Symbols used throughout the app:* `✓` success · `✗` error · `⚠` warning · `→` running · `○` pending
