#!/usr/bin/env bash
# taskme-cobrancas — enfileira e envia cobranças de vencimento (00:02 diário)
# Cron: hermes cron create "2 0 * * *" --no-agent --script cobrancas.sh --name taskme-cobrancas
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"
source .env 2>/dev/null || true
PYTHON="${REPO}/.venv/bin/python3"
[ -x "$PYTHON" ] || PYTHON=python3
"$PYTHON" -m taskme.dispatch due_charges
