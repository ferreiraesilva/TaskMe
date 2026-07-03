from contextlib import contextmanager
from urllib.parse import unquote

from taskme import invitations


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


def test_create_reuses_active_invite_and_builds_wa_link(monkeypatch):
    cur = FakeCursor([{"token": "abcdefghijklmnop"}])
    monkeypatch.setattr(invitations.config, "WHATSAPP_BOT_PHONE", "5562999999999")
    monkeypatch.setattr(invitations.db, "transaction", _transaction(cur))

    result = invitations.create("5562991111111", "5562992222222")

    assert result["ok"] is True
    assert result["url"].startswith("https://wa.me/5562999999999?text=")
    assert "TASKME abcdefghijklmnop" in unquote(result["url"])
    assert len(cur.calls) == 1


def test_create_fails_closed_without_bot_phone(monkeypatch):
    monkeypatch.setattr(invitations.config, "WHATSAPP_BOT_PHONE", "")
    assert invitations.create("5562991111111", "5562992222222") == {
        "error": "bot_phone_not_configured"
    }


def test_redeem_links_lid_and_consumes_token(monkeypatch):
    cur = FakeCursor([{"phone": "5562992222222"}])
    monkeypatch.setattr(invitations.db, "transaction", _transaction(cur))

    phone = invitations.redeem(
        "Ola! Codigo: TASKME abcdefghijklmnop", "123456789@lid"
    )

    assert phone == "5562992222222"
    assert len(cur.calls) == 3
    assert "INSERT INTO taskme_channels" in cur.calls[1][0]
    assert cur.calls[1][1] == ("5562992222222", "123456789@lid")
    assert "UPDATE taskme_whatsapp_invites" in cur.calls[2][0]


def test_redeem_ignores_normal_message_without_database(monkeypatch):
    called = []
    monkeypatch.setattr(
        invitations.db, "transaction", lambda: called.append(True)
    )
    assert invitations.redeem("bom dia", "123456789@lid") == ""
    assert called == []


def test_redeem_rejects_token_for_another_resolved_phone(monkeypatch):
    cur = FakeCursor([None])
    monkeypatch.setattr(invitations.db, "transaction", _transaction(cur))

    result = invitations.redeem(
        "Código: TASKME abcdefghijklmnop",
        "5562993333333@s.whatsapp.net",
        expected_phone="5562993333333",
    )

    assert result == ""
    assert cur.calls[0][1] == (
        "abcdefghijklmnop", "5562993333333", "5562993333333"
    )
