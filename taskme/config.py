"""Configuração via ambiente (.env). Sem segredos no código."""
from __future__ import annotations

import os
from datetime import date, datetime
from zoneinfo import ZoneInfo

# Carrega .env se python-dotenv estiver disponível (opcional; em prod o
# ambiente já vem do profile/host). Mantemos sem dependência obrigatória.
try:  # pragma: no cover - conveniência de dev
    from pathlib import Path
    from dotenv import load_dotenv

    # Procura .env na raiz do repo (pai do pacote taskme/)
    _env_file = Path(__file__).parent.parent / ".env"
    load_dotenv(_env_file if _env_file.exists() else None, override=True)
except Exception:  # pragma: no cover
    pass

DATABASE_URL = os.environ.get("DATABASE_URL", "")
TZ_NAME = os.environ.get("TZ", "America/Sao_Paulo")
HERMES_SEND_CMD = os.environ.get("HERMES_SEND_CMD", "hermes send")
MODE = os.environ.get("TASKME_MODE", "shared").strip().lower()
TG_TEST_PHONE = os.environ.get("TASKME_TG_TEST_PHONE", "").strip()
WHATSAPP_BOT_PHONE = os.environ.get(
    "TASKME_WHATSAPP_BOT_PHONE",
    os.environ.get("WHATSAPP_ACCOUNT_PHONE", ""),
).strip()
NOTIFY_CHANNELS = tuple(
    item.strip().lower()
    for item in os.environ.get("TASKME_NOTIFY_CHANNELS", "whatsapp").split(",")
    if item.strip().lower() in {"whatsapp", "telegram"}
)

TZ = ZoneInfo(TZ_NAME)


def now() -> datetime:
    """Agora, no fuso configurado (o do Hermes)."""
    return datetime.now(TZ)


def today() -> date:
    """Data de hoje, no fuso configurado."""
    return now().date()
