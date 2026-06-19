"""Log append-only de eventos da tarefa (histórico)."""
from __future__ import annotations

from datetime import date

import psycopg

from .util import summarize


def add_event(
    cur: psycopg.Cursor,
    task_id: str,
    type: str,
    actor: str,
    summary: str | None = None,
    old_due: date | None = None,
    new_due: date | None = None,
) -> None:
    """Insere um evento usando o cursor da transação em curso."""
    cur.execute(
        """INSERT INTO task_events (task_id, type, actor, summary, old_due_date, new_due_date)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (task_id, type, actor, summarize(summary), old_due, new_due),
    )
