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

def _fake_task_row(status="pendente"):
    from datetime import date
    return {
        "id": "task-uuid",
        "code": "TM-1002",
        "title": "Enviar o contrato",
        "description": None,
        "current_due_date": date(2026, 7, 4),
        "status": status,
        "assignee_name": "Lívia",
        "assignee_phone": "5562988887777",
        "assigner_name": "Leonardo",
        "assigner_phone": "5562993119454",
    }


def test_resend_task_sem_canal_registra_nota(monkeypatch):
    from taskme.services import tasks

    events = []
    monkeypatch.setattr(tasks.db, "query_one", lambda *a, **k: _fake_task_row())
    monkeypatch.setattr(tasks.notify, "targets", lambda phone: [])
    monkeypatch.setattr(tasks.notify, "send", lambda phone, msg: False)

    class FakeCur:
        def __enter__(self): return self
        def __exit__(self, *a): return False
    monkeypatch.setattr(tasks.db, "transaction", lambda: FakeCur())
    monkeypatch.setattr(tasks, "add_event", lambda cur, tid, typ, actor, summary=None, **k: events.append((typ, actor)))

    res = tasks.resend_task("TM-1002", requester_phone="5562993119454")
    assert res["sent"] is False
    assert res["had_targets"] is False
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


def test_resend_task_entregue(monkeypatch):
    from taskme.services import tasks
    events = []
    monkeypatch.setattr(tasks.db, "query_one", lambda *a, **k: _fake_task_row())
    monkeypatch.setattr(tasks.notify, "targets", lambda phone: ["telegram:42"])
    monkeypatch.setattr(tasks.notify, "send", lambda phone, msg: True)

    class FakeCur:
        def __enter__(self): return self
        def __exit__(self, *a): return False
    monkeypatch.setattr(tasks.db, "transaction", lambda: FakeCur())
    monkeypatch.setattr(tasks, "add_event", lambda cur, tid, typ, actor, summary=None, **k: events.append((typ, actor)))

    res = tasks.resend_task("TM-1002", requester_phone="5562993119454")
    assert res["sent"] is True
    assert events == [("enviada", "sistema")]
