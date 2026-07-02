-- TaskMe 0003 — canal de comunicação por tarefa (escopo por meio).
-- O canal (whatsapp|telegram) é a plataforma que o assignante usou para criar
-- a tarefa; passa a filtrar entrega, consultas, cobranças e digests.
-- SQL idempotente: roda em qualquer estado via psql.

-- ---------- tasks.channel ----------
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS channel text;
-- Backfill: todo o histórico desta instância foi criado via WhatsApp.
UPDATE tasks SET channel = 'whatsapp' WHERE channel IS NULL;
ALTER TABLE tasks ALTER COLUMN channel SET NOT NULL;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'tasks_channel_chk') THEN
    ALTER TABLE tasks ADD CONSTRAINT tasks_channel_chk
      CHECK (channel IN ('whatsapp', 'telegram'));
  END IF;
END $$;

-- ---------- interaction_queue.channel ----------
ALTER TABLE interaction_queue ADD COLUMN IF NOT EXISTS channel text;
UPDATE interaction_queue q SET channel = t.channel
  FROM tasks t WHERE t.id = q.task_id AND q.channel IS NULL;
-- Linha órfã remanescente (não deveria existir) assume whatsapp.
UPDATE interaction_queue SET channel = 'whatsapp' WHERE channel IS NULL;
ALTER TABLE interaction_queue ALTER COLUMN channel SET NOT NULL;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'interaction_queue_channel_chk') THEN
    ALTER TABLE interaction_queue ADD CONSTRAINT interaction_queue_channel_chk
      CHECK (channel IN ('whatsapp', 'telegram'));
  END IF;
END $$;

-- Cobrança 1-pergunta-por-vez agora é por (telefone, canal): a mesma pessoa
-- pode ter uma cobrança aberta no WhatsApp e outra no Telegram.
DROP INDEX IF EXISTS uq_queue_one_open_per_phone;
CREATE UNIQUE INDEX IF NOT EXISTS uq_queue_one_open_per_phone_channel
  ON interaction_queue (contact_phone, channel)
  WHERE status = 'aguardando_resposta';

CREATE INDEX IF NOT EXISTS idx_tasks_channel ON tasks (channel);
