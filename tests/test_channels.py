from types import SimpleNamespace

from taskme import identity, notify


def test_telegram_test_resolve_e_vincula(monkeypatch):
    linked = []
    monkeypatch.setattr(identity.config, "MODE", "telegram_test")
    monkeypatch.setattr(identity.config, "TG_TEST_PHONE", "5562993119454")
    monkeypatch.setattr(identity.channels, "link", lambda *args: linked.append(args))

    assert identity.resolve("telegram", "1008988131") == "5562993119454"
    assert linked == [("5562993119454", "telegram", "1008988131")]


def test_whatsapp_continua_resolvendo(monkeypatch):
    monkeypatch.setattr(identity.channels, "link", lambda *args: None)
    assert identity.resolve("whatsapp", "5562993119454@s.whatsapp.net") == "5562993119454"


def test_notify_telegram_sem_whatsapp(monkeypatch):
    calls = []
    monkeypatch.setattr(notify.config, "HERMES_SEND_CMD", "hermes send")
    monkeypatch.setattr(notify.config, "NOTIFY_CHANNELS", ("telegram",))
    monkeypatch.setattr(
        notify.channels, "addresses",
        lambda phone, platforms: [{"platform": "telegram", "address": "1008988131"}],
    )
    monkeypatch.setattr(
        notify.subprocess, "run",
        lambda cmd, **kwargs: calls.append(cmd) or SimpleNamespace(returncode=0),
    )

    assert notify.send("5562993119454", "teste") is True
    assert calls == [["hermes", "send", "--to", "telegram:1008988131", "teste"]]


def test_notify_dual_channel(monkeypatch):
    monkeypatch.setattr(notify.config, "NOTIFY_CHANNELS", ("whatsapp", "telegram"))
    monkeypatch.setattr(notify.channels, "has_inbound", lambda phone, platform: True)
    monkeypatch.setattr(
        notify.channels, "addresses",
        lambda phone, platforms: [{"platform": "telegram", "address": "42"}],
    )
    assert notify.targets("5562993119454") == [
        "whatsapp:5562993119454@s.whatsapp.net", "telegram:42"
    ]


def test_hook_links_telegram_user_from_contact(monkeypatch):
    import importlib.util
    import os
    import sys
    
    import taskme as taskme_sub
    sys.modules["taskme.taskme"] = taskme_sub
    
    hook_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../hook.py'))
    spec = importlib.util.spec_from_file_location("taskme.hook", hook_path)
    hook = importlib.util.module_from_spec(spec)
    sys.modules["taskme.hook"] = hook
    spec.loader.exec_module(hook)
    
    linked_channels = []
    created_users = []
    
    monkeypatch.setattr(hook.channels, "link", lambda phone, platform, address: linked_channels.append((phone, platform, address)))
    monkeypatch.setattr(hook.contacts, "get_or_create_user", lambda phone, name: created_users.append((phone, name)))
    
    # Mock platform resolve to return "" (unlinked user)
    monkeypatch.setattr(hook, "resolve", lambda platform, user_id: "")
    
    # Event mock representing contact card sharing
    event = SimpleNamespace(
        source=SimpleNamespace(
            platform="telegram",
            user_id="12345"
        ),
        text="Contato compartilhado: Leonardo | 5562993119454"
    )
    
    res = hook.handle_gateway(event)
    assert res is None  # Should fall through to LLM
    assert linked_channels == [("5562993119454", "telegram", "12345")]
    assert created_users == [("5562993119454", "Leonardo")]


def test_hook_links_telegram_user_from_raw_phone(monkeypatch):
    import importlib.util
    import os
    import sys
    
    import taskme as taskme_sub
    sys.modules["taskme.taskme"] = taskme_sub
    
    hook_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../hook.py'))
    spec = importlib.util.spec_from_file_location("taskme.hook", hook_path)
    hook = importlib.util.module_from_spec(spec)
    sys.modules["taskme.hook"] = hook
    spec.loader.exec_module(hook)
    
    linked_channels = []
    created_users = []
    
    monkeypatch.setattr(hook.channels, "link", lambda phone, platform, address: linked_channels.append((phone, platform, address)))
    monkeypatch.setattr(hook.contacts, "get_or_create_user", lambda phone, name: created_users.append((phone, name)))
    
    # Mock platform resolve to return "" (unlinked user)
    monkeypatch.setattr(hook, "resolve", lambda platform, user_id: "")
    
    # Event mock representing raw phone number
    event = SimpleNamespace(
        source=SimpleNamespace(
            platform="telegram",
            user_id="12345"
        ),
        text="5562993119454"
    )
    
    res = hook.handle_gateway(event)
    assert res is None  # Should fall through to LLM
    assert linked_channels == [("5562993119454", "telegram", "12345")]
    assert created_users == [("5562993119454", "Telegram User")]


def test_dynamic_inject_phone_context(monkeypatch):
    import importlib.util
    import os
    import sys
    
    import taskme as taskme_sub
    sys.modules["taskme.taskme"] = taskme_sub
    
    init_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../__init__.py'))
    spec = importlib.util.spec_from_file_location("taskme", init_path)
    taskme_root = importlib.util.module_from_spec(spec)
    sys.modules["taskme"] = taskme_root
    spec.loader.exec_module(taskme_root)
    
    taskme_root._session_metadata["sess_1"] = ("telegram", "12345")
    
    # Mock resolve to return empty first, then phone number
    phone_res = ""
    def mock_resolve(platform, user_id):
        return phone_res
    
    monkeypatch.setattr(taskme_sub.identity, "resolve", mock_resolve)
    
    # First call: not linked yet
    ctx1 = taskme_root._inject_phone_context("sess_1")
    assert ctx1 is None
    
    # Link the user now
    phone_res = "5562993119454"
    
    # Second call: linked mid-session
    ctx2 = taskme_root._inject_phone_context("sess_1")
    assert ctx2 is not None
    assert "5562993119454" in ctx2["context"]
    
    # Restore original sys.modules["taskme"] for other tests
    sys.modules["taskme"] = taskme_sub


# ---------- Reenvio + honestidade de entrega ----------

def _fake_task_row(status="pendente", channel="whatsapp"):
    from datetime import date
    return {
        "id": "task-uuid",
        "code": "TM-1002",
        "title": "Enviar o contrato",
        "description": None,
        "current_due_date": date(2026, 7, 4),
        "status": status,
        "channel": channel,
        "assignee_name": "Lívia",
        "assignee_phone": "5562988887777",
        "assigner_name": "Leonardo",
        "assigner_phone": "5562993119454",
    }


def test_resend_task_sem_canal_registra_nota(monkeypatch):
    from taskme.services import tasks

    events = []
    monkeypatch.setattr(tasks.db, "query_one", lambda *a, **k: _fake_task_row())
    monkeypatch.setattr(tasks.channels, "has_inbound", lambda phone, platform: True)
    monkeypatch.setattr(tasks.notify, "channel_targets", lambda phone, channel: [])
    monkeypatch.setattr(tasks.notify, "send_on", lambda phone, channel, msg, **kwargs: False)

    class FakeCur:
        def __enter__(self): return self
        def __exit__(self, *a): return False
    monkeypatch.setattr(tasks.db, "transaction", lambda: FakeCur())
    monkeypatch.setattr(tasks, "add_event", lambda cur, tid, typ, actor, summary=None, **k: events.append((typ, actor)))

    res = tasks.resend_task("TM-1002", requester_phone="5562993119454")
    assert res["sent"] is False
    assert res["had_targets"] is False
    assert res["channel"] == "whatsapp"
    assert events == [("nota", "sistema")]


def test_resend_task_autoriza_so_criador(monkeypatch):
    from taskme.services import tasks
    monkeypatch.setattr(tasks.db, "query_one", lambda *a, **k: _fake_task_row())
    res = tasks.resend_task("TM-1002", requester_phone="5562000000000")
    assert res["error"] == "not_authorized"


def test_resend_task_concluida(monkeypatch):
    from taskme.services import tasks
    monkeypatch.setattr(tasks.db, "query_one", lambda *a, **k: _fake_task_row(status="concluida"))
    res = tasks.resend_task("TM-1002", requester_phone="5562993119454")
    assert res["error"] == "task_completed"


def test_resend_task_nao_encontrada(monkeypatch):
    from taskme.services import tasks
    monkeypatch.setattr(tasks.db, "query_one", lambda *a, **k: None)
    res = tasks.resend_task("TM-9999")
    assert res["error"] == "task_not_found"


def test_commit_task_bloqueia_whatsapp_sem_primeiro_contato(monkeypatch):
    from taskme.services import tasks
    writes = []
    monkeypatch.setattr(
        tasks.contacts, "get_contact",
        lambda contact_id: {
            "id": contact_id,
            "name": "Lívia",
            "whatsapp_phone": "5562988887777",
        },
    )
    monkeypatch.setattr(tasks.channels, "has_inbound", lambda phone, platform: False)
    monkeypatch.setattr(
        tasks.contacts, "get_or_create_user", lambda *a, **k: writes.append("user")
    )
    monkeypatch.setattr(tasks.db, "transaction", lambda: writes.append("transaction"))

    result = tasks.commit_task(
        "5562993119454", "contact-1", "Envie o contrato", None,
        "2026-07-10", channel="whatsapp",
    )

    assert result == {
        "error": "recipient_not_started",
        "assignee_name": "Lívia",
        "assignee_phone": "5562988887777",
    }
    assert writes == []


def test_resend_task_entregue_no_canal_da_tarefa(monkeypatch):
    from taskme.services import tasks
    events = []
    sends = []
    monkeypatch.setattr(tasks.db, "query_one", lambda *a, **k: _fake_task_row(channel="telegram"))
    monkeypatch.setattr(tasks.notify, "channel_targets", lambda phone, channel: ["telegram:42"])
    monkeypatch.setattr(tasks.notify, "send_on", lambda phone, channel, msg, **kwargs: sends.append((phone, channel)) or True)

    class FakeCur:
        def __enter__(self): return self
        def __exit__(self, *a): return False
    monkeypatch.setattr(tasks.db, "transaction", lambda: FakeCur())
    monkeypatch.setattr(tasks, "add_event", lambda cur, tid, typ, actor, summary=None, **k: events.append((typ, actor)))

    res = tasks.resend_task("TM-1002", requester_phone="5562993119454")
    assert res["sent"] is True
    assert res["channel"] == "telegram"
    # entregou no canal da tarefa (telegram), não em broadcast
    assert sends == [("5562988887777", "telegram")]
    assert events == [("enviada", "sistema")]


# ---------- Escopo por canal ----------

def test_channel_targets_isola_canal(monkeypatch):
    from taskme import notify
    monkeypatch.setattr(notify.channels, "has_inbound", lambda phone, platform: True)
    monkeypatch.setattr(notify.channels, "addresses",
                        lambda phone, platforms: [{"platform": "telegram", "address": "42"}])
    assert notify.channel_targets("5562993119454", "whatsapp") == [
        "whatsapp:5562993119454@s.whatsapp.net"]
    assert notify.channel_targets("5562993119454", "telegram") == ["telegram:42"]
    assert notify.channel_targets("5562993119454", "sms") == []


def test_send_on_entrega_so_no_canal(monkeypatch):
    from types import SimpleNamespace
    from taskme import notify
    calls = []
    monkeypatch.setattr(notify.config, "HERMES_SEND_CMD", "hermes send")
    monkeypatch.setattr(notify.channels, "has_inbound", lambda phone, platform: True)
    monkeypatch.setattr(notify.channels, "addresses",
                        lambda phone, platforms: [{"platform": "telegram", "address": "42"}])
    monkeypatch.setattr(notify.subprocess, "run",
                        lambda cmd, **k: calls.append(cmd) or SimpleNamespace(returncode=0))
    assert notify.send_on("5562993119454", "whatsapp", "oi") is True
    # só o alvo whatsapp foi acionado, telegram não
    assert calls == [["hermes", "send", "--to", "whatsapp:5562993119454@s.whatsapp.net", "oi"]]


def test_whatsapp_sem_inbound_nao_gera_alvo(monkeypatch):
    from taskme import notify
    monkeypatch.setattr(notify.channels, "has_inbound", lambda phone, platform: False)
    assert notify.channel_targets("5562993119454", "whatsapp") == []


def test_query_tasks_filtra_por_canal(monkeypatch):
    from taskme.services import queries
    captured = {}
    monkeypatch.setattr(queries, "normalize_phone", lambda p: p)
    monkeypatch.setattr(queries.config, "today", lambda: __import__("datetime").date(2026, 7, 2))
    def fake_query_all(sql, params):
        captured["sql"] = sql
        captured["params"] = params
        return []
    monkeypatch.setattr(queries.db, "query_all", fake_query_all)
    queries.query_tasks("5562993119454", "assignee", channel="whatsapp")
    assert "t.channel = %s" in captured["sql"]
    assert "whatsapp" in captured["params"]


def test_channel_from_platform():
    from taskme.identity import channel_from_platform
    assert channel_from_platform("telegram") == "telegram"
    assert channel_from_platform("TELEGRAM") == "telegram"
    assert channel_from_platform("whatsapp") == "whatsapp"
    assert channel_from_platform("") == "whatsapp"
    assert channel_from_platform(None) == "whatsapp"


def test_charges_open_charge_escopa_canal(monkeypatch):
    from taskme.services import charges
    captured = {}
    def fake_query_one(sql, params):
        captured["sql"] = sql
        captured["params"] = params
        return None
    monkeypatch.setattr(charges.db, "query_one", fake_query_one)
    charges.has_open_charge("5562993119454", "telegram")
    assert "q.channel = %s" in captured["sql"]
    assert "telegram" in captured["params"]


# ---------- BUG-0001: remarcação sem data pede a nova data ----------

class _FakeCur:
    def __enter__(self): return self
    def __exit__(self, *a): return False


def _open_charge_row(channel="whatsapp"):
    return {"queue_id": "q1", "task_id": "t1", "code": "TM-1002", "title": "x", "channel": channel}


def test_request_new_due_pergunta_uma_vez(monkeypatch):
    from taskme.services import charges
    sends, events = [], []
    def fake_query_one(sql, params):
        if "interaction_queue" in sql:
            return _open_charge_row()
        if "task_events" in sql:
            return None  # nenhum evento anterior
        return None
    monkeypatch.setattr(charges.db, "query_one", fake_query_one)
    monkeypatch.setattr(charges.notify, "send_on",
                        lambda phone, channel, msg, **kwargs: sends.append((phone, channel)) or True)
    monkeypatch.setattr(charges.db, "transaction", lambda: _FakeCur())
    monkeypatch.setattr(charges, "add_event",
                        lambda cur, tid, typ, actor, summary=None, **k: events.append((typ, summary)))

    assert charges.request_new_due("556299299266", "whatsapp") == "asked"
    assert sends == [("556299299266", "whatsapp")]
    assert events == [("nota", charges._AWAIT_DUE_MARK)]


def test_request_new_due_nao_repete(monkeypatch):
    from taskme.services import charges
    called = []
    def fake_query_one(sql, params):
        if "interaction_queue" in sql:
            return _open_charge_row()
        if "task_events" in sql:
            return {"type": "nota", "summary": charges._AWAIT_DUE_MARK}
        return None
    monkeypatch.setattr(charges.db, "query_one", fake_query_one)
    monkeypatch.setattr(charges.notify, "send_on", lambda *a: called.append(a) or True)

    assert charges.request_new_due("556299299266", "whatsapp") == "defer"
    assert called == []  # não pergunta de novo → deixa o agente conduzir


def test_request_new_due_sem_cobranca(monkeypatch):
    from taskme.services import charges
    monkeypatch.setattr(charges.db, "query_one", lambda sql, params: None)
    assert charges.request_new_due("556299299266", "whatsapp") == "defer"


# ---------- BUG-0002: identidade WhatsApp por LID ----------

def test_resolve_whatsapp_lid_usa_channel_link(monkeypatch):
    from taskme import identity
    monkeypatch.setattr(
        identity.channels, "phone_for",
        lambda platform, addr: "5562988887777" if addr == "236657060135090@lid" else "",
    )
    # LID conhecido -> telefone vinculado; LID desconhecido -> "" (dispara onboarding)
    assert identity.resolve("whatsapp", "236657060135090@lid") == "5562988887777"
    assert identity.resolve("whatsapp", "999999@lid") == ""


def test_resolve_whatsapp_lid_nao_vira_telefone(monkeypatch):
    from taskme import identity
    # Garante que os dígitos do LID NÃO são usados como telefone
    monkeypatch.setattr(identity.channels, "phone_for", lambda platform, addr: "")
    linked = []
    monkeypatch.setattr(identity.channels, "link", lambda *a: linked.append(a))
    assert identity.resolve("whatsapp", "236657060135090@lid") == ""
    assert linked == []  # não vincula LID como se fosse telefone


def test_resolve_whatsapp_phone_jid_inalterado(monkeypatch):
    from taskme import identity
    monkeypatch.setattr(identity.channels, "link", lambda *a: None)
    # JID de telefone normal continua resolvendo pelo número (comportamento atual)
    assert identity.resolve("whatsapp", "5562988887777@s.whatsapp.net") == "5562988887777"
