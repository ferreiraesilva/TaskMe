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
- [x] Scaffold + fundação (`config`, `db` psycopg, `dates` PT-BR, `util`, `events`).
- [x] `migrations/0001_init.sql` aplicada; **SQL dos serviços validado funcionalmente via MCP** (list_pending, due-charge, digests concluídas/reprogramadas/atrasadas, atraso +N) com cenário semeado+limpo.
- [x] `templates.py` (PT-BR imperativo), `notify.py` (`$HERMES_SEND_CMD`).
- [x] services: `contacts`, `tasks` (propose/commit/list/complete, code TM-#### via sequence, intro 1ª tarefa), `reprogram`, `charges` (fila 1-por-vez + cobrança + `handle_reply` + `route_inbound`), `digests`, `queries`.
- [x] `dispatch.py` (cron) + `cli.py` (todos os comandos → JSON).
- [x] Testes: `tests/test_dates.py` (27) + `tests/test_pure.py` (period/summarize/templates) → **33 verdes**.

## Próximo passo
- [ ] Plugin Hermes na raiz: `plugin.yaml`, `__init__.py` (register), `schemas.py`, `tools.py` (importam `taskme.services`), `hook.py` (`pre_gateway_dispatch` → `charges.route_inbound`/`handle_reply`).
- [ ] `cron/monday.sh|diario.sh|cobrancas.sh`, `.hermes.md`/`AGENTS.md`, `ci/selftest.sh`, `PROMOTION.md`.
- [ ] **Teste E2E vivo** precisa de `DATABASE_URL` (senha do Postgres do Supabase) — pedir ao Leonardo ou pegar no host. Rodar `cli.py` real + seed.
- [ ] Push, deploy no host via SSH (`~/projects/TaskMe`), `hermes plugins install`, cron; `hermes chat -q` smoke; merge main + tag.

## Pendências / decisões abertas
- Hardening: habilitar RLS (deny-all) em prod, pois conexão direta privilegiada bypassa RLS — confirmar role no host.
- Validar no host: flags exatas de `hermes send`/`hermes cron --script`/`hermes plugins`; e se `pre_gateway_dispatch` já recebe transcrição de áudio (senão áudio → `taskme_responder`).
