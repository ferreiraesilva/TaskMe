from contextlib import contextmanager

from types import SimpleNamespace

from taskme import notify
from taskme.services import deliveries


class FakeCursor:
    def __init__(self, rows):
        self.rows = iter(rows)
        self.calls = []

    def execute(self, sql, params):
        self.calls.append((sql, params))

    def fetchone(self):
        return next(self.rows)


def _transaction(cursor):
    @contextmanager
    def fake_transaction():
        yield cursor
    return fake_transaction


def test_begin_claims_new_delivery(monkeypatch):
    cur = FakeCursor([{"idempotency_key": "task:1"}])
    monkeypatch.setattr(deliveries.db, "transaction", _transaction(cur))
    assert deliveries.begin("task:1", "whatsapp:1", "mensagem") == "send"
    assert len(cur.calls) == 1


def test_begin_suppresses_already_sent_delivery(monkeypatch):
    digest = deliveries.payload_hash("mensagem")
    cur = FakeCursor([
        None,
        {"target": "whatsapp:1", "payload_sha256": digest, "status": "sent"},
    ])
    monkeypatch.setattr(deliveries.db, "transaction", _transaction(cur))
    assert deliveries.begin("task:1", "whatsapp:1", "mensagem") == "duplicate"


def test_begin_rejects_same_key_with_different_payload(monkeypatch):
    cur = FakeCursor([
        None,
        {
            "target": "whatsapp:1",
            "payload_sha256": deliveries.payload_hash("outra"),
            "status": "failed",
        },
    ])
    monkeypatch.setattr(deliveries.db, "transaction", _transaction(cur))
    assert deliveries.begin("task:1", "whatsapp:1", "mensagem") == "conflict"


def test_failed_delivery_can_be_claimed_for_retry(monkeypatch):
    digest = deliveries.payload_hash("mensagem")
    cur = FakeCursor([
        None,
        {"target": "whatsapp:1", "payload_sha256": digest, "status": "failed"},
        {"idempotency_key": "task:1"},
    ])
    monkeypatch.setattr(deliveries.db, "transaction", _transaction(cur))
    assert deliveries.begin("task:1", "whatsapp:1", "mensagem") == "send"
    assert "attempts=attempts+1" in cur.calls[2][0]


def test_target_key_is_stable_and_scoped_by_target():
    one = deliveries.target_key("task:1", "whatsapp:1")
    assert one == deliveries.target_key("task:1", "whatsapp:1")
    assert one != deliveries.target_key("task:1", "telegram:1")


def test_notify_suppresses_duplicate_without_running_command(monkeypatch):
    calls = []
    monkeypatch.setattr(notify.config, "HERMES_SEND_CMD", "hermes send")
    monkeypatch.setattr(notify.deliveries, "begin", lambda *args: "duplicate")
    monkeypatch.setattr(
        notify.subprocess, "run", lambda *args, **kwargs: calls.append(args)
    )

    assert notify._deliver(
        ["whatsapp:5562992222222@s.whatsapp.net"], "mensagem",
        idempotency_key="task:1:assignment",
    ) is True
    assert calls == []


def test_notify_marks_successful_delivery(monkeypatch):
    marked = []
    monkeypatch.setattr(notify.config, "HERMES_SEND_CMD", "hermes send")
    monkeypatch.setattr(notify.deliveries, "begin", lambda *args: "send")
    monkeypatch.setattr(
        notify.deliveries, "mark_sent", lambda key: marked.append(key)
    )
    monkeypatch.setattr(
        notify.subprocess, "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""),
    )

    assert notify._deliver(
        ["whatsapp:5562992222222@s.whatsapp.net"], "mensagem",
        idempotency_key="task:1:assignment",
    ) is True
    assert marked == [notify.deliveries.target_key(
        "task:1:assignment", "whatsapp:5562992222222@s.whatsapp.net"
    )]
