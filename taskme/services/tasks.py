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
    channel: str = "whatsapp",
) -> dict:
    """Cria a tarefa, registra histórico e ENVIA ao assignado via Hermes.

    `channel` é o meio pelo qual o assignante criou a tarefa (whatsapp|telegram);
    a tarefa fica escopada nesse canal e a notificação sai só por ele.
    """
    channel = (channel or "whatsapp").strip().lower()
    if channel not in ("whatsapp", "telegram"):
        channel = "whatsapp"
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
        code = _next_code(cur)
        cur.execute(
            """INSERT INTO tasks
                 (code, assigner_user_id, assignee_contact_id, title, description,
                  original_due_date, current_due_date, channel)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
            (code, owner["id"], contact["id"], title, description, d, d, channel),
        )
        task_id = cur.fetchone()["id"]
        add_event(cur, task_id, "criada", "assignante", title)
        # Abre a fila imediatamente — captura respostas antes do cron de cobrança
        cur.execute(
            """INSERT INTO interaction_queue (contact_phone, task_id, channel, status, sent_at)
               VALUES (%s, %s, %s, 'aguardando_resposta', now())""",
            (contact["whatsapp_phone"], task_id, channel),
        )

    msg = templates.task_message(
        contact["name"], owner.get("name") or "a equipe", code, title, description, d
    )
    had_targets = bool(notify.channel_targets(contact["whatsapp_phone"], channel))
    sent = notify.send_on(contact["whatsapp_phone"], channel, msg)
    with db.transaction() as cur:
        if sent:
            add_event(cur, task_id, "enviada", "sistema", "tarefa enviada ao assignado")
        else:
            add_event(cur, task_id, "nota", "sistema", "envio não entregue (canal indisponível)")

    return {
        "ok": True,
        "code": code,
        "assignee_name": contact["name"],
        "assignee_phone": contact["whatsapp_phone"],
        "due_fmt": templates.fmt_date(d),
        "channel": channel,
        "sent": sent,
        "had_targets": had_targets,
        "message": msg,
    }


def resend_task(task_code: str, requester_phone: str | None = None) -> dict:
    """Reenvia a notificação de uma tarefa existente ao assignado.

    Só o assignante (criador) pode reenviar. Grava evento no histórico e
    retorna o resultado de entrega — `had_targets` distingue "sem canal ativo"
    de "falha no gateway".
    """
    task = db.query_one(
        """SELECT t.id, t.code, t.title, t.description, t.current_due_date, t.status,
                  t.channel,
                  c.name AS assignee_name, c.whatsapp_phone AS assignee_phone,
                  u.name AS assigner_name, u.whatsapp_phone AS assigner_phone
             FROM tasks t
             JOIN contacts c ON c.id = t.assignee_contact_id
             JOIN users u ON u.id = t.assigner_user_id
            WHERE t.code = %s""",
        (task_code,),
    )
    if not task:
        return {"error": "task_not_found"}
    if requester_phone and normalize_phone(requester_phone) != normalize_phone(
        task["assigner_phone"]
    ):
        return {"error": "not_authorized"}
    if str(task["status"]) == "concluida":
        return {"error": "task_completed"}

    channel = task["channel"]
    d = _to_date(task["current_due_date"])
    msg = templates.task_message(
        task["assignee_name"], task["assigner_name"] or "a equipe",
        task["code"], task["title"], task.get("description"), d,
    )
    had_targets = bool(notify.channel_targets(task["assignee_phone"], channel))
    sent = notify.send_on(task["assignee_phone"], channel, msg)
    with db.transaction() as cur:
        if sent:
            add_event(cur, task["id"], "enviada", "sistema", "tarefa reenviada ao assignado")
        else:
            add_event(cur, task["id"], "nota", "sistema", "reenvio não entregue (canal indisponível)")

    return {
        "ok": True,
        "code": task["code"],
        "assignee_name": task["assignee_name"],
        "channel": channel,
        "sent": sent,
        "had_targets": had_targets,
    }


def list_pending(phone: str, role: str, channel: str | None = None) -> list[dict]:
    """Tarefas pendentes ordenadas por vencimento.

    role=assigner → o que ESSE telefone pediu; role=assignee → o que devem dele.
    `channel` (opcional) escopa por meio de comunicação (whatsapp|telegram).
    """
    p = normalize_phone(phone)
    ch_clause = " AND t.channel = %s" if channel else ""
    ch_params = (channel,) if channel else ()
    if role == "assigner":
        return db.query_all(
            f"""SELECT t.code, t.title, t.current_due_date, t.original_due_date, c.name AS assignee_name
                 FROM tasks t
                 JOIN users u ON u.id = t.assigner_user_id
                 JOIN contacts c ON c.id = t.assignee_contact_id
                WHERE u.whatsapp_phone = %s AND t.status = 'pendente'{ch_clause}
                ORDER BY t.current_due_date""",
            (p, *ch_params),
        )
    return db.query_all(
        f"""SELECT t.code, t.title, t.current_due_date, t.original_due_date,
                  u.name AS assigner_name
             FROM tasks t
             JOIN contacts c ON c.id = t.assignee_contact_id
             JOIN users u ON u.id = t.assigner_user_id
            WHERE c.whatsapp_phone = %s AND t.status = 'pendente'{ch_clause}
            ORDER BY t.current_due_date""",
        (p, *ch_params),
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
