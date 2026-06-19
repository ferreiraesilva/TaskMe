#!/usr/bin/env bash
# taskme-digest-segunda — envia digest de pendentes a cada assignado (seg 00:01)
# Cron: hermes cron create "0 0 * * 1" --no-agent --script monday.sh --name taskme-digest-segunda
set -euo pipefail
cd "$(dirname "$0")/.."
source .env 2>/dev/null || true
python3 -m taskme.dispatch monday_digests
