#!/usr/bin/env bash
#
# WebBehaviorLab installer (Termux / Linux).
#
# Safe, idempotent installation:
#   1. check Python + pip
#   2. create/reuse a local virtual environment
#   3. install Python dependencies
#   4. set up a Chromium browser for Playwright (Termux uses pkg chromium)
#   5. prepare application directories (~/.webbehavior)
#   6. create the `webbehavior` CLI command
#   7. run a basic health check
#
# Usage:  bash install.sh [--force]
#   --force  reinstall dependencies even if everything looks healthy
#
set -euo pipefail

# ---------------------------------------------------------------- pretty I/O
BOLD=$'\033[1m'; DIM=$'\033[2m'; GREEN=$'\033[32m'; RED=$'\033[31m'; CYAN=$'\033[36m'; OFF=$'\033[0m'
step()   { printf '%s\n' "${CYAN}→${OFF} $*"; }
ok()     { printf '%s\n' "${GREEN}✓${OFF} $*"; }
fail()   { printf '%s\n' "${RED}✗${OFF} $*" >&2; }
note()   { printf '%s\n' "${DIM}$*${OFF}"; }

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$REPO_DIR/.venv"
FORCE=0
[[ "${1:-}" == "--force" ]] && FORCE=1

# ---------------------------------------------------------------- environment
IS_TERMUX=0
if [[ -n "${TERMUX_VERSION:-}" || "${PREFIX:-}" == *com.termux* ]]; then
  IS_TERMUX=1
fi

banner() {
  cat <<'EOF'

  W E B B E H A V I O R   L A B
  installer · educational testing environment

EOF
}

banner
[[ $IS_TERMUX -eq 1 ]] && note "Detected environment: Termux (Android)" \
                       || note "Detected environment: Linux / Unix-like"

# ------------------------------------------------------------ 1. Python check
step "Checking Python (3.8+ required)"
if ! command -v python3 >/dev/null 2>&1; then
  fail "Python 3 was not found."
  if [[ $IS_TERMUX -eq 1 ]]; then
    note "Install it with:  pkg install python"
  else
    note "Install it with your package manager, e.g.  sudo apt install python3 python3-venv"
  fi
  exit 1
fi
PYOK=$(python3 -c 'import sys; print(1 if sys.version_info >= (3, 8) else 0)' 2>/dev/null || echo 0)
if [[ "$PYOK" != "1" ]]; then
  fail "Python 3.8+ is required (found: $(python3 --version 2>&1))."
  exit 1
fi
ok "$(python3 --version 2>&1)"

# --------------------------------------------------------------- 2. pip check
step "Checking pip"
if ! python3 -m pip --version >/dev/null 2>&1; then
  fail "pip is not available."
  [[ $IS_TERMUX -eq 1 ]] && note "Fix with:  pkg install python-pip"
  exit 1
fi
ok "pip $(python3 -m pip --version 2>/dev/null | awk '{print $2}')"

# ------------------------------------------------------- 3. virtual environment
PY="$VENV_DIR/bin/python"
WBL="$VENV_DIR/bin/webbehavior"
NEED_INSTALL=1

if [[ -x "$PY" && -x "$WBL" && $FORCE -eq 0 ]]; then
  if "$PY" -c "import webbehavior, rich" >/dev/null 2>&1; then
    ok "Existing virtual environment is healthy (reusing)."
    NEED_INSTALL=0
  else
    step "Virtual environment found but incomplete - repairing..."
  fi
else
  step "Creating virtual environment at: $VENV_DIR"
  if ! python3 -m venv "$VENV_DIR" >/dev/null 2>&1; then
    if [[ $IS_TERMUX -eq 1 ]]; then
      step "venv module unavailable - installing python-venv..."
      pkg install -y python-venv || true
    fi
    if ! python3 -m venv "$VENV_DIR" >/dev/null 2>&1; then
      fail "Could not create the virtual environment."
      note "On Debian/Ubuntu:  sudo apt install python3-venv"
      exit 1
    fi
  fi
  ok "Virtual environment ready"
fi

# ------------------------------------------------------ 4. Python dependencies
if [[ $NEED_INSTALL -eq 1 || $FORCE -eq 1 ]]; then
  step "Installing Python dependencies (rich, playwright)"
  if ! "$PY" -m pip install --quiet --upgrade pip setuptools wheel >/dev/null 2>&1; then
    note "pip self-upgrade skipped (offline or restricted)"
  fi
  if ! "$PY" -m pip install --quiet -e "$REPO_DIR"; then
    fail "Dependency installation failed."
    note "Check your internet connection and re-run:  bash install.sh"
    exit 1
  fi
  ok "Dependencies installed"
fi

# ------------------------------------------------------------ 5. browser setup
step "Checking for a Chromium browser"
BROWSER_PATH="${WEBBEHAVIOR_BROWSER_PATH:-}"
if [[ -z "$BROWSER_PATH" ]]; then
  for candidate in chromium chromium-browser google-chrome chrome; do
    if command -v "$candidate" >/dev/null 2>&1; then
      BROWSER_PATH="$(command -v "$candidate")"
      break
    fi
  done
fi

if [[ -n "$BROWSER_PATH" ]]; then
  ok "Using browser: $BROWSER_PATH"
elif [[ -x "$HOME/.cache/ms-playwright"/chromium-*/chrome-linux*/chrome ]] 2>/dev/null; then
  ok "Using Playwright's downloaded Chromium"
else
  if [[ $IS_TERMUX -eq 1 ]]; then
    step "Installing Chromium via pkg (Termux)..."
    if pkg install -y chromium >/dev/null 2>&1 && command -v chromium >/dev/null 2>&1; then
      ok "Chromium installed"
    else
      note "Could not install Chromium automatically."
      note "Run manually:  pkg install chromium   then re-run:  bash install.sh"
    fi
  else
    step "Downloading Chromium for Playwright (one time, ~150 MB)..."
    if "$PY" -m playwright install chromium >/dev/null 2>&1; then
      ok "Chromium downloaded"
    else
      note "Chromium download failed or unavailable."
      note "Try later with:  $PY -m playwright install chromium"
      note "WebBehaviorLab still installs - the browser is only needed for tests."
    fi
  fi
fi

# ------------------------------------------------- 6. application directories
step "Preparing application directories"
"$PY" - <<'PYEOF'
from webbehavior.utils import storage
base = storage.ensure_dirs()
print("  storage:", base)
PYEOF
ok "Storage directories ready (~/.webbehavior)"

# ----------------------------------------------------------- 7. CLI command
step "Creating the 'webbehavior' command"
BIN_DIR="$HOME/.local/bin"
[[ $IS_TERMUX -eq 1 && -n "${PREFIX:-}" ]] && BIN_DIR="$PREFIX/bin"
mkdir -p "$BIN_DIR"
CLI="$BIN_DIR/webbehavior"
cat > "$CLI" <<WRAPPER
#!/usr/bin/env bash
# WebBehaviorLab launcher (generated by install.sh)
exec "$WBL" "\$@"
WRAPPER
chmod +x "$CLI"
ok "Installed: $CLI"

case ":$PATH:" in
  *":$BIN_DIR:"*) : ;;
  *)
    note "NOTE: $BIN_DIR is not in your PATH."
    note "Add it with:  echo 'export PATH=\"$BIN_DIR:\$PATH\"' >> ~/.bashrc && source ~/.bashrc"
    ;;
esac

# ------------------------------------------------------------ 8. health check
step "Running health check"
if "$WBL" version >/dev/null 2>&1; then
  ok "$("$WBL" version)"
else
  fail "Health check failed: webbehavior did not start."
  note "Run diagnostics with:  $WBL doctor"
  exit 1
fi
"$WBL" doctor || note "Doctor reported issues - see the messages above."

# --------------------------------------------------------------------- done
printf '%s\n'
printf '%s\n' "╭──────────────────────────────╮"
printf '%s\n' "│   Installation Complete ✓    │"
printf '%s\n' "╰──────────────────────────────╯"
printf '%s\n'
printf '%s\n' "Run:"
printf '%s\n' "${BOLD}  webbehavior${OFF}"
printf '%s\n'
printf '%s\n' "${DIM}Authorized testing only · maximum 10 sessions per run${OFF}"
printf '%s\n'
