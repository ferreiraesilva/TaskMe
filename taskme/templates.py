"""Textos PT-BR (tom imperativo na atribuição). Gerados em Python e enviados
verbatim pelo Hermes — o agente não compõe mensagem de tarefa.
"""
from __future__ import annotations

from datetime import date

_WD = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]


def fmt_date(d: date) -> str:
    return d.strftime("%d/%m/%Y")


def fmt_date_long(d: date) -> str:
    return f"{_WD[d.weekday()]}, {d.strftime('%d/%m/%Y')}"


# ---------- Atribuição ----------
def intro_prefix(assigner_name: str) -> str:
    return (
        f"Olá! Aqui é o assistente de tarefas de {assigner_name}. "
        "Eu organizo e acompanho tarefas por aqui: vou te avisar de prazos às "
        "segundas e cobrar no dia do vencimento. É só me responder por aqui "
        "(texto ou áudio).\n\nSua primeira tarefa:"
    )


def task_message(
    assignee_name: str,
    assigner_name: str,
    code: str,
    title: str,
    description: str | None,
    due: date,
    *,
    intro: bool = False,
) -> str:
    head = intro_prefix(assigner_name) if intro else f"{assignee_name}, {assigner_name} te atribuiu uma tarefa:"
    desc = f"\n{description}" if description else ""
    return (
        f"{head}\n\n"
        f"*{title}* [{code}]{desc}\n"
        f"📅 Prazo: {fmt_date(due)}\n\n"
        "Pode confirmar? Se precisar de mais prazo, me avise a nova data e o motivo."
    )


# ---------- Lembrete de segunda (digest do assignado) ----------
def monday_digest(assignee_name: str, items: list[dict]) -> str:
    linhas = []
    for i, t in enumerate(items, 1):
        linhas.append(f"{i}. *{t['title']}* [{t['code']}] — vence {fmt_date(t['current_due_date'])}")
    corpo = "\n".join(linhas)
    return (
        f"Bom dia, {assignee_name}! Suas tarefas pendentes (por vencimento):\n\n"
        f"{corpo}\n\n"
        "Alguma precisa de novo prazo? É só me dizer."
    )


# ---------- Cobrança no vencimento ----------
def due_charge(assignee_name: str, code: str, title: str) -> str:
    return (
        f"{assignee_name}, hoje é o prazo de:\n*{title}* [{code}]\n\n"
        "Concluiu? Se ainda não, me diga o que faltou e a nova data."
    )


# ---------- Acks ----------
def ack_concluida() -> str:
    return "Obrigado pelo retorno! Registrei a tarefa como *concluída*. ✅"


def ack_reprogramada(new_due: date) -> str:
    return f"Anotado. Novo prazo registrado para *{fmt_date(new_due)}*. Te cobro nessa data."


# ---------- Digest diário do assignante ----------
def assigner_daily(assigner_name: str, concluidas: list[dict], reprogramadas: list[dict], atrasadas: list[dict]) -> str:
    partes = [f"Resumo de hoje, {assigner_name}:"]

    if concluidas:
        partes.append("\n✅ *Concluídas*")
        for t in concluidas:
            atraso = t["atraso_dias"]
            sinal = f"{atraso:+d} dia(s)" if atraso else "no prazo"
            partes.append(
                f"• *{t['title']}* [{t['code']}] — {t['assignee_name']} "
                f"(prazo orig. {fmt_date(t['original_due_date'])}, {sinal})"
            )

    if reprogramadas:
        partes.append("\n🔁 *Reprogramadas*")
        for t in reprogramadas:
            just = f" — {t['justificativa']}" if t.get("justificativa") else ""
            partes.append(
                f"• *{t['title']}* [{t['code']}] — {t['assignee_name']}: "
                f"{fmt_date(t['original_due_date'])} → {fmt_date(t['new_due_date'])}{just}"
            )

    if atrasadas:
        partes.append("\n⚠️ *Atrasadas (sem retorno)*")
        for t in atrasadas:
            partes.append(
                f"• *{t['title']}* [{t['code']}] — {t['assignee_name']} "
                f"(venceu {fmt_date(t['current_due_date'])})"
            )

    return "\n".join(partes)
