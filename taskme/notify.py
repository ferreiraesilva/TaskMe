"""Envio de mensagens via Hermes.

O próprio Python envia cada mensagem por-destinatário chamando o CLI do Hermes
(`$HERMES_SEND_CMD`, default `hermes send`). O texto é exato — o agente não
compõe nem decide envio.

Para testes/local use `HERMES_SEND_CMD=echo` (não envia de verdade), ou
monkeypatch `notify.send`.
"""
from __future__ import annotations

import shlex
import subprocess

from . import config


def whatsapp_target(phone: str) -> str:
    """Normaliza para o alvo do Hermes: whatsapp:<digits>@s.whatsapp.net."""
    digits = "".join(ch for ch in phone if ch.isdigit())
    return f"whatsapp:{digits}@s.whatsapp.net"


def send(phone: str, text: str) -> bool:
    """Envia `text` para o telefone via Hermes. Retorna True se exit 0."""
    base = shlex.split(config.HERMES_SEND_CMD)
    cmd = [*base, "--to", whatsapp_target(phone), text]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return proc.returncode == 0
    except Exception:
        return False
