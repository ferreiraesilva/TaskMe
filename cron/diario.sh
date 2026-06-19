#!/usr/bin/env bash
# taskme-digest-diario — envia resumo do dia anterior a cada assignante (00:01 diário)
# Cron: hermes cron create "1 0 * * *" --no-agent --script diario.sh --name taskme-digest-diario
set -euo pipefail
cd "$(dirname "$0")/.."
source .env 2>/dev/null || true
python3 -m taskme.dispatch assigner_digests
