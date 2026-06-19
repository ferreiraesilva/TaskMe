-- TaskMe — schema inicial. SQL idempotente: roda em qualquer Postgres limpo
-- (Supabase ou container) via psql. Não depende do MCP.

-- ---------- Enums (guardados) ----------
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'task_status') THEN
    CREATE TYPE task_status AS ENUM ('pendente', 'concluida');
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'event_type') THEN
    CREATE TYPE event_type AS ENUM (
      'criada', 'enviada', 'lembrete', 'cobranca', 'resposta',
      'reprogramada', 'concluida', 'contato_pedido', 'nota'
    );
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'event_actor') THEN
    CREATE TYPE event_actor AS ENUM ('assignante', 'assignado', 'sistema');
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'queue_kind') THEN
    CREATE TYPE queue_kind AS ENUM ('cobranca_vencimento');
  END IF;
END $$;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'queue_status') THEN
    CREATE TYPE queue_status AS ENUM ('pendente_envio', 'aguardando_resposta', 'respondida');
  END IF;
END $$;

-- ---------- Tabelas ----------
CREATE TABLE IF NOT EXISTS users (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  whatsapp_phone text NOT NULL UNIQUE,
  name           text,
  created_at     timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS contacts (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_user_id  uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name           text NOT NULL,
  whatsapp_phone text NOT NULL,
  created_at     timestamptz NOT NULL DEFAULT now(),
  UNIQUE (owner_user_id, whatsapp_phone)
);

CREATE SEQUENCE IF NOT EXISTS taskme_code_seq START 1000;

CREATE TABLE IF NOT EXISTS tasks (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code                text NOT NULL UNIQUE,
  assigner_user_id    uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  assignee_contact_id uuid NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
  title               text NOT NULL,
  description         text,
  original_due_date   date NOT NULL,
  current_due_date    date NOT NULL,
  status              task_status NOT NULL DEFAULT 'pendente',
  reprogram_count     int NOT NULL DEFAULT 0,
  created_at          timestamptz NOT NULL DEFAULT now(),
  completed_at        timestamptz,
  completion_note     text
);

CREATE TABLE IF NOT EXISTS task_events (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  task_id       uuid NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  type          event_type NOT NULL,
  actor         event_actor NOT NULL,
  summary       text,
  old_due_date  date,
  new_due_date  date,
  created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS interaction_queue (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  contact_phone text NOT NULL,
  task_id       uuid NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  kind          queue_kind NOT NULL DEFAULT 'cobranca_vencimento',
  status        queue_status NOT NULL DEFAULT 'pendente_envio',
  created_at    timestamptz NOT NULL DEFAULT now(),
  sent_at       timestamptz,
  answered_at   timestamptz
);

-- ---------- Índices ----------
CREATE INDEX IF NOT EXISTS idx_tasks_assigner ON tasks (assigner_user_id);
CREATE INDEX IF NOT EXISTS idx_tasks_assignee ON tasks (assignee_contact_id);
CREATE INDEX IF NOT EXISTS idx_tasks_due_status ON tasks (current_due_date, status);
CREATE INDEX IF NOT EXISTS idx_events_task ON task_events (task_id);
CREATE INDEX IF NOT EXISTS idx_queue_phone_status ON interaction_queue (contact_phone, status);

-- No máximo 1 cobrança "aguardando_resposta" por telefone (fila 1-por-vez).
CREATE UNIQUE INDEX IF NOT EXISTS uq_queue_one_open_per_phone
  ON interaction_queue (contact_phone)
  WHERE status = 'aguardando_resposta';
