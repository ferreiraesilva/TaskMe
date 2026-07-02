# PROGRESS — TaskMe (checkpoint vivo)

> Retomada após perda de contexto: leia este arquivo + `git log --oneline`.

Branch de trabalho: `feature/taskme-v1` (merge na `main` + tag ao validar).

## Ambiente / acessos

- Repo local: `D:\Projetos\Hermes\TaskMe` (Windows). Remote: github.com/ferreiraesilva/TaskMe.
- Host Hermes (homolog): SSH `leonardo@192.168.100.120` (mac02); Hermes rodando em container `hermes-leonardo-pessoal-hml`.
- Banco: Postgres local `postgres-hml` em mac02 (127.0.0.1:5432). DATABASE_URL gerada pelo `deploy-instance.sh` do hermes-infra.
- Deploy gerenciado por [`hermes-infra`](https://github.com/ferreiraesilva/hermes-infra): `./scripts/deploy-instance.sh hml leonardo-pessoal`.

## Feito

- [x] Branch `feature/taskme-v1`.
- [x] Scaffold + fundação (`config`, `db` psycopg, `dates` PT-BR, `util`, `events`).
- [x] `migrations/0001_init.sql` — 5 tabelas base.
- [x] Todos os serviços: `contacts`, `tasks`, `reprogram`, `charges`, `digests`, `queries`.
- [x] `templates.py`, `notify.py`, `dispatch.py`, `cli.py`.
- [x] Testes: **33+ verdes**.
- [x] **Plugin Hermes** completo: `plugin.yaml` + `__init__.py` + `schemas.py` + `tools.py` + `hook.py`
  - 8 ferramentas `taskme_*` + 3 hooks (`on_session_start`, `pre_llm_call`, `pre_gateway_dispatch`)
- [x] E2E smoke confirmado via `hermes chat`.
- [x] 3 cron jobs: `taskme-digest-segunda`, `taskme-digest-diario`, `taskme-cobrancas`.
- [x] **Identidade multicanal** (`feat: adicionar identidade e notificacao multicanal`):
  - `taskme/identity.py`, `taskme/services/channels.py`
  - `migrations/0002_channels.sql`
  - `TASKME_NOTIFY_CHANNELS` (whatsapp, telegram ou ambos)

## Próximo passo

- [ ] Validar `migration/0002_channels.sql` aplicada no `postgres-hml` (deploy-instance.sh deve ter aplicado).
- [ ] **Teste E2E via Telegram** no deployment `leonardo-pessoal-hml`: criar tarefa, cobrar, digest.
- [ ] Merge `feature/taskme-v1` → `main` + tag `v0.1.0`.
