# Getting Started

Welcome! This guide takes you from zero to your first completed test in
about five minutes. You never need to open a Python file.

## What you need

- A phone with [Termux](https://termux.dev) or any Linux machine
- Python 3.8 or newer
- About 5 minutes

Not installed yet? See [installation.md](installation.md) first.

## Step 0 — Launch the app

```bash
webbehavior
```

You will see the banner and the main menu:

```text
[1] Start Test
[2] Live Dashboard
[3] Test History
[4] Reports
[5] Settings
[6] Help
[0] Exit
```

Navigate by typing a number and pressing ENTER.

## Step 1 — Start a local test website

The safest way to learn is a website that runs on your own device. From
the repository folder:

```bash
python -m http.server 8000 --directory assets/demo
```

This serves the bundled demo page at `http://127.0.0.1:8000/`. Leave it
running in another Termux session or terminal tab.

## Step 2 — Start a test

In WebBehaviorLab choose `[1] Start Test`.

**What happens:** the app explains what a test does (opens your page,
records performance information) and reminds you of the 10-session
maximum.

**Why:** you should never run something against a website without knowing
what it does.

### Enter the URL

```text
Enter authorized test URL:
> http://127.0.0.1:8000/
```

Missing the `http://`? The app adds it for you. Something invalid?
You get a clear error and can try again — nothing crashes.

### The safety check

```text
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

Press `1` to continue or `2` to cancel. This confirmation appears for
**every** test — it is the core of responsible use.

### Choose the session count

```text
Number of test sessions (1-10):
> 3
```

Type any number from 1 to 10. Larger values are rejected:

```text
✗ Invalid value
Maximum allowed sessions: 10
Please enter a value between 1 and 10.
```

## Step 3 — Watch the live dashboard

While the test runs you will see the dashboard update in real time: the
progress bar fills, the current session's stages tick from `→` to `✓`,
and metrics recalculate after every session.

See [dashboard.md](dashboard.md) for a full tour.

## Step 4 — Read the results

```text
╭──────────── TEST COMPLETE ────────────╮

 Test ID       : WB-2026-0001
 Sessions      : 3
 Successful    : 3
 Failed        : 0

 Avg Latency   : 42 ms
 Max Latency   : 61 ms
 Min Latency   : 33 ms

 Total Time    : 6.9 sec

╰───────────────────────────────────────╯
```

Two report files were just saved:

- `~/.webbehavior/reports/WB-2026-0001-….json` (machine-readable)
- `~/.webbehavior/reports/WB-2026-0001-….txt` (human-readable)

## Step 5 — Explore

- `[3] Test History` — list every run; enter a Test ID to view its report
- `[4] Reports` — browse the report files themselves
- `[5] Settings` — try the themes, turn animations off, set your default
  session limit
- `webbehavior doctor` — check that everything is healthy

## What to try next

1. **Actions** — add `"page_end"` or `"click_test_element"` to your
   action list in Settings → see [configuration.md](configuration.md)
2. **A slow page** — add a big file to your test folder and watch latency
   change
3. **A failure** — stop your local server (`Ctrl+C`) and run a test: all
   sessions fail gracefully and the report shows why

## Safety reminder

Every target you test must be yours or explicitly authorized. When in
doubt: don't test it.
