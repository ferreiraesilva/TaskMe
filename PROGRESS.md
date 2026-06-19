# PROGRESS — TaskMe (checkpoint vivo)

> Retomada após perda de contexto: leia este arquivo + `git log --oneline`.
> Plano completo: `C:\Users\Admin\.claude\plans\vamos-responder-a-lista-recursive-robin.md`

Branch de trabalho: `feature/taskme-v1` (merge na `main` + tag ao validar).

## Ambiente / acessos
- Repo local: `D:\Projetos\AI\TaskMe` (Windows). Remote: github.com/ferreiraesilva/TaskMe.
- Host Hermes (homolog): SSH `leonardo@192.168.100.125` (`mac02`, Ubuntu); `hermes` em `~/.local/bin/hermes`; clone em `~/projects/TaskMe`.
- Banco: Supabase "TaskMe" (`db.mlhuqnobarbgeptdqbpx.supabase.co:5432`). Migration `0001_init` aplicada (5 tabelas). DATABASE_URL configurada em `~/projects/TaskMe/.env`.
- venv no host: `~/projects/TaskMe/.venv` (Python 3.11). Deps também instaladas no venv do Hermes (`~/.hermes/hermes-agent/venv`).
- `HERMES_SEND_CMD=hermes send` (ativo no `.env`).

## Feito
- [x] Branch `feature/taskme-v1`.
- [x] Scaffold + fundação (`config`, `db` psycopg, `dates` PT-BR, `util`, `events`).
- [x] `migrations/0001_init.sql` aplicada; SQL validado via MCP (5 tabelas).
- [x] Todos os serviços: `contacts`, `tasks`, `reprogram`, `charges`, `digests`, `queries`.
- [x] `templates.py`, `notify.py`, `dispatch.py`, `cli.py`.
- [x] Testes: **33 verdes** (local + host).
- [x] **Plugin Hermes** completo e carregando no venv do Hermes:
  - `plugin.yaml` + `__init__.py` + `schemas.py` + `tools.py` + `hook.py`
  - 8 ferramentas `taskme_*` + 3 hooks (`on_session_start`, `pre_llm_call`, `pre_gateway_dispatch`)
  - Import relativo `from .taskme import X` (evita conflito de namespace)
  - `psycopg`, `python-dateutil`, `python-dotenv` instalados no venv do Hermes
- [x] Plugin **enabled** (`hermes plugins list` → `taskme | enabled | 0.1.0`)
- [x] **8 ferramentas visíveis** ao agente (`hermes chat -q "quais ferramentas taskme..."`)
- [x] **E2E smoke** confirmado: `hermes chat -q "cria tarefa pra João..."` → chamou `taskme_propor_tarefa` → pediu telefone do contato (flow correto)
- [x] **3 cron jobs ativos**: `taskme-digest-segunda` (seg 00:00), `taskme-digest-diario` (00:01), `taskme-cobrancas` (00:02)
- [x] `cron/monday.sh|diario.sh|cobrancas.sh`, `.hermes.md`, `PROMOTION.md`, `ci/selftest.sh`

## Próximo passo
- [ ] **Teste E2E via WhatsApp**: enviar mensagem real para o número do Hermes, criar tarefa para um número real de teste, verificar via Supabase MCP e hermes-remote.
- [ ] Merge `feature/taskme-v1` → `main` + tag `v0.1.0`.

## Observações / pendências
- Em CLI mode (`hermes chat`), `on_session_start` não injeta o telefone (é hook de gateway). Em WhatsApp real, o fluxo completo funciona.
- Hardening: habilitar RLS no Supabase em produção.
- Cron `deliver: local` — stdout não vai para WhatsApp (ok para homolog).
