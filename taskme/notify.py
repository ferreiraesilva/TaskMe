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
from .services import channels


def whatsapp_target(phone: str) -> str:
    """Normaliza para o alvo do Hermes: whatsapp:<digits>@s.whatsapp.net."""
    digits = "".join(ch for ch in phone if ch.isdigit())
    return f"whatsapp:{digits}@s.whatsapp.net"


def telegram_target(address: str) -> str:
    return f"telegram:{address.strip()}"


def targets(phone: str) -> list[str]:
    """Destinos ativos da pessoa, respeitando os canais habilitados na instalação."""
    result: list[str] = []
    if "whatsapp" in config.NOTIFY_CHANNELS:
        result.append(whatsapp_target(phone))
    if "telegram" in config.NOTIFY_CHANNELS:
        result.extend(
            telegram_target(row["address"])
            for row in channels.addresses(phone, ("telegram",))
        )
    return result


def send(phone: str, text: str) -> bool:
    """Envia para todos os endpoints habilitados; sucesso se ao menos um entregar."""
    base = shlex.split(config.HERMES_SEND_CMD)
    delivered = False
    for target in targets(phone):
        try:
            proc = subprocess.run(
                [*base, "--to", target, text], capture_output=True, text=True, timeout=30
            )
            delivered = proc.returncode == 0 or delivered
        except Exception:
            continue
    return delivered
