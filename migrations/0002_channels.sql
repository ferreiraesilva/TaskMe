-- Endpoints multicanal associados à identidade canônica atual (telefone).
-- Aditivo: preserva todas as tabelas, dados e fluxos WhatsApp existentes.
CREATE TABLE IF NOT EXISTS taskme_channels (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  phone      text NOT NULL,
  platform   text NOT NULL CHECK (platform IN ('telegram', 'whatsapp')),
  address    text NOT NULL,
  enabled    boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (platform, address)
);

CREATE INDEX IF NOT EXISTS idx_taskme_channels_phone
  ON taskme_channels (phone, enabled);
