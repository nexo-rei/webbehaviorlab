# Troubleshooting

Start here when something goes wrong. The most useful command:

```bash
webbehavior doctor
```

It checks Python, dependencies, the browser and storage, and prints a
hint next to anything failing.

## Installation

### `Python 3 was not found`

```bash
# Termux
pkg install python
# Debian/Ubuntu
sudo apt install python3 python3-pip python3-venv
```

### `Could not create the virtual environment`

```bash
# Termux
pkg install python-venv
# Debian/Ubuntu
sudo apt install python3-venv
```

Then re-run `bash install.sh` — it will repair the environment.

### Dependency download fails

Check your connection, then:

```bash
.venv/bin/pip install -e .
```

You can re-run `bash install.sh` as many times as needed; it skips what
is already healthy.

## Browser problems

### `✗ Browser initialization failed`

The Playwright package is fine but no Chromium was found.

```bash
# Termux
pkg install chromium
# Linux
.venv/bin/python -m playwright install chromium
```

Custom browser location:

```bash
export WEBBEHAVIOR_BROWSER_PATH=/path/to/chrome
webbehavior doctor    # should now show Browser ✓
```

### Doctor says `Browser ✗ no Chromium found`

Same fix as above. Everything else can be ✓ while the browser is missing —
the menu, history, reports and settings all work without it; only
*starting a test* needs a browser.

### Chromium is slow to launch on Android

Normal on low-end devices. The first session includes launch time in its
duration; later sessions reuse the same browser process.

## Testing problems

### All sessions fail with connection errors

The target is not reachable:

```text
✗ Connection failed
The target could not be reached.
Check the URL and network connection.
```

1. Is your server running? (`python -m http.server 8000`)
2. Right port? `http://127.0.0.1:8000` — the port must match.
3. From Termux, prefer `127.0.0.1` over `localhost` if resolution is odd.

### `✗ Invalid URL`

Enter a full HTTP(S) URL:

```text
http://127.0.0.1:8000/
https://example.com/
```

Rejected on purpose: `ftp://`, `file://`, `javascript:`, URLs with
`user:pass@`, URLs with spaces.

### Sessions rejected above 10

```text
✗ Invalid value
Maximum allowed sessions: 10
```

This is by design (see [SECURITY.md](../SECURITY.md)). The limit cannot
be raised — not by settings, config, or command line.

## Interface problems

### `webbehavior: command not found`

```bash
bash install.sh        # recreates the command
# or run without installing:
bash run.sh
```

If `~/.local/bin` is not on your PATH:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### UI flickers or feels slow

`[5] Settings → [2] Animation Speed → OFF`, and consider the `minimal`
theme. On terminals without color, `high-contrast` reads best.

### Layout looks cramped

The UI auto-enables **compact mode** under 70 columns. To gain width in
Termux: pinch-zoom out, or reduce the font size in Termux settings.

### An unexpected error appeared (Error ID: ERR-XXXX)

Something unexpected happened; the app kept running. A sanitized log was
saved at:

```text
~/.webbehavior/logs/diagnostics/ERR-XXXX.log
```

It contains no secrets (URLs are reduced to scheme://host:port and
sensitive values are scrubbed). Feel free to open it, and please report
the Error ID in a GitHub issue.

## Logs and data

| What | Where |
|---|---|
| App log | `~/.webbehavior/logs/webbehavior.log` (rotating) |
| Diagnostics | `~/.webbehavior/logs/diagnostics/` |
| Reports | `~/.webbehavior/reports/` |
| History | `~/.webbehavior/history.json` |
| Settings | `~/.webbehavior/config/settings.json` |

Reset everything to defaults: `[5] Settings → [5] Reset Settings`.

Still stuck? See [faq.md](faq.md) or open an issue.
