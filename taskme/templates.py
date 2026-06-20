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
def help_message() -> str:
    return (
        "👋 Olá! Sou o *TaskMe*, assistente de tarefas via WhatsApp.\n\n"
        "Funciono nos dois sentidos — você pode *receber* tarefas de quem te atribuiu, "
        "e também pode *enviar* tarefas para qualquer pessoa que você tenha no WhatsApp, "
        "da sua equipe ou não, em qualquer lugar do mundo.\n\n"
        "*Se alguém te atribuiu uma tarefa:*\n"
        "📋 Você recebe a tarefa com prazo e ID (ex: TM-1042)\n"
        "📅 Toda segunda, um resumo das suas pendentes\n"
        "🔔 No dia do vencimento, vou te cobrar aqui\n"
        "✅ Responda \"feito\" ou \"pronto\" para concluir\n"
        "📆 Ou me diga um novo prazo para renegociar\n\n"
        "*Se você quiser atribuir tarefas para alguém:*\n"
        "💬 É só me pedir — ex: \"cria uma tarefa para a Ana entregar o contrato até sexta\"\n"
        "👤 Na primeira vez, vou pedir o número de WhatsApp da pessoa\n"
        "📲 Depois de confirmado, envio a tarefa direto para ela e acompanho o prazo\n\n"
        "*Para consultar seu histórico, é só perguntar:*\n"
        "📂 \"Minhas tarefas pendentes\" — o que você ainda deve entregar\n"
        "📂 \"O que pedi pra fulano\" — tarefas que você atribuiu a alguém\n"
        "⚠️ \"Tenho alguma atrasada?\" — pendentes com prazo vencido\n"
        "✅ \"O que entreguei essa semana\" — suas conclusões no período\n"
        "🔁 \"O que foi reprogramado?\" — tarefas com prazo renegociado\n"
        "🔍 \"Detalhes da TM-1042\" — histórico completo de uma tarefa específica\n\n"
        "Tudo por aqui, sem app extra."
    )


def task_message(
    assignee_name: str,
    assigner_name: str,
    code: str,
    title: str,
    description: str | None,
    due: date,
) -> str:
    desc_line = f"\n📝 Descrição: {description}" if description else ""
    return (
        f"{assignee_name}, uma nova tarefa foi atribuída a você pelo TaskMe:\n\n"
        f"👤 De: {assigner_name}\n"
        f"📋 Tarefa: {title}{desc_line}\n"
        f"📅 Prazo: {fmt_date(due)}\n"
        f"🔖 ID: {code}\n\n"
        "Me avise quando concluir ou se precisar negociar o prazo."
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
