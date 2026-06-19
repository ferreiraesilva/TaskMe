#!/usr/bin/env bash
# taskme-digest-diario — envia resumo do dia anterior a cada assignante (00:01 diário)
# Cron: hermes cron create "1 0 * * *" --no-agent --script diario.sh --name taskme-digest-diario
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"
source .env 2>/dev/null || true
PYTHON="${REPO}/.venv/bin/python3"
[ -x "$PYTHON" ] || PYTHON=python3
"$PYTHON" -m taskme.dispatch assigner_digests
