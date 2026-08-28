# Installation

WebBehaviorLab installs on Termux (Android) and Linux. The installer is
**idempotent** — safe to run repeatedly; it only fixes what is missing.

## Requirements

| Requirement | Minimum | Check |
|---|---|---|
| Python | 3.8 | `python3 --version` |
| pip | any recent | `python3 -m pip --version` |
| Disk space | ~600 MB with a browser | — |
| Network | needed once for dependencies | — |

## Termux (Android)

```bash
pkg update && pkg upgrade
pkg install python git
git clone https://github.com/nexo-rei/webbehaviorlab.git
cd webbehaviorlab
bash install.sh
```

Termux notes:

- Playwright cannot download its bundled Chromium on Android, so the
  installer uses the Termux Chromium package (`pkg install chromium`)
  automatically.
- If your device is low on space, Chromium is the big item — the rest of
  the app is small.

## Linux

```bash
git clone https://github.com/nexo-rei/webbehaviorlab.git
cd webbehaviorlab
bash install.sh
```

The installer:

1. checks Python ≥ 3.8 and pip,
2. creates (or reuses) a virtual environment at `.venv/`,
3. installs `rich`, `playwright` and WebBehaviorLab itself,
4. finds or downloads a Chromium browser,
5. creates the application directories under `~/.webbehavior/`,
6. installs the `webbehavior` command into `~/.local/bin` (or `$PREFIX/bin`
   on Termux),
7. runs a health check (`webbehavior doctor`).

If `~/.local/bin` is not on your PATH, the installer tells you the exact
line to add to your `~/.bashrc`.

## Verifying the installation

```bash
webbehavior version   # prints e.g. "WebBehaviorLab v1.0.0"
webbehavior doctor    # all checks should show ✓
```

```text
WebBehaviorLab Doctor

  Python          ✓ (v3.11.2)
  Rich            ✓ (v13.x)
  Playwright      ✓
  Browser         ✓ (/usr/bin/chromium)
  Storage         ✓ (/home/you/.webbehavior)

✓ System is ready.
```

## Manual installation (without install.sh)

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/python -m playwright install chromium   # Linux; on Termux: pkg install chromium
.venv/bin/webbehavior doctor
```

To make the command global:

```bash
mkdir -p ~/.local/bin && ln -s "$PWD/.venv/bin/webbehavior" ~/.local/bin/webbehavior
```

## Using a specific browser

If you have Chromium/Chrome in a non-standard location:

```bash
export WEBBEHAVIOR_BROWSER_PATH=/path/to/chrome
webbehavior doctor
```

## Uninstallation

```bash
bash uninstall.sh
```

You will be asked whether local reports, settings and history should be
deleted too. The repository folder itself is never removed automatically.

## Troubleshooting

See [troubleshooting.md](troubleshooting.md) or run
`webbehavior doctor` — its hints point at the exact fix for each failed
check.
