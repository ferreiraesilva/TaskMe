# Promoção Homolog → Produção

## Pré-requisitos
- Número de "projetos" pareado no Hermes de produção
- Projeto Supabase de produção criado (base limpa)
- DATABASE_URL de produção em mãos

## Passo a passo

### 1. Instalar o plugin no profile de produção
```bash
# No host de produção (ou no mesmo host com --profile projetos):
hermes plugins install ferreiraesilva/TaskMe --enable
# OU, para instalar do clone local:
ln -s ~/projects/TaskMe ~/.hermes/plugins/taskme
hermes plugins enable taskme
```

### 2. Criar o .env de produção
```bash
cat > ~/projects/TaskMe/.env <<'EOF'
DATABASE_URL=postgresql://user:pass@host:5432/prod_db
TZ=America/Sao_Paulo
HERMES_SEND_CMD=hermes --profile projetos send
EOF
chmod 600 ~/projects/TaskMe/.env
```

### 3. Aplicar as migrations na base limpa
```bash
source ~/projects/TaskMe/.env
psql $DATABASE_URL -f ~/projects/TaskMe/migrations/0001_init.sql
```
Verifique: `psql $DATABASE_URL -c "\dt"` deve mostrar 5 tabelas.

### 4. Aplicar patch no bridge.js do Hermes
O TaskMe precisa que o WhatsApp bridge reconheça mensagens de contato (vCard).
Este patch é necessário uma vez por instalação do Hermes (e re-aplicar após updates do Hermes que sobrescrevam o bridge.js):
```bash
python3 ~/projects/TaskMe/ci/patch_hermes_bridge.py
```
O script verifica se já foi aplicado, testa a sintaxe e reinicia o bridge automaticamente.

### 5. Criar os cron jobs no profile de produção
```bash
hermes cron create "0 0 * * 1" --no-agent --script ~/projects/TaskMe/cron/monday.sh --name taskme-digest-segunda
hermes cron create "1 0 * * *" --no-agent --script ~/projects/TaskMe/cron/diario.sh --name taskme-digest-diario
hermes cron create "2 0 * * *" --no-agent --script ~/projects/TaskMe/cron/cobrancas.sh --name taskme-cobrancas
```

### 5. Smoke test
```bash
# Dry-run (sem enviar mensagens):
HERMES_SEND_CMD=echo python3 -m taskme.dispatch monday_digests
HERMES_SEND_CMD=echo python3 -m taskme.dispatch due_charges

# Com envio real (número do Leonardo):
hermes chat -q "cria tarefa pra mim fazer o smoke test até hoje"
```

## Diferenças entre ambientes

| | Homolog | Produção |
|---|---|---|
| `DATABASE_URL` | Supabase TaskMe (homolog) | Supabase/Postgres de prod |
| `HERMES_SEND_CMD` | `hermes send` | `hermes --profile projetos send` |
| Dados | Descartáveis | Base limpa, sem migração |
| Número | Número pessoal do Hermes | Número de "projetos" |

## Hardening futuro (pós-v1)
- Habilitar RLS no Supabase (deny-all + policy por role do Postgres)
- Confirmar que `DATABASE_URL` de produção usa um role não-privilegiado
