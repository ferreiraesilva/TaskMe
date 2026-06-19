"""Criação, listagem e conclusão de tarefas."""
from __future__ import annotations

from datetime import date, datetime

from .. import config, db, notify, templates
from ..events import add_event
from ..util import normalize_phone, summarize
from . import contacts


def _to_date(value) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _next_code(cur) -> str:
    cur.execute("SELECT nextval('taskme_code_seq') AS n")
    return f"TM-{cur.fetchone()['n']}"


def propose_task(
    owner_phone: str,
    assignee_contact_id: str,
    title: str,
    description: str | None,
    due: str | None = None,
    due_phrase: str | None = None,
    now: datetime | None = None,
) -> dict:
    """Valida e resolve a data (em Python). NÃO grava. Retorna resumo p/ aprovação."""
    from ..dates import resolve_due

    contact = contacts.get_contact(assignee_contact_id)
    if not contact:
        return {"error": "contact_not_found"}

    d = _to_date(due)
    if d is None and due_phrase:
        d = resolve_due(due_phrase, now or config.now())
    if d is None:
        return {"error": "due_required"}

    if not title or not title.strip():
        return {"error": "title_required"}

    return {
        "ok": True,
        "assignee_name": contact["name"],
        "title": summarize(title, 140),
        "description": summarize(description),
        "due": d.isoformat(),
        "due_fmt": templates.fmt_date(d),
    }


def commit_task(
    owner_phone: str,
    assignee_contact_id: str,
    title: str,
    description: str | None,
    due: str,
    owner_name: str | None = None,
) -> dict:
    """Cria a tarefa, registra histórico e ENVIA ao assignado via Hermes."""
    owner = contacts.get_or_create_user(owner_phone, owner_name)
    contact = contacts.get_contact(assignee_contact_id)
    if not contact:
        return {"error": "contact_not_found"}
    d = _to_date(due)
    if d is None:
        return {"error": "due_required"}

    title = summarize(title, 140)
    description = summarize(description)

    with db.transaction() as cur:
        # 1ª tarefa daquele dono para aquele contato? (antes de inserir)
        cur.execute(
            "SELECT count(*) AS n FROM tasks WHERE assigner_user_id=%s AND assignee_contact_id=%s",
            (owner["id"], contact["id"]),
        )
        first = cur.fetchone()["n"] == 0

        code = _next_code(cur)
        cur.execute(
            """INSERT INTO tasks
                 (code, assigner_user_id, assignee_contact_id, title, description,
                  original_due_date, current_due_date)
               VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
            (code, owner["id"], contact["id"], title, description, d, d),
        )
        task_id = cur.fetchone()["id"]
        add_event(cur, task_id, "criada", "assignante", title)

    msg = templates.task_message(
        contact["name"], owner.get("name") or "a equipe", code, title, description, d, intro=first
    )
    sent = notify.send(contact["whatsapp_phone"], msg)
    with db.transaction() as cur:
        add_event(cur, task_id, "enviada", "sistema", "tarefa enviada ao assignado")

    return {
        "ok": True,
        "code": code,
        "assignee_name": contact["name"],
        "assignee_phone": contact["whatsapp_phone"],
        "due_fmt": templates.fmt_date(d),
        "sent": sent,
        "message": msg,
    }


def list_pending(phone: str, role: str) -> list[dict]:
    """Tarefas pendentes ordenadas por vencimento.

    role=assigner → o que ESSE telefone pediu; role=assignee → o que devem dele.
    """
    p = normalize_phone(phone)
    if role == "assigner":
        return db.query_all(
            """SELECT t.code, t.title, t.current_due_date, t.original_due_date, c.name AS assignee_name
                 FROM tasks t
                 JOIN users u ON u.id = t.assigner_user_id
                 JOIN contacts c ON c.id = t.assignee_contact_id
                WHERE u.whatsapp_phone = %s AND t.status = 'pendente'
                ORDER BY t.current_due_date""",
            (p,),
        )
    return db.query_all(
        """SELECT t.code, t.title, t.current_due_date, t.original_due_date,
                  u.name AS assigner_name
             FROM tasks t
             JOIN contacts c ON c.id = t.assignee_contact_id
             JOIN users u ON u.id = t.assigner_user_id
            WHERE c.whatsapp_phone = %s AND t.status = 'pendente'
            ORDER BY t.current_due_date""",
        (p,),
    )


def complete_task(task_code: str, note: str | None = None, actor: str = "assignado") -> dict:
    with db.transaction() as cur:
        cur.execute("SELECT id, status FROM tasks WHERE code = %s", (task_code,))
        row = cur.fetchone()
        if not row:
            return {"error": "task_not_found"}
        cur.execute(
            "UPDATE tasks SET status='concluida', completed_at=now(), completion_note=%s WHERE id=%s",
            (summarize(note), row["id"]),
        )
        add_event(cur, row["id"], "concluida", actor, note or "concluída")
    return {"ok": True, "code": task_code}
