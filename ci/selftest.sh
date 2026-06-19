#!/usr/bin/env bash
# Selftest CI — roda pytest + smoke do cli.py (sem banco real).
# Uso: bash ci/selftest.sh   (na raiz do repo; DATABASE_URL pode estar no .env)
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"
source .env 2>/dev/null || true
export HERMES_SEND_CMD="echo"
PYTHON="${REPO}/.venv/bin/python3"
[ -x "$PYTHON" ] || PYTHON=python3

echo "=== pytest ==="
"$PYTHON" -m pytest tests/ -v --tb=short

echo ""
echo "=== smoke: dates ==="
"$PYTHON" -c "
from taskme.dates import resolve_due
from datetime import datetime
now = datetime(2026, 6, 19, 8, 0)
tests = [
    ('sexta', '2026-06-19'),
    ('amanhã', '2026-06-20'),
    ('em 3 dias', '2026-06-22'),
    ('dia 25', '2026-06-25'),
    ('fim do mês', '2026-06-30'),
]
ok = 0
for phrase, expected in tests:
    result = resolve_due(phrase, now)
    r = result.isoformat() if result else None
    status = '✓' if r == expected else f'✗ (got {r})'
    print(f'  {phrase!r:20s} → {r} {status}')
    if r == expected: ok += 1
print(f'  {ok}/{len(tests)} ok')
"

echo ""
echo "=== smoke: templates ==="
"$PYTHON" -c "
from taskme import templates
from datetime import date
m = templates.task_message('João', 'Leo', 'TM-1001', 'Envie o relatório', None, date(2026,6,20))
assert 'TM-1001' in m and 'Envie' in m, 'FAIL task_message'
print('  task_message ✓')
m2 = templates.due_charge('João', 'TM-1001', 'Envie o relatório')
assert 'prazo' in m2.lower() or 'TM-1001' in m2, 'FAIL due_charge'
print('  due_charge ✓')
print('  templates ok')
"

echo ""
echo "=== selftest PASS ==="
