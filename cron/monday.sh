#!/usr/bin/env bash
# taskme-digest-segunda — envia digest de pendentes a cada assignado (seg 00:01)
# Cron: hermes cron create "0 0 * * 1" --no-agent --script monday.sh --name taskme-digest-segunda
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"
source .env 2>/dev/null || true
PYTHON="${REPO}/.venv/bin/python3"
[ -x "$PYTHON" ] || PYTHON=python3
"$PYTHON" -m taskme.dispatch monday_digests
