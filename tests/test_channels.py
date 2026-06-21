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
