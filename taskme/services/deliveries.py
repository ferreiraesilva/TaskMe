"""Reservas persistentes que tornam retries de envio idempotentes."""
from __future__ import annotations

import hashlib

from .. import db
from ..util import summarize


def payload_hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def target_key(idempotency_key: str, target: str) -> str:
    suffix = hashlib.sha256(target.encode("utf-8")).hexdigest()[:16]
    return f"{idempotency_key}:{suffix}"


def begin(idempotency_key: str, target: str, text: str) -> str:
    """Retorna send, duplicate ou conflict.

    Uma reserva travada em ``sending`` pode ser retomada depois de cinco
    minutos. Isso cobre encerramento abrupto do processo sem liberar retries
    concorrentes.
    """
    key = str(idempotency_key or "").strip()
    digest = payload_hash(text)
    if not key:
        return "send"

    with db.transaction() as cur:
        cur.execute(
            """INSERT INTO taskme_outbound_deliveries
                 (idempotency_key, target, payload_sha256, status)
               VALUES (%s, %s, %s, 'sending')
               ON CONFLICT (idempotency_key) DO NOTHING
               RETURNING idempotency_key""",
            (key, target, digest),
        )
        if cur.fetchone():
            return "send"

        cur.execute(
            """SELECT target, payload_sha256, status
                 FROM taskme_outbound_deliveries
                WHERE idempotency_key=%s""",
            (key,),
        )
        existing = cur.fetchone()
        if not existing:
            return "conflict"
        if existing["target"] != target or existing["payload_sha256"] != digest:
            return "conflict"
        if existing["status"] == "sent":
            return "duplicate"

        cur.execute(
            """UPDATE taskme_outbound_deliveries
                  SET status='sending', attempts=attempts+1,
                      last_error=NULL, updated_at=now()
                WHERE idempotency_key=%s
                  AND (status='failed' OR
                       (status='sending' AND updated_at < now() - interval '5 minutes'))
                RETURNING idempotency_key""",
            (key,),
        )
        return "send" if cur.fetchone() else "duplicate"


def mark_sent(idempotency_key: str) -> None:
    with db.transaction() as cur:
        cur.execute(
            """UPDATE taskme_outbound_deliveries
                  SET status='sent', sent_at=now(), updated_at=now(), last_error=NULL
                WHERE idempotency_key=%s""",
            (idempotency_key,),
        )


def mark_failed(idempotency_key: str, error: str) -> None:
    with db.transaction() as cur:
        cur.execute(
            """UPDATE taskme_outbound_deliveries
                  SET status='failed', last_error=%s, updated_at=now()
                WHERE idempotency_key=%s""",
            (summarize(error, 500), idempotency_key),
        )
