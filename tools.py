"""Handlers das ferramentas TaskMe — chamados pelo Hermes quando o LLM escolhe a tool."""
from __future__ import annotations

import json
import logging

from taskme import config, dates
from taskme.services import charges, contacts, queries, reprogram as reprogram_svc, tasks
from taskme.util import normalize_phone

log = logging.getLogger("taskme.tools")


def _ok(data: dict) -> str:
    return json.dumps(data, default=str, ensure_ascii=False)


def taskme_propor_tarefa(args: dict, **kwargs) -> str:
    try:
        owner_phone = normalize_phone(args.get("owner_phone") or "")
        assignee_name = (args.get("assignee_name") or "").strip()
        title = (args.get("title") or "").strip()
        description = args.get("description") or None
        due_phrase = (args.get("due_phrase") or "").strip()

        if not owner_phone:
            return _ok({"status": "error", "message": "owner_phone obrigatório."})
        if not assignee_name:
            return _ok({"status": "error", "message": "assignee_name obrigatório."})
        if not title:
            return _ok({"status": "error", "message": "title obrigatório."})
        if not due_phrase:
            return _ok({"status": "error", "message": "due_phrase obrigatório."})

        contact_result = contacts.resolve_contact(owner_phone, assignee_name)
        match = contact_result.get("match")

        if match == "none":
            return _ok({
                "status": "contact_not_found",
                "message": (
                    f"Não encontrei '{assignee_name}' nos seus contatos. "
                    f"Qual é o número WhatsApp de {assignee_name}? (formato: 5562...)"
                ),
            })
        if match == "many":
            names = ", ".join(c["name"] for c in contact_result.get("candidates", []))
            return _ok({
                "status": "ambiguous_contact",
                "message": f"Encontrei vários contatos com esse nome: {names}. Qual você quis dizer?",
                "candidates": contact_result.get("candidates", []),
            })

        contact = contact_result["candidates"][0]
        proposal = tasks.propose_task(
            owner_phone, contact["id"], title, description,
            due_phrase=due_phrase, now=config.now(),
        )

        if proposal.get("error") == "due_required":
            return _ok({
                "status": "due_required",
                "message": (
                    f"Não consegui interpretar o prazo '{due_phrase}'. "
                    "Qual é o prazo? (ex: 'sexta', 'dia 25', 'em 3 dias')"
                ),
            })
        if proposal.get("error"):
            return _ok({"status": "error", "message": proposal["error"]})

        return _ok({
            "status": "ok",
            "assignee_name": contact["name"],
            "assignee_contact_id": str(contact["id"]),
            "title": proposal["title"],
            "description": proposal.get("description"),
            "due": proposal["due"],
            "due_fmt": proposal["due_fmt"],
            "preview": (
                f"Vou criar:\n"
                f"• Para: {contact['name']}\n"
                f"• Tarefa: {proposal['title']}\n"
                f"• Prazo: {proposal['due_fmt']}\n\n"
                f"Confirma? (sim / não)"
            ),
        })
    except Exception as e:
        log.exception("taskme_propor_tarefa")
        return _ok({"status": "error", "message": str(e)})


def taskme_criar_tarefa(args: dict, **kwargs) -> str:
    try:
        owner_phone = normalize_phone(args.get("owner_phone") or "")
        owner_name = args.get("owner_name") or None
        assignee_contact_id = (args.get("assignee_contact_id") or "").strip()
        title = (args.get("title") or "").strip()
        description = args.get("description") or None
        due = (args.get("due") or "").strip()

        if not all([owner_phone, assignee_contact_id, title, due]):
            return _ok({"status": "error", "message": "Parâmetros obrigatórios ausentes (owner_phone, assignee_contact_id, title, due)."})

        result = tasks.commit_task(
            owner_phone, assignee_contact_id, title, description, due,
            owner_name=owner_name,
        )
        if result.get("error"):
            return _ok({"status": "error", "message": result["error"]})

        return _ok({
            "status": "ok",
            "code": result["code"],
            "message": f"Tarefa {result['code']} criada e enviada para {result['assignee_name']} ✓",
        })
    except Exception as e:
        log.exception("taskme_criar_tarefa")
        return _ok({"status": "error", "message": str(e)})


def taskme_add_contato(args: dict, **kwargs) -> str:
    try:
        owner_phone = normalize_phone(args.get("owner_phone") or "")
        assignee_name = (args.get("assignee_name") or "").strip()
        assignee_phone = normalize_phone(args.get("assignee_phone") or "")

        if not all([owner_phone, assignee_name, assignee_phone]):
            return _ok({"status": "error", "message": "Parâmetros obrigatórios ausentes (owner_phone, assignee_name, assignee_phone)."})

        result = contacts.add_contact(owner_phone, assignee_name, assignee_phone)
        return _ok({
            "status": "ok",
            "contact_id": str(result["id"]),
            "name": result["name"],
            "message": f"Contato {result['name']} salvo. Pode prosseguir com a tarefa.",
        })
    except Exception as e:
        log.exception("taskme_add_contato")
        return _ok({"status": "error", "message": str(e)})


def taskme_consultar(args: dict, **kwargs) -> str:
    try:
        phone = normalize_phone(args.get("phone") or "")
        role = args.get("role") or ""
        status = args.get("status") or None
        assignee_name = args.get("assignee_name") or None
        period = args.get("period") or None
        order = args.get("order") or None

        if not phone or not role:
            return _ok({"status": "error", "message": "phone e role são obrigatórios."})

        result = queries.query_tasks(
            phone, role, status=status, assignee_name=assignee_name,
            period=period, order=order,
        )
        return _ok({"status": "ok", "tasks": result, "count": len(result)})
    except Exception as e:
        log.exception("taskme_consultar")
        return _ok({"status": "error", "message": str(e)})


def taskme_detalhe(args: dict, **kwargs) -> str:
    try:
        task_code = (args.get("task_code") or "").strip().upper()
        phone = normalize_phone(args.get("phone") or "")

        if not task_code:
            return _ok({"status": "error", "message": "task_code obrigatório."})

        result = queries.task_detail(task_code, phone=phone or None)
        if result.get("error"):
            return _ok({"status": "error", "message": result["error"]})

        return _ok({"status": "ok", **result})
    except Exception as e:
        log.exception("taskme_detalhe")
        return _ok({"status": "error", "message": str(e)})


def taskme_reprogramar(args: dict, **kwargs) -> str:
    try:
        task_code = (args.get("task_code") or "").strip().upper()
        new_due_phrase = (args.get("new_due_phrase") or "").strip()
        justification = args.get("justification") or ""
        by = args.get("by") or "assignante"

        if not task_code or not new_due_phrase:
            return _ok({"status": "error", "message": "task_code e new_due_phrase são obrigatórios."})

        new_due_date = dates.resolve_due(new_due_phrase, config.now())
        if new_due_date is None:
            return _ok({
                "status": "due_required",
                "message": f"Não consegui interpretar o prazo '{new_due_phrase}'. Qual é a nova data?",
            })

        result = reprogram_svc.reprogram(task_code, new_due_date.isoformat(), justification, by=by)
        if result.get("error"):
            return _ok({"status": "error", "message": result["error"]})

        return _ok({
            "status": "ok",
            "message": f"Tarefa {task_code} reprogramada para {result['new_due_fmt']} ✓",
        })
    except Exception as e:
        log.exception("taskme_reprogramar")
        return _ok({"status": "error", "message": str(e)})


def taskme_concluir(args: dict, **kwargs) -> str:
    try:
        task_code = (args.get("task_code") or "").strip().upper()
        note = args.get("note") or None

        if not task_code:
            return _ok({"status": "error", "message": "task_code obrigatório."})

        result = tasks.complete_task(task_code, note=note, actor="assignante")
        if result.get("error"):
            return _ok({"status": "error", "message": result["error"]})

        return _ok({"status": "ok", "message": f"Tarefa {task_code} marcada como concluída ✓"})
    except Exception as e:
        log.exception("taskme_concluir")
        return _ok({"status": "error", "message": str(e)})


def taskme_responder(args: dict, **kwargs) -> str:
    """Fallback para respostas em áudio a cobranças."""
    try:
        phone = normalize_phone(args.get("phone") or "")
        outcome = (args.get("outcome") or "").strip()
        task_code = args.get("task_code") or None
        new_due_phrase = (args.get("new_due_phrase") or "").strip()
        justification = args.get("justification") or None

        if not phone or not outcome:
            return _ok({"status": "error", "message": "phone e outcome são obrigatórios."})

        new_due = None
        if outcome == "reprogram":
            if not new_due_phrase:
                return _ok({
                    "status": "due_required",
                    "message": "Para reprogramar, informe o novo prazo (new_due_phrase).",
                })
            new_due_date = dates.resolve_due(new_due_phrase, config.now())
            if new_due_date is None:
                return _ok({
                    "status": "due_required",
                    "message": f"Não consegui interpretar o prazo '{new_due_phrase}'. Qual é a nova data?",
                })
            new_due = new_due_date.isoformat()

        result = charges.handle_reply(
            phone, outcome,
            task_code=task_code,
            new_due=new_due,
            justification=justification,
        )
        if result.get("error"):
            return _ok({"status": "error", "message": result["error"]})

        return _ok({
            "status": "ok",
            "message": result.get("ack", "Resposta registrada."),
        })
    except Exception as e:
        log.exception("taskme_responder")
        return _ok({"status": "error", "message": str(e)})
