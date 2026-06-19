"""Reprogramação (pelo assignante ou pelo assignado). Mantém a data original."""
from __future__ import annotations

from datetime import date, datetime

from .. import db, templates
from ..events import add_event
from ..util import summarize


def _to_date(value) -> date | None:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError):
        return None


def reprogram(task_code: str, new_due, justification: str | None, by: str = "assignado") -> dict:
    d = _to_date(new_due)
    if d is None:
        return {"error": "new_due_required"}
    with db.transaction() as cur:
        cur.execute("SELECT id, status, current_due_date FROM tasks WHERE code=%s", (task_code,))
        row = cur.fetchone()
        if not row:
            return {"error": "task_not_found"}
        if row["status"] == "concluida":
            return {"error": "already_completed"}
        cur.execute(
            """UPDATE tasks
                 SET current_due_date=%s, reprogram_count = reprogram_count + 1
               WHERE id=%s""",
            (d, row["id"]),
        )
        add_event(
            cur, row["id"], "reprogramada", by,
            summarize(justification), old_due=row["current_due_date"], new_due=d,
        )
    return {"ok": True, "code": task_code, "new_due": d.isoformat(), "new_due_fmt": templates.fmt_date(d)}
