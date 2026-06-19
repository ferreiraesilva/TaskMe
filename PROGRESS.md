# PROGRESS — TaskMe (checkpoint vivo)

> Retomada após perda de contexto: leia este arquivo + `git log --oneline`.
> Plano completo: `C:\Users\Admin\.claude\plans\vamos-responder-a-lista-recursive-robin.md`

Branch de trabalho: `feature/taskme-v1` (merge na `main` + tag ao validar).

## Ambiente / acessos
- Repo local: `D:\Projetos\AI\TaskMe` (Windows). Remote: github.com/ferreiraesilva/TaskMe (vazio até 1º push).
- Host Hermes (homolog): SSH `leonardo@192.168.100.125` (`mac02`, Ubuntu); `hermes` em `~/.local/bin/hermes`; clone alvo `~/projects/TaskMe`.
- Banco: Supabase "TaskMe" (MCP só p/ dev). Runtime usa `DATABASE_URL` (psycopg). Migration `0001_init` JÁ aplicada (5 tabelas).
- Envio: `HERMES_SEND_CMD` (default `hermes send`; testes `echo`).

## Feito
- [x] Branch `feature/taskme-v1`.
- [x] Scaffold: `.gitignore`, `requirements.txt`, `.env.example`, `taskme/__init__.py`.
- [x] `taskme/config.py` (env + TZ + now/today).
- [x] `taskme/db.py` (psycopg: `transaction()`, `query_all/one`).
- [x] `taskme/dates.py` (resolução determinística PT-BR).
- [x] `migrations/0001_init.sql` (idempotente) + aplicada no Supabase.

## Próximo passo
- [ ] `tests/test_dates.py` (cobrir o resolver) + `pytest.ini`/conftest.
- [ ] `taskme/templates.py` (textos PT-BR imperativos).
- [ ] `taskme/notify.py` (wrapper `$HERMES_SEND_CMD` via subprocess; mockável).
- [ ] `services/contacts.py` (resolve/dedupe/add) → `resolve_contact`/`add_contact`.
- [ ] `services/tasks.py` (propose/commit/list/complete; code TM-#### via sequence; intro 1ª tarefa).
- [ ] `services/reprogram.py`; `services/charges.py` (+fila/handle_reply); `services/digests.py` + `dispatch.py`; `services/queries.py`.
- [ ] `taskme/cli.py` (dispatch dos comandos).
- [ ] Plugin Hermes (`plugin.yaml`, `__init__.py`, `schemas.py`, `tools.py`, `hook.py`).
- [ ] `cron/`, `.hermes.md`/`AGENTS.md`, `ci/selftest.sh`, `README`, `PROMOTION.md`.
- [ ] Deploy + teste no host via SSH; merge main + tag.

## Pendências / decisões abertas
- Hardening: habilitar RLS (deny-all) em prod, pois conexão direta privilegiada bypassa RLS — confirmar role no host.
- Validar no host: flags exatas de `hermes send`/`hermes cron --script`/`hermes plugins`; e se `pre_gateway_dispatch` já recebe transcrição de áudio (senão áudio → `taskme_responder`).
