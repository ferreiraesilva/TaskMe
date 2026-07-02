"""Digests: segunda (assignados) e diário do dia anterior (assignantes).

Escopados por canal: um mesmo telefone recebe um digest por canal em que tem
tarefas, entregue naquele canal (whatsapp|telegram)."""
from __future__ import annotations

from datetime import datetime, timedelta

from .. import config, db, notify, templates

_TZ = config.TZ_NAME


def build_monday_digests(now: datetime | None = None) -> list[dict]:
    """Para cada (assignado, canal) com pendentes, envia a lista por vencimento."""
    now = now or config.now()
    rows = db.query_all(
        """SELECT c.whatsapp_phone AS phone, c.name AS name, t.channel,
                  t.code, t.title, t.current_due_date
             FROM tasks t
             JOIN contacts c ON c.id = t.assignee_contact_id
            WHERE t.status = 'pendente'
            ORDER BY c.whatsapp_phone, t.channel, t.current_due_date""",
    )
    by_key: dict[tuple, dict] = {}
    for r in rows:
        g = by_key.setdefault((r["phone"], r["channel"]), {"name": r["name"], "items": []})
        g["items"].append(r)

    sent = []
    for (phone, channel), g in by_key.items():
        msg = templates.monday_digest(g["name"], g["items"])
        notify.send_on(phone, channel, msg)
        sent.append({"phone": phone, "channel": channel, "n": len(g["items"])})
    return sent


def _yesterday(now: datetime):
    return (now - timedelta(days=1)).date()


def build_assigner_digests(now: datetime | None = None) -> list[dict]:
    """Reporta o dia anterior para cada (assignante, canal). Só envia se houver algo."""
    now = now or config.now()
    y = _yesterday(now)

    concluidas = db.query_all(
        """SELECT u.whatsapp_phone AS phone, u.name AS assigner_name, t.channel,
                  t.code, t.title, c.name AS assignee_name,
                  t.original_due_date,
                  ((t.completed_at AT TIME ZONE %s)::date - t.original_due_date) AS atraso_dias
             FROM tasks t
             JOIN users u ON u.id = t.assigner_user_id
             JOIN contacts c ON c.id = t.assignee_contact_id
            WHERE t.status='concluida'
              AND (t.completed_at AT TIME ZONE %s)::date = %s""",
        (_TZ, _TZ, y),
    )

    reprogramadas = db.query_all(
        """SELECT DISTINCT ON (t.id)
                  u.whatsapp_phone AS phone, u.name AS assigner_name, t.channel,
                  t.code, t.title, c.name AS assignee_name,
                  t.original_due_date, e.new_due_date, e.summary AS justificativa
             FROM task_events e
             JOIN tasks t ON t.id = e.task_id
             JOIN users u ON u.id = t.assigner_user_id
             JOIN contacts c ON c.id = t.assignee_contact_id
            WHERE e.type='reprogramada'
              AND (e.created_at AT TIME ZONE %s)::date = %s
            ORDER BY t.id, e.created_at DESC""",
        (_TZ, y),
    )

    atrasadas = db.query_all(
        """SELECT u.whatsapp_phone AS phone, u.name AS assigner_name, t.channel,
                  t.code, t.title, c.name AS assignee_name, t.current_due_date
             FROM tasks t
             JOIN users u ON u.id = t.assigner_user_id
             JOIN contacts c ON c.id = t.assignee_contact_id
            WHERE t.status='pendente' AND t.current_due_date = %s
              AND NOT EXISTS (
                SELECT 1 FROM task_events e
                 WHERE e.task_id=t.id AND e.type='reprogramada'
                   AND (e.created_at AT TIME ZONE %s)::date = %s)""",
        (y, _TZ, y),
    )

    keys: dict[tuple, dict] = {}
    def _bucket(r):
        return keys.setdefault(
            (r["phone"], r["channel"]),
            {"name": r["assigner_name"], "c": [], "r": [], "a": []},
        )
    for r in concluidas:
        _bucket(r)["c"].append(r)
    for r in reprogramadas:
        _bucket(r)["r"].append(r)
    for r in atrasadas:
        _bucket(r)["a"].append(r)

    sent = []
    for (phone, channel), g in keys.items():
        msg = templates.assigner_daily(g["name"], g["c"], g["r"], g["a"])
        notify.send_on(phone, channel, msg)
        sent.append({"phone": phone, "channel": channel,
                     "concluidas": len(g["c"]), "reprogramadas": len(g["r"]), "atrasadas": len(g["a"])})
    return sent
