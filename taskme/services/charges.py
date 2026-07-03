"""Cobrança no vencimento + fila 1-pergunta-por-vez por (telefone, canal).

Regras:
- No dia (e depois, se não respondida) cobra a tarefa vencida.
- 1 pergunta aberta por (telefone, canal): se já há cobrança aguardando
  resposta para aquele telefone naquele canal, repica a MESMA tarefa (1×/dia)
  e não inicia outra. A mesma pessoa pode ter cobrança aberta no WhatsApp e
  outra no Telegram simultaneamente (canais são escopos separados).
- Quando o assignado responde, registra e dispara a próxima cobrança do
  telefone naquele canal.
"""
from __future__ import annotations

from datetime import date, datetime

from .. import config, db, notify, templates
from ..events import add_event
from ..util import normalize_phone
from . import reprogram as reprogram_svc
from . import tasks as tasks_svc


# ---------- leitura de estado ----------
def _open_charge_for_phone(phone: str, channel: str | None = None) -> dict | None:
    """Cobrança aguardando resposta (tarefa ainda pendente) para o telefone,
    opcionalmente escopada a um canal."""
    ch_clause = " AND q.channel = %s" if channel else ""
    params = (phone, channel) if channel else (phone,)
    return db.query_one(
        f"""SELECT q.id AS queue_id, t.id AS task_id, t.code, t.title, t.channel
             FROM interaction_queue q
             JOIN tasks t ON t.id = q.task_id
            WHERE q.contact_phone = %s AND q.status = 'aguardando_resposta'
              AND t.status = 'pendente'{ch_clause}
            LIMIT 1""",
        params,
    )


def has_open_charge(phone: str, channel: str | None = None) -> bool:
    return _open_charge_for_phone(normalize_phone(phone), channel) is not None


def route_inbound(phone: str, channel: str | None = None) -> str:
    """Decisão do hook: 'skip' se há cobrança aberta p/ o telefone (naquele
    canal, se informado); senão 'allow'."""
    return "skip" if has_open_charge(phone, channel) else "allow"


# Marcador de estado: já pedimos a nova data e aguardamos o assignado informá-la.
_AWAIT_DUE_MARK = "aguardando nova data informada pelo assignado"


def request_new_due(phone: str, channel: str | None = None) -> str:
    """Assignado sinalizou remarcação SEM data parseável.

    Pede a nova data de forma determinística (não depende do agente) — 1 vez por
    "rodada": se a última interação já foi este pedido e a pessoa ainda não deu
    a data, devolve 'defer' para o agente conduzir (evita loop).

    Retorna 'asked' (perguntou → o hook deve dar skip no dispatch) ou 'defer'.
    """
    p = normalize_phone(phone)
    openc = _open_charge_for_phone(p, channel)
    if not openc:
        return "defer"
    last = db.query_one(
        "SELECT type, summary FROM task_events WHERE task_id=%s ORDER BY created_at DESC LIMIT 1",
        (openc["task_id"],),
    )
    if last and last.get("type") == "nota" and last.get("summary") == _AWAIT_DUE_MARK:
        return "defer"
    notify.send_on(
        p, openc["channel"], templates.ask_new_due(openc["code"]),
        idempotency_key=f"task:{openc['task_id']}:ask-new-due",
    )
    with db.transaction() as cur:
        add_event(cur, openc["task_id"], "nota", "sistema", _AWAIT_DUE_MARK)
    return "asked"


# ---------- envio ----------
def _send_charge(
    phone: str, channel: str, contact_name: str, code: str, title: str,
    task_id: str, delivery_date: date | None = None,
) -> None:
    delivery_date = delivery_date or config.today()
    notify.send_on(
        phone, channel, templates.due_charge(contact_name, code, title),
        idempotency_key=f"task:{task_id}:due-charge:{delivery_date.isoformat()}",
    )
    with db.transaction() as cur:
        add_event(cur, task_id, "cobranca", "sistema", f"cobrança enviada ({code})")


def _start_charge_for_phone(phone: str, channel: str, now: datetime) -> dict | None:
    """Inicia a cobrança da tarefa vencida mais antiga do telefone naquele canal
    (sem pergunta aberta). Cria/garante a linha de fila e envia."""
    today = now.date()
    task = db.query_one(
        """SELECT t.id, t.code, t.title, t.channel, c.name AS cname
             FROM tasks t
             JOIN contacts c ON c.id = t.assignee_contact_id
            WHERE c.whatsapp_phone = %s AND t.channel = %s AND t.status = 'pendente'
              AND t.current_due_date <= %s
            ORDER BY t.current_due_date
            LIMIT 1""",
        (phone, channel, today),
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
                """INSERT INTO interaction_queue (contact_phone, task_id, channel, status, sent_at)
                   VALUES (%s,%s,%s,'aguardando_resposta', now())""",
                (phone, task["id"], channel),
            )
    _send_charge(
        phone, task["channel"], task["cname"], task["code"], task["title"],
        task["id"], delivery_date=today,
    )
    return {"phone": phone, "channel": channel, "code": task["code"]}


def build_due_charges(now: datetime | None = None) -> list[dict]:
    """Roda diariamente (cron). Para cada (telefone, canal) com tarefa vencida e
    pendente: repica a pergunta aberta (1×/dia) ou inicia a tarefa mais antiga."""
    now = now or config.now()
    today = now.date()
    pairs = db.query_all(
        """SELECT DISTINCT c.whatsapp_phone AS phone, t.channel AS channel
             FROM tasks t JOIN contacts c ON c.id = t.assignee_contact_id
            WHERE t.status='pendente' AND t.current_due_date <= %s""",
        (today,),
    )
    sent: list[dict] = []
    for pair in pairs:
        phone, channel = pair["phone"], pair["channel"]
        openc = _open_charge_for_phone(phone, channel)
        if openc:  # repique da mesma tarefa
            c = db.query_one(
                "SELECT name FROM contacts WHERE whatsapp_phone=%s LIMIT 1", (phone,)
            )
            _send_charge(
                phone, channel, c["name"] if c else "", openc["code"],
                openc["title"], openc["task_id"], delivery_date=today,
            )
            with db.transaction() as cur:
                cur.execute(
                    "UPDATE interaction_queue SET sent_at=now() WHERE id=%s", (openc["queue_id"],)
                )
            sent.append({"phone": phone, "channel": channel, "code": openc["code"], "repique": True})
        else:
            r = _start_charge_for_phone(phone, channel, now)
            if r:
                sent.append(r)
    return sent


# ---------- resposta do assignado ----------
def handle_reply(
    phone: str,
    outcome: str,
    channel: str | None = None,
    task_code: str | None = None,
    new_due=None,
    justification: str | None = None,
    note: str | None = None,
    now: datetime | None = None,
) -> dict:
    """Processa a resposta a uma cobrança. outcome: 'done' | 'reprogram'.
    Escopada ao canal (quando informado). Fecha a fila e dispara a próxima
    cobrança do telefone naquele canal (serialização)."""
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
        openc = _open_charge_for_phone(p, channel)
        if not openc:
            return {"error": "no_open_charge"}
        code, queue_id = openc["code"], openc["queue_id"]

    # Carrega info da tarefa para notificar o assigner (no canal da tarefa)
    task_info = db.query_one(
        """SELECT u.whatsapp_phone AS assigner_phone, u.name AS assigner_name,
                  c.name AS assignee_name, t.title, t.channel
             FROM tasks t
             JOIN users u ON u.id = t.assigner_user_id
             JOIN contacts c ON c.id = t.assignee_contact_id
            WHERE t.code = %s""",
        (code,),
    )
    task_channel = task_info["channel"] if task_info else (channel or "whatsapp")

    assigner_msg = None
    if outcome == "done":
        res = tasks_svc.complete_task(code, note, actor="assignado")
        ack = templates.ack_concluida()
        if task_info:
            assigner_msg = templates.ack_assigner_done(
                task_info["assignee_name"], code, task_info["title"]
            )
    elif outcome == "reprogram":
        res = reprogram_svc.reprogram(code, new_due, justification, by="assignado")
        if "error" in res:
            return res
        new_due_date = __import__("datetime").date.fromisoformat(res["new_due"])
        ack = templates.ack_reprogramada(new_due_date)
        if task_info:
            assigner_msg = templates.ack_assigner_reprogram(
                task_info["assignee_name"], code, task_info["title"], new_due_date, justification
            )
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

    # ack para o assignado + notificação em tempo real ao assigner, ambos no canal da tarefa
    outcome_version = str(new_due or "done")
    notify.send_on(
        p, task_channel, ack,
        idempotency_key=f"task:{code}:assignee-ack:{outcome}:{outcome_version}",
    )
    if task_info and task_info.get("assigner_phone") and assigner_msg:
        notify.send_on(
            task_info["assigner_phone"], task_channel, assigner_msg,
            idempotency_key=f"task:{code}:assigner-ack:{outcome}:{outcome_version}",
        )

    nxt = _start_charge_for_phone(p, task_channel, now)
    return {"ok": True, "code": code, "ack": ack, "next_charge": nxt}
