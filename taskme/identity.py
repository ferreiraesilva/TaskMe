"""Resolução de identidade de entrada sem acoplar o domínio ao canal."""
from __future__ import annotations

from . import config
from .services import channels
from .util import normalize_phone


def resolve(platform: str, user_id: str) -> str:
    platform = (platform or "").lower()
    user_id = str(user_id or "").strip()
    if "whatsapp" in platform:
        # Não-contato endereçado por LID que o bridge não resolveu para telefone:
        # NUNCA tratar os dígitos do LID como telefone. Resolve pelo vínculo de
        # canal (preenchido no onboarding); vazio = desconhecido -> onboarding.
        if "@lid" in user_id:
            try:
                return channels.phone_for("whatsapp", user_id)
            except Exception:
                return ""
        try:
            from gateway.whatsapp_identity import normalize_whatsapp_identifier
            phone = normalize_whatsapp_identifier(user_id)
        except Exception:
            phone = normalize_phone(user_id)
        if phone:
            try:
                channels.link(phone, "whatsapp", user_id)
            except Exception:
                pass
        return phone

    if "telegram" in platform:
        if config.MODE == "telegram_test" and config.TG_TEST_PHONE:
            phone = normalize_phone(config.TG_TEST_PHONE)
            try:
                channels.link(phone, "telegram", user_id)
            except Exception:
                pass
            return phone
        try:
            return channels.phone_for("telegram", user_id)
        except Exception:
            return ""
    return ""


def channel_from_platform(platform: str) -> str:
    """Normaliza a plataforma de origem para o canal da tarefa (whatsapp|telegram)."""
    return "telegram" if "telegram" in (platform or "").lower() else "whatsapp"


def platform_from_event(event) -> str:
    source = getattr(event, "source", None)
    value = (
        getattr(source, "platform", None)
        or getattr(event, "platform", None)
        or getattr(source, "channel", None)
        or ""
    )
    return str(getattr(value, "value", value) or "").lower()
