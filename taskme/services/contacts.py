"""Usuários (assignantes) e caderno de contatos por dono."""
from __future__ import annotations

from .. import db
from ..util import normalize_phone


def get_or_create_user(phone: str, name: str | None = None) -> dict:
    """Assignante identificado pelo telefone que fala com o Hermes."""
    p = normalize_phone(phone)
    with db.transaction() as cur:
        cur.execute("SELECT * FROM users WHERE whatsapp_phone = %s", (p,))
        row = cur.fetchone()
        if row:
            if name and not row.get("name"):
                cur.execute("UPDATE users SET name=%s WHERE id=%s", (name, row["id"]))
                row["name"] = name
            return row
        cur.execute(
            "INSERT INTO users (whatsapp_phone, name) VALUES (%s, %s) RETURNING *",
            (p, name),
        )
        return cur.fetchone()


def resolve_contact(owner_phone: str, name: str) -> dict:
    """Procura no caderno do dono por nome (case-insensitive, parcial).

    Retorna {match: none|one|many, candidates: [...]}.
    """
    owner = get_or_create_user(owner_phone)
    like = f"%{name.strip()}%"
    rows = db.query_all(
        """SELECT id, name, whatsapp_phone FROM contacts
           WHERE owner_user_id = %s AND name ILIKE %s
           ORDER BY name""",
        (owner["id"], like),
    )
    if not rows:
        return {"match": "none", "candidates": []}
    if len(rows) == 1:
        return {"match": "one", "candidates": rows}
    return {"match": "many", "candidates": rows}


def add_contact(owner_phone: str, name: str, phone: str) -> dict:
    """Cadastra/atualiza um contato no caderno do dono. Idempotente por telefone."""
    owner = get_or_create_user(owner_phone)
    p = normalize_phone(phone)
    with db.transaction() as cur:
        cur.execute(
            """INSERT INTO contacts (owner_user_id, name, whatsapp_phone)
               VALUES (%s, %s, %s)
               ON CONFLICT (owner_user_id, whatsapp_phone)
               DO UPDATE SET name = EXCLUDED.name
               RETURNING id, name, whatsapp_phone""",
            (owner["id"], name.strip(), p),
        )
        return cur.fetchone()


def get_contact(contact_id: str) -> dict | None:
    return db.query_one("SELECT * FROM contacts WHERE id = %s", (contact_id,))
