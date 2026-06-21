"""Associa uma pessoa canônica (telefone) aos canais em que pode ser atendida."""
from __future__ import annotations

from .. import db
from ..util import normalize_phone


def link(phone: str, platform: str, address: str) -> None:
    p = normalize_phone(phone)
    platform = (platform or "").strip().lower()
    address = (address or "").strip()
    if not p or platform not in {"telegram", "whatsapp"} or not address:
        return
    with db.transaction() as cur:
        cur.execute(
            """INSERT INTO taskme_channels (phone, platform, address)
               VALUES (%s, %s, %s)
               ON CONFLICT (platform, address)
               DO UPDATE SET phone=EXCLUDED.phone, enabled=true, updated_at=now()""",
            (p, platform, address),
        )


def phone_for(platform: str, address: str) -> str:
    row = db.query_one(
        """SELECT phone FROM taskme_channels
           WHERE platform=%s AND address=%s AND enabled=true""",
        ((platform or "").lower(), str(address or "")),
    )
    return normalize_phone(row["phone"]) if row else ""


def addresses(phone: str, platforms: tuple[str, ...]) -> list[dict]:
    p = normalize_phone(phone)
    if not p or not platforms:
        return []
    return db.query_all(
        """SELECT platform, address FROM taskme_channels
           WHERE phone=%s AND platform = ANY(%s) AND enabled=true
           ORDER BY platform, address""",
        (p, list(platforms)),
    )
