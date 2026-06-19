"""Schemas das ferramentas TaskMe — o que o LLM vê."""

PROPOR_TAREFA = {
    "name": "taskme_propor_tarefa",
    "description": (
        "OBRIGATÓRIO para qualquer pedido de criar/atribuir/delegar tarefa a outra pessoa. "
        "Use SEMPRE que o usuário mencionar tarefa para um colega (Larissa, João, Ana, etc.). "
        "NUNCA use ferramentas internas de todo/kanban para isso. "
        "Propõe a tarefa sem gravar — retorna preview para o usuário confirmar. "
        "Só após confirmação, chame taskme_criar_tarefa."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "owner_phone": {
                "type": "string",
                "description": "Número WhatsApp do remetente desta mensagem (apenas dígitos, sem +).",
            },
            "assignee_name": {
                "type": "string",
                "description": "Nome (ou apelido) de quem vai executar a tarefa.",
            },
            "title": {
                "type": "string",
                "description": (
                    "Título da tarefa no imperativo (ex: 'Envie o relatório de vendas'). "
                    "Resuma e deixe no imperativo se o usuário não o fez."
                ),
            },
            "description": {
                "type": "string",
                "description": "Detalhes opcionais da tarefa (resumido, máx 280 chars).",
            },
            "due_phrase": {
                "type": "string",
                "description": (
                    "Frase do prazo exatamente como o usuário disse "
                    "(ex: 'sexta', 'dia 20', 'em 3 dias', 'fim do mês'). "
                    "Nunca resolva a data — repasse a frase crua."
                ),
            },
        },
        "required": ["owner_phone", "assignee_name", "title", "due_phrase"],
    },
}

CRIAR_TAREFA = {
    "name": "taskme_criar_tarefa",
    "description": (
        "Cria e envia a tarefa após o usuário confirmar a proposta. "
        "Use SOMENTE depois que o usuário disse 'sim', 'confirma' ou equivalente "
        "sobre a proposta exibida por taskme_propor_tarefa. "
        "Nunca chame sem confirmação explícita."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "owner_phone": {
                "type": "string",
                "description": "Número WhatsApp do remetente (apenas dígitos, sem +).",
            },
            "owner_name": {
                "type": "string",
                "description": "Nome do remetente (para a intro na 1ª tarefa enviada ao destinatário).",
            },
            "assignee_contact_id": {
                "type": "string",
                "description": "ID do contato retornado por taskme_propor_tarefa.",
            },
            "title": {
                "type": "string",
                "description": "Título imperativo da tarefa (igual ao retornado pela proposta).",
            },
            "description": {
                "type": "string",
                "description": "Detalhes opcionais (igual ao retornado pela proposta).",
            },
            "due": {
                "type": "string",
                "description": "Data em formato YYYY-MM-DD (retornada pela proposta).",
            },
        },
        "required": ["owner_phone", "assignee_contact_id", "title", "due"],
    },
}

ADD_CONTATO = {
    "name": "taskme_add_contato",
    "description": (
        "Salva o número WhatsApp de um colega no caderno de contatos do usuário. "
        "Use quando taskme_propor_tarefa retornar status=contact_not_found e o usuário "
        "informar o número. Depois de salvar, chame taskme_propor_tarefa novamente."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "owner_phone": {
                "type": "string",
                "description": "Número WhatsApp do remetente (apenas dígitos, sem +).",
            },
            "assignee_name": {
                "type": "string",
                "description": "Nome do contato a salvar.",
            },
            "assignee_phone": {
                "type": "string",
                "description": "Número WhatsApp do contato (apenas dígitos, sem +).",
            },
        },
        "required": ["owner_phone", "assignee_name", "assignee_phone"],
    },
}

CONSULTAR = {
    "name": "taskme_consultar",
    "description": (
        "Consulta tarefas do usuário com filtros. Use para: "
        "'minhas pendentes', 'o que pedi pra alguém', 'tarefas atrasadas', "
        "'o que entreguei essa semana', 'o que foi reprogramado'."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "phone": {
                "type": "string",
                "description": "Número WhatsApp do remetente (apenas dígitos, sem +).",
            },
            "role": {
                "type": "string",
                "enum": ["assignee", "assigner"],
                "description": "assignee = tarefas que o usuário deve executar; assigner = tarefas que o usuário atribuiu.",
            },
            "status": {
                "type": "string",
                "enum": ["pendente", "atrasada", "concluida", "reprogramada"],
                "description": "Filtro de status (omita para todos os status).",
            },
            "assignee_name": {
                "type": "string",
                "description": "Filtrar por nome do destinatário (apenas quando role=assigner).",
            },
            "period": {
                "type": "string",
                "description": "Período: 'last_week', 'last_month', 'since:YYYY-MM-DD', 'range:A..B'.",
            },
            "order": {
                "type": "string",
                "enum": ["due", "completed"],
                "description": "Ordenação: 'due' por prazo (default), 'completed' por data de conclusão.",
            },
        },
        "required": ["phone", "role"],
    },
}

DETALHE = {
    "name": "taskme_detalhe",
    "description": (
        "Retorna detalhes completos de uma tarefa: título, prazo original e atual, "
        "histórico de reprogramações com justificativas, quem criou. "
        "Use quando o usuário perguntar 'por que a TM-XXXX foi reprogramada' ou "
        "pedir detalhes de uma tarefa específica."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "task_code": {
                "type": "string",
                "description": "Código da tarefa (ex: TM-1042).",
            },
            "phone": {
                "type": "string",
                "description": "Número WhatsApp do remetente para verificar autorização (apenas dígitos, sem +).",
            },
        },
        "required": ["task_code", "phone"],
    },
}

REPROGRAMAR = {
    "name": "taskme_reprogramar",
    "description": (
        "Reprograma o prazo de uma tarefa pendente. "
        "Use quando o assignante quiser mover o prazo de uma tarefa que ele atribuiu."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "task_code": {
                "type": "string",
                "description": "Código da tarefa (ex: TM-1042).",
            },
            "new_due_phrase": {
                "type": "string",
                "description": (
                    "Novo prazo exatamente como o usuário disse "
                    "(ex: 'próxima quarta', 'dia 30'). Repasse a frase crua."
                ),
            },
            "justification": {
                "type": "string",
                "description": "Motivo da reprogramação (resumido, máx 280 chars).",
            },
            "by": {
                "type": "string",
                "enum": ["assignante", "assignado"],
                "description": "Quem está reprogramando (geralmente 'assignante' neste contexto).",
            },
        },
        "required": ["task_code", "new_due_phrase", "justification", "by"],
    },
}

CONCLUIR = {
    "name": "taskme_concluir",
    "description": (
        "Marca uma tarefa como concluída pelo assignante (fora do fluxo de cobrança). "
        "Use quando o assignante informar diretamente que uma tarefa foi entregue."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "task_code": {
                "type": "string",
                "description": "Código da tarefa (ex: TM-1042).",
            },
            "note": {
                "type": "string",
                "description": "Nota opcional sobre a conclusão (resumido, máx 280 chars).",
            },
        },
        "required": ["task_code"],
    },
}

RESPONDER = {
    "name": "taskme_responder",
    "description": (
        "Registra a resposta do assignado a uma cobrança de prazo — fallback para ÁUDIO. "
        "Use SOMENTE quando receber mensagem de ÁUDIO de alguém com cobrança aberta "
        "(o Hermes já transcreveu o áudio). "
        "Para mensagens de TEXTO, o sistema já roteia automaticamente sem chamar este tool."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "phone": {
                "type": "string",
                "description": "Número WhatsApp do remetente (apenas dígitos, sem +).",
            },
            "outcome": {
                "type": "string",
                "enum": ["done", "reprogram"],
                "description": "done = concluiu a tarefa; reprogram = precisa de mais prazo.",
            },
            "task_code": {
                "type": "string",
                "description": "Código da tarefa (opcional — omita se não souber; o sistema resolve pelo telefone).",
            },
            "new_due_phrase": {
                "type": "string",
                "description": "Novo prazo como o assignado disse (necessário para outcome=reprogram). Repasse a frase crua.",
            },
            "justification": {
                "type": "string",
                "description": "Justificativa da reprogramação (resumida, máx 280 chars).",
            },
        },
        "required": ["phone", "outcome"],
    },
}
