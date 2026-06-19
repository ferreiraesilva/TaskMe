#!/usr/bin/env bash
# taskme-cobrancas — enfileira e envia cobranças de vencimento (00:02 diário)
# Cron: hermes cron create "2 0 * * *" --no-agent --script cobrancas.sh --name taskme-cobrancas
set -euo pipefail
cd "$(dirname "$0")/.."
source .env 2>/dev/null || true
python3 -m taskme.dispatch due_charges
