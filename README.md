# TaskMe

Assistente de **cobrança e follow-up de tarefas via WhatsApp e Telegram**, rodando como um
**plugin do [Hermes Agent](https://hermes-agent.nousresearch.com/)**. Você atribui
uma tarefa a alguém por texto ou áudio; o TaskMe cria, envia, lembra (segundas),
cobra no vencimento, registra reprogramações e manda um resumo diário ao autor.

- **Lógica determinística em Python** (`taskme/`) — datas, fila, estados, textos.
- **Adaptador fino no Hermes** — ferramentas tipadas + hook de gateway; o agente só
  transcreve/extrai slots, nunca calcula datas nem compõe os envios.
- **Banco**: Postgres, acesso direto via `psycopg` (`DATABASE_URL`).
- **Identidade multicanal**: o telefone permanece como identidade canônica e pode
  receber endpoints WhatsApp e Telegram sem duplicar tarefas ou histórico.

## Primeiro contato no WhatsApp

O TaskMe nunca inicia uma conversa no WhatsApp. A tabela `taskme_channels` é a
lista geral, por instância/bot, das pessoas que já enviaram uma mensagem. Salvar
alguém no caderno particular de contatos de um assignante não autoriza envios.

Quando o assignante tenta criar uma tarefa para alguém que ainda não falou com o
bot, a criação é bloqueada e ele recebe um link `wa.me` para encaminhar. O link
abre uma mensagem com um código temporário e de uso único. Quando o destinatário
envia essa mensagem, o TaskMe registra o primeiro contato — inclusive quando o
WhatsApp identifica o remetente por `@lid`. Depois disso, o assignante pode pedir
a tarefa novamente.

O número público usado no link vem de `TASKME_WHATSAPP_BOT_PHONE` ou, por padrão,
de `WHATSAPP_ACCOUNT_PHONE`. No deploy gerenciado, este último é preenchido por
`whatsapp.account_phone` no inventário do `hermes-infra`.

## Setup (host do Hermes)
```bash
git clone https://github.com/ferreiraesilva/TaskMe.git ~/projects/TaskMe
cd ~/projects/TaskMe
cp .env.example .env   # preencher DATABASE_URL, TZ, HERMES_SEND_CMD
pip install -r requirements.txt
psql "$DATABASE_URL" -f migrations/0001_init.sql      # base limpa
hermes plugins install ~/projects/TaskMe --enable     # registra o plugin
# cron jobs (digests/cobranças):
hermes cron create "0 0 * * 1" --no-agent --script ~/projects/TaskMe/cron/monday.sh   --name taskme-digest-segunda
hermes cron create "1 0 * * *" --no-agent --script ~/projects/TaskMe/cron/diario.sh   --name taskme-digest-diario
hermes cron create "2 0 * * *" --no-agent --script ~/projects/TaskMe/cron/cobrancas.sh --name taskme-cobrancas
```

## Deployments e nomes

O TaskMe não define bots ou clientes concretos. O inventário, os secrets e os
usernames Telegram pertencem ao
[`hermes-infra`](https://github.com/ferreiraesilva/hermes-infra), seguindo
`TMHA_<Cliente>_<Perfil>_<Ambiente>_bot`.

## CLI (uso interno; o plugin/cron chamam isto)
```bash
python -m taskme.cli <comando> [args...]   # ver `taskme/cli.py`
```

## Promoção homolog → produção
Ver [PROMOTION.md](PROMOTION.md). Muda só `DATABASE_URL` e `HERMES_SEND_CMD`; a base
de produção começa limpa (migrations idempotentes).
