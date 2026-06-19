# PROGRESS — TaskMe (checkpoint vivo)

> Retomada após perda de contexto: leia este arquivo + `git log --oneline`.
> Plano completo: `C:\Users\Admin\.claude\plans\vamos-responder-a-lista-recursive-robin.md`

Branch de trabalho: `feature/taskme-v1` (merge na `main` + tag ao validar).

## Ambiente / acessos
- Repo local: `D:\Projetos\AI\TaskMe` (Windows). Remote: github.com/ferreiraesilva/TaskMe.
- Host Hermes (homolog): SSH `leonardo@192.168.100.125` (`mac02`, Ubuntu); `hermes` em `~/.local/bin/hermes`; clone em `~/projects/TaskMe`.
- Banco: Supabase "TaskMe" (MCP só p/ dev). Runtime usa `DATABASE_URL` (psycopg). Migration `0001_init` JÁ aplicada (5 tabelas).
- Envio: `HERMES_SEND_CMD` (atualmente `echo` no `.env` do host — trocar p/ `hermes send` após colocar a senha do DB).
- venv no host: `~/projects/TaskMe/.venv` (Python 3.11, psycopg + dateutil + pytest).

## Feito
- [x] Branch `feature/taskme-v1`.
- [x] Scaffold + fundação (`config`, `db` psycopg, `dates` PT-BR, `util`, `events`).
- [x] `migrations/0001_init.sql` aplicada; **SQL dos serviços validado via MCP** (5 tabelas).
- [x] `templates.py`, `notify.py`, services: `contacts`, `tasks`, `reprogram`, `charges`, `digests`, `queries`.
- [x] `dispatch.py` (cron) + `cli.py` (todos os comandos → JSON).
- [x] Testes: `tests/test_dates.py` (27) + `tests/test_pure.py` (6) → **33 verdes** (local + no host).
- [x] **Plugin Hermes**: `plugin.yaml`, `__init__.py`, `schemas.py`, `tools.py`, `hook.py`.
  - 8 ferramentas `taskme_*` + 3 hooks (`on_session_start`, `pre_llm_call`, `pre_gateway_dispatch`).
  - Hook injeta telefone do remetente no contexto do LLM; roteia respostas de cobrança deterministicamente.
- [x] `cron/monday.sh|diario.sh|cobrancas.sh` + wrappers em `~/.hermes/scripts/`.
- [x] `ci/selftest.sh`, `.hermes.md`, `PROMOTION.md`.
- [x] **Deploy no host**: plugin symlink `~/.hermes/plugins/taskme → ~/projects/TaskMe`; plugin `enabled`; **3 cron jobs ativos** (`taskme-digest-segunda`, `taskme-digest-diario`, `taskme-cobrancas`).

## Próximo passo (BLOQUEADO: precisa de DATABASE_URL)
- [ ] Leonardo adiciona `DATABASE_URL` real no `/home/leonardo/projects/TaskMe/.env` (senha do Supabase "TaskMe").
  - Formato: `postgresql://postgres.mlhuqnobarbgeptdqbpx:SENHA@aws-0-XX.pooler.supabase.com:6543/postgres`
  - Após isso: trocar `HERMES_SEND_CMD=echo` → `HERMES_SEND_CMD=hermes send` no mesmo `.env`.
- [ ] **Teste E2E vivo** via `hermes chat -q`:
  ```bash
  hermes chat -q "cria tarefa pra João fazer o relatório até sexta"
  hermes chat -q "minhas tarefas pendentes"
  ```
  Validar via Supabase MCP + hermes-remote.
- [ ] Merge `feature/taskme-v1` → `main` + tag `v0.1.0`.

## Pendências / decisões abertas
- `DATABASE_URL` no host (bloqueante para E2E).
- Hardening: habilitar RLS (deny-all) em prod, conexão direta privilegiada bypassa RLS.
- Validar no host: `on_session_start` hook recebe `user_id` como string JID (`5562...@s.whatsapp.net`)?
  A `normalize_whatsapp_identifier` do Hermes cuida disso, mas confirmar no smoke.
- Cron `deliver: local` (stdout não vai para WhatsApp) — ok para homolog; em prod pode redirecionar p/ owner.
