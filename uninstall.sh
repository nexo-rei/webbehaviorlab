#!/usr/bin/env bash
#
# WebBehaviorLab uninstaller.
#
# Removes the virtual environment and the CLI command. Optionally deletes
# local reports, settings and logs. Always asks before deleting user data.
#
set -euo pipefail

BOLD=$'\033[1m'; DIM=$'\033[2m'; GREEN=$'\033[32m'; RED=$'\033[31m'; CYAN=$'\033[36m'; OFF=$'\033[0m'
step() { printf '%s\n' "${CYAN}→${OFF} $*"; }
ok()   { printf '%s\n' "${GREEN}✓${OFF} $*"; }
fail() { printf '%s\n' "${RED}✗${OFF} $*" >&2; }
note() { printf '%s\n' "${DIM}$*${OFF}"; }

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$REPO_DIR/.venv"

printf '%s\n'
printf '%s\n' "${BOLD}This will remove WebBehaviorLab.${OFF}"
printf '%s\n'

# The repository itself is never deleted by this script - only generated
# artifacts and (optionally) user data.
[[ -d "$VENV_DIR" ]] && note "Virtual environment: $VENV_DIR"
[[ -d "$HOME/.webbehavior" ]] && note "User data:          $HOME/.webbehavior"

ask_yes_no() {
  local prompt="$1" default="${2:-N}" answer
  while true; do
    read -r -p "$(printf '%s ' "$prompt [$default]")" answer || answer=""
    answer="${answer:-$default}"
    case "$answer" in
      [Yy]|[Yy][Ee][Ss]) return 0 ;;
      [Nn]|[Nn][Oo])     return 1 ;;
      *) note "Please answer Y or N." ;;
    esac
  done
}

if ! ask_yes_no "Continue with removal?" "N"; then
  ok "Uninstall cancelled - nothing was deleted."
  exit 0
fi

# ---------------------------------------------------------------- CLI command
step "Removing the 'webbehavior' command"
for CLI in "$PREFIX/bin/webbehavior" "$HOME/.local/bin/webbehavior" "/usr/local/bin/webbehavior"; do
  if [[ -f "$CLI" ]]; then
    rm -f "$CLI" && ok "Removed $CLI"
  fi
done

# ------------------------------------------------------------- virtual env
if [[ -d "$VENV_DIR" ]]; then
  step "Removing virtual environment..."
  rm -rf "$VENV_DIR"
  ok "Removed $VENV_DIR"
fi

# ------------------------------------------------------------ user data
if [[ -d "$HOME/.webbehavior" ]]; then
  printf '%s\n'
  if ask_yes_no "Delete local reports, settings and history too?" "N"; then
    step "Deleting $HOME/.webbehavior ..."
    rm -rf "$HOME/.webbehavior"
    ok "User data removed"
  else
    note "Kept $HOME/.webbehavior (reports, settings and history survive)."
  fi
fi

printf '%s\n'
ok "WebBehaviorLab uninstalled."
note "The repository folder itself was left in place: $REPO_DIR"
note "Delete it manually if you no longer need the source code."
