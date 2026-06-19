"""Consultas livres: o Hermes traduz NL → filtros; aqui aplicamos no banco."""
from __future__ import annotations

from datetime import date, timedelta

from .. import config, db
from ..util import normalize_phone


def _parse_period(period: str | None, today: date):
    if not period:
        return None
    if period == "last_week":
        return (today - timedelta(days=7), today)
    if period == "last_month":
        return (today - timedelta(days=30), today)
    if period.startswith("since:"):
        try:
            return (date.fromisoformat(period[6:]), today)
        except ValueError:
            return None
    if period.startswith("range:") and ".." in period:
        a, b = period[6:].split("..", 1)
        try:
            return (date.fromisoformat(a), date.fromisoformat(b))
        except ValueError:
            return None
    return None


def query_tasks(
    phone: str,
    role: str,
    status: str | None = None,
    assignee_name: str | None = None,
    period: str | None = None,
    order: str | None = None,
) -> list[dict]:
    p = normalize_phone(phone)
    today = config.today()
    where = []
    params: list = []

    if role == "assigner":
        where.append("u.whatsapp_phone = %s")
        params.append(p)
    else:
        where.append("c.whatsapp_phone = %s")
        params.append(p)

    if assignee_name and role == "assigner":
        where.append("c.name ILIKE %s")
        params.append(f"%{assignee_name}%")

    period_col = "t.current_due_date"
    if status == "pendente":
        where.append("t.status = 'pendente'")
    elif status == "concluida":
        where.append("t.status = 'concluida'")
        period_col = "(t.completed_at AT TIME ZONE %s)::date"
    elif status == "atrasada":
        where.append("t.status = 'pendente' AND t.current_due_date < %s")
        params.append(today)
    elif status == "reprogramada":
        where.append("EXISTS (SELECT 1 FROM task_events e WHERE e.task_id=t.id AND e.type='reprogramada')")

    rng = _parse_period(period, today)
    period_params: list = []
    if rng:
        if period_col.startswith("("):  # completed_at precisa do TZ
            period_params.append(config.TZ_NAME)
        where.append(f"{period_col} BETWEEN %s AND %s")
        period_params.extend([rng[0], rng[1]])

    order_sql = "t.completed_at DESC" if order == "completed" else "t.current_due_date"

    sql = f"""
        SELECT t.code, t.title, t.status, t.original_due_date, t.current_due_date,
               t.completed_at, t.reprogram_count,
               c.name AS assignee_name, u.name AS assigner_name
          FROM tasks t
          JOIN contacts c ON c.id = t.assignee_contact_id
          JOIN users u ON u.id = t.assigner_user_id
         WHERE {' AND '.join(where)}
         ORDER BY {order_sql}
    """
    return db.query_all(sql, tuple(params + period_params))


def task_detail(task_code: str, phone: str | None = None) -> dict:
    task = db.query_one(
        """SELECT t.*, c.name AS assignee_name, c.whatsapp_phone AS assignee_phone,
                  u.name AS assigner_name, u.whatsapp_phone AS assigner_phone
             FROM tasks t
             JOIN contacts c ON c.id = t.assignee_contact_id
             JOIN users u ON u.id = t.assigner_user_id
            WHERE t.code = %s""",
        (task_code,),
    )
    if not task:
        return {"error": "task_not_found"}
    if phone:
        p = normalize_phone(phone)
        if p not in (normalize_phone(task["assignee_phone"]), normalize_phone(task["assigner_phone"])):
            return {"error": "not_authorized"}
    events = db.query_all(
        """SELECT type, actor, summary, old_due_date, new_due_date, created_at
             FROM task_events WHERE task_id = %s ORDER BY created_at""",
        (task["id"],),
    )
    return {"task": task, "events": events}
