"""Convites para uma pessoa iniciar a conversa com o bot no WhatsApp."""
from __future__ import annotations

import re
import secrets
from urllib.parse import quote

from . import config, db
from .util import normalize_phone

_TOKEN_RE = re.compile(r"\bTASKME\s+([A-Za-z0-9_-]{16,64})\b", re.IGNORECASE)


def _message(token: str) -> str:
    return "Olá! Quero iniciar uma conversa com o TaskMe.\nCódigo: TASKME " + token


def create(owner_phone: str, recipient_phone: str) -> dict:
    """Cria ou reutiliza um convite ativo e retorna seu link wa.me."""
    bot_phone = normalize_phone(config.WHATSAPP_BOT_PHONE)
    owner = normalize_phone(owner_phone)
    recipient = normalize_phone(recipient_phone)
    if not bot_phone:
        return {"error": "bot_phone_not_configured"}
    if not owner or not recipient:
        return {"error": "invalid_phone"}

    with db.transaction() as cur:
        cur.execute(
            """SELECT token FROM taskme_whatsapp_invites
                WHERE phone=%s AND used_at IS NULL AND expires_at > now()
                ORDER BY created_at DESC LIMIT 1""",
            (recipient,),
        )
        row = cur.fetchone()
        token = row["token"] if row else secrets.token_urlsafe(18)
        if not row:
            cur.execute(
                """INSERT INTO taskme_whatsapp_invites
                     (token, phone, owner_phone, expires_at)
                   VALUES (%s, %s, %s, now() + interval '14 days')""",
                (token, recipient, owner),
            )

    text = _message(token)
    return {
        "ok": True,
        "token": token,
        "phone": recipient,
        "url": f"https://wa.me/{bot_phone}?text={quote(text, safe='')}",
        "message": text,
    }


def redeem(text: str, address: str, expected_phone: str | None = None) -> str:
    """Consome um convite e vincula o endereco WhatsApp ao telefone correto."""
    match = _TOKEN_RE.search(text or "")
    address = str(address or "").strip()
    if not match or not address:
        return ""

    token = match.group(1)
    expected = normalize_phone(expected_phone or "")
    with db.transaction() as cur:
        cur.execute(
            """SELECT phone FROM taskme_whatsapp_invites
                WHERE token=%s AND used_at IS NULL AND expires_at > now()
                  AND (%s = '' OR phone = %s)
                FOR UPDATE""",
            (token, expected, expected),
        )
        row = cur.fetchone()
        if not row:
            return ""
        phone = normalize_phone(row["phone"])
        cur.execute(
            """INSERT INTO taskme_channels (phone, platform, address)
               VALUES (%s, 'whatsapp', %s)
               ON CONFLICT (platform, address)
               DO UPDATE SET phone=EXCLUDED.phone, enabled=true, updated_at=now()""",
            (phone, address),
        )
        cur.execute(
            """UPDATE taskme_whatsapp_invites
                  SET used_at=now(), used_address=%s
                WHERE token=%s""",
            (address, token),
        )
        return phone
