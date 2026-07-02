"""TaskMe — atribuição e follow-up de tarefas por WhatsApp e Telegram."""
from __future__ import annotations

import logging

from . import hook, schemas, tools

log = logging.getLogger("taskme.plugin")

# Cache {session_id → identidade canônica} — populado pelo on_session_start
_session_phones: dict[str, str] = {}
# Cache {session_id → (platform, user_id)} — para permitir resolução dinâmica mid-session
_session_metadata: dict[str, tuple[str, str]] = {}


def _on_session_start(session_id: str, platform: str, user_id: str, **kwargs) -> None:
    """Resolve WhatsApp/Telegram para a identidade canônica da pessoa."""
    try:
        platform_str = str(getattr(platform, "value", platform) or "").lower()
        user_id_str = str(user_id or "").strip()
        _session_metadata[session_id] = (platform_str, user_id_str)
        from .taskme.identity import resolve
        phone = resolve(platform_str, user_id_str)
        if phone:
            _session_phones[session_id] = phone
            log.debug("taskme: session %s → identity %s", session_id, phone)
    except Exception:
        log.debug("taskme on_session_start cache failed", exc_info=True)


def _inject_phone_context(session_id: str, **kwargs) -> dict | None:
    """pre_llm_call: injeta o telefone e avisa se há cobrança pendente."""
    metadata = _session_metadata.get(session_id)
    if metadata:
        platform, user_id = metadata
        from .taskme.identity import resolve
        phone = resolve(platform, user_id)
    else:
        phone = _session_phones.get(session_id)

    if not phone:
        return None

    # Atualiza o cache de telefone
    _session_phones[session_id] = phone

    try:
        from .taskme.services.charges import has_open_charge
        pending = has_open_charge(phone)
    except Exception:
        pending = False
    pending_note = (
        "\n[TaskMe] Esta pessoa tem uma cobrança de tarefa aguardando resposta. "
        "Se a mensagem for sobre outro assunto, responda normalmente. "
        "Se ela indicar que concluiu ou quiser um novo prazo, chame taskme_responder."
    ) if pending else ""
    return {
        "context": (
            f"[TaskMe] Identidade canônica do remetente desta mensagem: {phone}\n"
            f"Use este valor no parâmetro owner_phone/phone das ferramentas taskme_*.{pending_note}"
        )
    }


def register(ctx) -> None:
    """Registra ferramentas e hooks do TaskMe no Hermes."""

    # --- Ferramentas ---
    ctx.register_tool(
        name="taskme_propor_tarefa", toolset="taskme",
        schema=schemas.PROPOR_TAREFA, handler=tools.taskme_propor_tarefa,
        description="Propõe nova tarefa para confirmação antes de criar.",
    )
    ctx.register_tool(
        name="taskme_criar_tarefa", toolset="taskme",
        schema=schemas.CRIAR_TAREFA, handler=tools.taskme_criar_tarefa,
        description="Cria e envia tarefa após confirmação do usuário.",
    )
    ctx.register_tool(
        name="taskme_add_contato", toolset="taskme",
        schema=schemas.ADD_CONTATO, handler=tools.taskme_add_contato,
        description="Salva um colega no caderno de contatos.",
    )
    ctx.register_tool(
        name="taskme_consultar", toolset="taskme",
        schema=schemas.CONSULTAR, handler=tools.taskme_consultar,
        description="Consulta tarefas por status, período, pessoa.",
    )
    ctx.register_tool(
        name="taskme_detalhe", toolset="taskme",
        schema=schemas.DETALHE, handler=tools.taskme_detalhe,
        description="Retorna detalhes e histórico completo de uma tarefa.",
    )
    ctx.register_tool(
        name="taskme_reprogramar", toolset="taskme",
        schema=schemas.REPROGRAMAR, handler=tools.taskme_reprogramar,
        description="Reprograma o prazo de uma tarefa pendente.",
    )
    ctx.register_tool(
        name="taskme_concluir", toolset="taskme",
        schema=schemas.CONCLUIR, handler=tools.taskme_concluir,
        description="Marca tarefa como concluída (pelo assignante).",
    )
    ctx.register_tool(
        name="taskme_responder", toolset="taskme",
        schema=schemas.RESPONDER, handler=tools.taskme_responder,
        description="Registra resposta de ÁUDIO a cobrança de prazo (fallback do hook).",
    )
    ctx.register_tool(
        name="taskme_ajuda", toolset="taskme",
        schema=schemas.AJUDA, handler=tools.taskme_ajuda,
        description="Envia manual do TaskMe ao remetente pelo canal disponível.",
    )
    ctx.register_tool(
        name="taskme_reenviar", toolset="taskme",
        schema=schemas.REENVIAR, handler=tools.taskme_reenviar,
        description="Reenvia a notificação de uma tarefa existente ao assignado.",
    )

    # --- Hooks ---
    ctx.register_hook("on_session_start", _on_session_start)
    ctx.register_hook("pre_llm_call", _inject_phone_context)
    ctx.register_hook("pre_gateway_dispatch", hook.handle_gateway)

    log.info("TaskMe plugin registrado: 10 ferramentas + 3 hooks")
