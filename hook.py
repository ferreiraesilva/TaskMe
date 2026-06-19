"""Hook pre_gateway_dispatch do TaskMe.

Texto → roteamento determinístico: se o remetente tem cobrança aberta,
parseia a resposta (concluiu/reprograma) e chama handle_reply direto, sem LLM.
Áudio → retorna None (allow) para o agente transcrever e chamar taskme_responder.
"""
from __future__ import annotations

import logging
import re

from .taskme import config, dates
from .taskme.services import charges
from .taskme.util import normalize_phone

log = logging.getLogger("taskme.hook")

_DONE_WORDS = frozenset({
    "sim", "s", "ok", "feito", "fiz", "concluí", "conclui",
    "pronto", "done", "entregue", "entregui", "concluido", "concluído",
    "terminei", "terminado", "certo", "já", "ja", "entregamos",
})

_REPROGRAM_INDICATORS = frozenset({
    "não", "nao", "reprogram", "adiar", "adiamento", "prazo",
    "dia", "semana", "mês", "mes", "próximo", "proximo",
    "amanhã", "amanha", "depois",
    "segunda", "terca", "terça", "quarta", "quinta", "sexta",
    "sabado", "sábado", "domingo",
    "janeiro", "fevereiro", "março", "marco", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
})


def _normalize_text(text: str) -> set[str]:
    clean = text.lower().strip()
    clean = re.sub(r"[.,!?;:]", " ", clean)
    return set(clean.split())


def _parse_outcome(text: str):
    """Return ('done',) | ('reprogram', text) | None (ambiguous → agent).

    'done' only when strong positive keywords appear with no scheduling context.
    'reprogram' when scheduling indicators or digits appear.
    None when ambiguous → let agent handle via taskme_responder.
    """
    words = _normalize_text(text)
    has_digits = bool(re.search(r"\d", text))
    has_reprogram = bool(words & _REPROGRAM_INDICATORS) or has_digits
    has_done = bool(words & _DONE_WORDS)

    if has_done and not has_reprogram:
        return ("done",)
    if has_reprogram and not has_done:
        return ("reprogram", text.strip())
    # Ambiguous (both or neither) → let agent handle
    return None


def _phone_from_event(event) -> str:
    """Extrai telefone normalizado de event.source (WhatsApp JID ou bare)."""
    src = getattr(event, "source", None)
    user_id = getattr(src, "user_id", None) or ""
    try:
        from gateway.whatsapp_identity import normalize_whatsapp_identifier
        return normalize_whatsapp_identifier(str(user_id))
    except Exception:
        return normalize_phone(str(user_id))


def _is_text(event) -> bool:
    """True somente para mensagens de texto puro (não áudio/voz/imagem)."""
    try:
        from gateway.platforms.base import MessageType
        return getattr(event, "message_type", MessageType.TEXT) == MessageType.TEXT
    except Exception:
        return True  # assume texto se import falhar


def handle_gateway(event, **kwargs) -> dict | None:
    """pre_gateway_dispatch: roteamento de cobranças."""
    try:
        phone = _phone_from_event(event)
        if not phone:
            return None

        # Só age se esse telefone tem cobrança aguardando resposta
        if charges.route_inbound(phone) != "skip":
            return None

        # Áudio/voz → agent transcribe → taskme_responder
        if not _is_text(event):
            return None

        text = (getattr(event, "text", None) or "").strip()
        if not text:
            return None

        outcome_result = _parse_outcome(text)
        if outcome_result is None:
            # Ambíguo → agent handle
            return None

        outcome = outcome_result[0]
        phrase = outcome_result[1] if len(outcome_result) > 1 else None

        new_due = None
        if outcome == "reprogram":
            if not phrase:
                return None
            new_due_date = dates.resolve_due(phrase, config.now())
            if new_due_date is None:
                # Data não parseável → agent handle
                return None
            new_due = new_due_date.isoformat()

        result = charges.handle_reply(
            phone, outcome,
            new_due=new_due,
            justification=phrase if outcome == "reprogram" else None,
        )
        if result.get("error"):
            log.warning("taskme handle_reply error phone=%s: %s", phone, result)
            return None  # fall through on error

        return {"action": "skip", "reason": f"taskme-charge-{outcome}"}

    except Exception:
        log.exception("taskme pre_gateway_dispatch error")
        return None  # sempre fall-through em erro → dispatch normal
