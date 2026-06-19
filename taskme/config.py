"""Configuração via ambiente (.env). Sem segredos no código."""
from __future__ import annotations

import os
from datetime import date, datetime
from zoneinfo import ZoneInfo

# Carrega .env se python-dotenv estiver disponível (opcional; em prod o
# ambiente já vem do profile/host). Mantemos sem dependência obrigatória.
try:  # pragma: no cover - conveniência de dev
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover
    pass

DATABASE_URL = os.environ.get("DATABASE_URL", "")
TZ_NAME = os.environ.get("TZ", "America/Sao_Paulo")
HERMES_SEND_CMD = os.environ.get("HERMES_SEND_CMD", "hermes send")

TZ = ZoneInfo(TZ_NAME)


def now() -> datetime:
    """Agora, no fuso configurado (o do Hermes)."""
    return datetime.now(TZ)


def today() -> date:
    """Data de hoje, no fuso configurado."""
    return now().date()
