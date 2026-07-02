# Promoção Homolog → Produção

O TaskMe não gerencia seu próprio deploy. Toda promoção passa pelo
[`hermes-infra`](https://github.com/ferreiraesilva/hermes-infra):
o inventário define o deployment, o `deploy-instance.sh` provisiona banco,
migrations, clone do produto e container.

## Pré-requisitos

- Deployment registrado em `hermes-infra/clients/<cliente>.json`
- Bot Telegram criado seguindo `TMHA_<Cliente>_<Perfil>_<Ambiente>_bot`
- Secrets em `~/.config/hermes-infra/secrets/<ambiente>/<deployment>.env`
- `postgres-<ambiente>` saudável no host de destino

## Deploy (homolog ou produção)

```bash
# No host de destino (mac02 para hml, solid para prd):
cd ~/projects/hermes-infra
./scripts/deploy-instance.sh hml <deployment-id>
# Ex.: ./scripts/deploy-instance.sh hml leonardo-pessoal
```

O script:
1. Valida o inventário completo
2. Cria banco e role exclusivos para o deployment
3. Clona o TaskMe na branch `feature/taskme-v1` (hml) ou `main` (prd)
4. Aplica migrations (`0001_init.sql`, `0002_channels.sql`) — idempotentes
5. Gera `.env` com `DATABASE_URL` apontando para o Postgres local
6. Sobe container `hermes-<deployment>-<ambiente>` com `gateway run`

## Diferenças entre ambientes

| | Homolog (hml) | Produção (prd) |
|---|---|---|
| Host | mac02 (192.168.100.120) | solid (177.135.249.173) |
| Postgres | `postgres-hml` (127.0.0.1:5432) | `postgres-prd` (127.0.0.1:5432) |
| Deploy | Manual via script | GitHub Actions (`hermes-infra`) |
| Dados | Seed fictício na 1ª criação | Base limpa, sem seed |
| Bot Telegram | `TMHA_*_Hml_bot` | `TMHA_*_Prd_bot` |

## Migrations

Sempre idempotentes (`IF NOT EXISTS`). Aplicar na ordem numérica:

```
migrations/0001_init.sql      # tabelas base (tasks, contacts, charges…)
migrations/0002_channels.sql  # identidade multicanal (channels, phones…)
```

O `deploy-instance.sh` aplica todas automaticamente em ordem.

## Hardening futuro (pós-v1)

- Confirmar que o role do deployment só tem acesso ao próprio banco (já garantido pelo script)
- Avaliar política de backup do `postgres-prd`
