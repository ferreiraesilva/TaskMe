-- TaskMe 0004 - convites para primeiro contato no WhatsApp.
-- A lista geral de quem iniciou conversa e taskme_channels. Esta tabela guarda
-- apenas convites temporarios para contatos novos que chegam como @lid.

CREATE TABLE IF NOT EXISTS taskme_whatsapp_invites (
  token         text PRIMARY KEY,
  phone         text NOT NULL,
  owner_phone   text NOT NULL,
  created_at    timestamptz NOT NULL DEFAULT now(),
  expires_at    timestamptz NOT NULL,
  used_at       timestamptz,
  used_address  text
);

CREATE INDEX IF NOT EXISTS idx_taskme_whatsapp_invites_phone_active
  ON taskme_whatsapp_invites (phone, expires_at)
  WHERE used_at IS NULL;
