-- TaskMe 0005 - idempotencia persistente para entregas externas.

CREATE TABLE IF NOT EXISTS taskme_outbound_deliveries (
  idempotency_key text PRIMARY KEY,
  target          text NOT NULL,
  payload_sha256  text NOT NULL,
  status          text NOT NULL CHECK (status IN ('sending', 'sent', 'failed')),
  attempts        integer NOT NULL DEFAULT 1,
  last_error      text,
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now(),
  sent_at         timestamptz
);

CREATE INDEX IF NOT EXISTS idx_taskme_outbound_deliveries_status_updated
  ON taskme_outbound_deliveries (status, updated_at);
