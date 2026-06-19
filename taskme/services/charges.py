"""Cobrança no vencimento + fila 1-pergunta-por-vez por telefone.

Regras:
- No dia (e depois, se não respondida) cobra a tarefa vencida.
- 1 pergunta aberta por telefone: se já há cobrança aguardando resposta para
  aquele telefone, repica a MESMA tarefa (1×/dia) e não inicia outra.
- Quando o assignado responde, registra e dispara a próxima cobrança do telefone.
"""
from __future__ import annotations

from datetime import datetime

from .. import config, db, notify, templates
from ..events import add_event
from ..util import normalize_phone
from . import reprogram as reprogram_svc
from . import tasks as tasks_svc


# ---------- leitura de estado ----------
def _open_charge_for_phone(phone: str) -> dict | None:
    """Cobrança aguardando resposta (tarefa ainda pendente) para o telefone."""
    return db.query_one(
        """SELECT q.id AS queue_id, t.id AS task_id, t.code, t.title
             FROM interaction_queue q
             JOIN tasks t ON t.id = q.task_id
            WHERE q.contact_phone = %s AND q.status = 'aguardando_resposta'
              AND t.status = 'pendente'
            LIMIT 1""",
        (phone,),
    )


def has_open_charge(phone: str) -> bool:
    return _open_charge_for_phone(normalize_phone(phone)) is not None


def route_inbound(phone: str) -> str:
    """Decisão do hook: 'skip' se há cobrança aberta p/ o telefone; senão 'allow'."""
    return "skip" if has_open_charge(phone) else "allow"


# ---------- envio ----------
def _send_charge(phone: str, contact_name: str, code: str, title: str, task_id: str) -> None:
    notify.send(phone, templates.due_charge(contact_name, code, title))
    with db.transaction() as cur:
        add_event(cur, task_id, "cobranca", "sistema", f"cobrança enviada ({code})")


def _start_charge_for_phone(phone: str, now: datetime) -> dict | None:
    """Inicia a cobrança da tarefa vencida mais antiga do telefone (sem pergunta
    aberta). Cria/garante a linha de fila e envia. Retorna {phone, code} ou None."""
    today = now.date()
    task = db.query_one(
        """SELECT t.id, t.code, t.title, c.name AS cname
             FROM tasks t
             JOIN contacts c ON c.id = t.assignee_contact_id
            WHERE c.whatsapp_phone = %s AND t.status = 'pendente'
              AND t.current_due_date <= %s
            ORDER BY t.current_due_date
            LIMIT 1""",
        (phone, today),
    )
    if not task:
        return None
    with db.transaction() as cur:
        # reusa linha pendente/aberta ou cria nova
        cur.execute(
            """SELECT id FROM interaction_queue
                WHERE contact_phone=%s AND task_id=%s AND status <> 'respondida'
                LIMIT 1""",
            (phone, task["id"]),
        )
        q = cur.fetchone()
        if q:
            cur.execute(
                "UPDATE interaction_queue SET status='aguardando_resposta', sent_at=now() WHERE id=%s",
                (q["id"],),
            )
        else:
            cur.execute(
                """INSERT INTO interaction_queue (contact_phone, task_id, status, sent_at)
                   VALUES (%s,%s,'aguardando_resposta', now())""",
                (phone, task["id"]),
            )
    _send_charge(phone, task["cname"], task["code"], task["title"], task["id"])
    return {"phone": phone, "code": task["code"]}


def build_due_charges(now: datetime | None = None) -> list[dict]:
    """Roda diariamente (cron). Para cada telefone com tarefa vencida e pendente:
    repica a pergunta aberta (1×/dia) ou inicia a tarefa mais antiga."""
    now = now or config.now()
    today = now.date()
    phones = db.query_all(
        """SELECT DISTINCT c.whatsapp_phone AS phone
             FROM tasks t JOIN contacts c ON c.id = t.assignee_contact_id
            WHERE t.status='pendente' AND t.current_due_date <= %s""",
        (today,),
    )
    sent: list[dict] = []
    for p in phones:
        phone = p["phone"]
        openc = _open_charge_for_phone(phone)
        if openc:  # repique da mesma tarefa
            # nome do contato p/ template
            c = db.query_one(
                "SELECT name FROM contacts WHERE whatsapp_phone=%s LIMIT 1", (phone,)
            )
            _send_charge(phone, c["name"] if c else "", openc["code"], openc["title"], openc["task_id"])
            with db.transaction() as cur:
                cur.execute(
                    "UPDATE interaction_queue SET sent_at=now() WHERE id=%s", (openc["queue_id"],)
                )
            sent.append({"phone": phone, "code": openc["code"], "repique": True})
        else:
            r = _start_charge_for_phone(phone, now)
            if r:
                sent.append(r)
    return sent


# ---------- resposta do assignado ----------
def handle_reply(
    phone: str,
    outcome: str,
    task_code: str | None = None,
    new_due=None,
    justification: str | None = None,
    note: str | None = None,
    now: datetime | None = None,
) -> dict:
    """Processa a resposta a uma cobrança. outcome: 'done' | 'reprogram'.
    Fecha a fila e dispara a próxima cobrança do telefone (serialização)."""
    now = now or config.now()
    p = normalize_phone(phone)

    if task_code:
        row = db.query_one(
            """SELECT q.id AS queue_id, t.code
                 FROM tasks t
                 LEFT JOIN interaction_queue q
                   ON q.task_id=t.id AND q.contact_phone=%s AND q.status='aguardando_resposta'
                WHERE t.code=%s""",
            (p, task_code),
        )
        if not row:
            return {"error": "task_not_found"}
        code, queue_id = row["code"], row.get("queue_id")
    else:
        openc = _open_charge_for_phone(p)
        if not openc:
            return {"error": "no_open_charge"}
        code, queue_id = openc["code"], openc["queue_id"]

    if outcome == "done":
        res = tasks_svc.complete_task(code, note, actor="assignado")
        ack = templates.ack_concluida()
    elif outcome == "reprogram":
        res = reprogram_svc.reprogram(code, new_due, justification, by="assignado")
        if "error" in res:
            return res
        ack = templates.ack_reprogramada(__import__("datetime").date.fromisoformat(res["new_due"]))
    else:
        return {"error": "invalid_outcome"}
    if "error" in res:
        return res

    if queue_id:
        with db.transaction() as cur:
            cur.execute(
                "UPDATE interaction_queue SET status='respondida', answered_at=now() WHERE id=%s",
                (queue_id,),
            )

    # ack imediato + próxima cobrança da fila (se houver)
    notify.send(p, ack)
    nxt = _start_charge_for_phone(p, now)
    return {"ok": True, "code": code, "ack": ack, "next_charge": nxt}
