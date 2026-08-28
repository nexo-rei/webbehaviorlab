#!/usr/bin/env bash
#
# WebBehaviorLab launcher - runs the app without a global install.
#
# Usage:  bash run.sh [start|history|reports|settings|help|version|doctor]
#
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -x "$REPO_DIR/.venv/bin/webbehavior" ]]; then
  exec "$REPO_DIR/.venv/bin/webbehavior" "$@"
elif [[ -x "$REPO_DIR/.venv/bin/python" ]]; then
  exec "$REPO_DIR/.venv/bin/python" -m webbehavior "$@"
fi

# Fall back to any importable installation (pipx, user site, system).
if command -v webbehavior >/dev/null 2>&1; then
  exec webbehavior "$@"
fi

if python3 -c "import webbehavior" >/dev/null 2>&1; then
  exec python3 -m webbehavior "$@"
fi

echo "✗ WebBehaviorLab is not installed yet."
echo "  Run:  bash install.sh"
exit 1
