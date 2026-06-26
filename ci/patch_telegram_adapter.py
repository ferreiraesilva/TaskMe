"""
Patch adapter.py to handle Telegram contact shared messages.

When a user shares a contact from Telegram, python-telegram-bot delivers a contact message
which is ignored by default. This patch converts shared contact messages to text:
    "Contato compartilhado: Nome | Telefone"
...so the Hermes agent can read them and call taskme_add_contato.

Run during deployment:
    python3 ci/patch_telegram_adapter.py --adapter PATH
"""
import argparse
import os
import sys

DEFAULT_ADAPTER = os.path.expanduser(
    '~/.hermes/hermes-agent/plugins/platforms/telegram/adapter.py'
)

HANDLER_OLD = '''            self._app.add_handler(TelegramMessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self._handle_text_message
            ))'''

HANDLER_NEW = '''            self._app.add_handler(TelegramMessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self._handle_text_message
            ))
            self._app.add_handler(TelegramMessageHandler(
                filters.CONTACT,
                self._handle_contact_message
            ))'''

METHOD_OLD = '''        event = self._build_message_event(msg, MessageType.LOCATION, update_id=update.update_id)
        event.text = "\\n".join(parts)
        event = self._apply_telegram_group_observe_attribution(event)
        await self.handle_message(event)

    # ------------------------------------------------------------------
    # Text message aggregation (handles Telegram client-side splits)
    # ------------------------------------------------------------------'''

METHOD_NEW = '''        event = self._build_message_event(msg, MessageType.LOCATION, update_id=update.update_id)
        event.text = "\\n".join(parts)
        event = self._apply_telegram_group_observe_attribution(event)
        await self.handle_message(event)

    async def _handle_contact_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle incoming contact shared messages by converting them to text."""
        msg = self._effective_update_message(update)
        if not msg or not msg.contact:
            return
        if not self._should_process_message(msg):
            return
        await self._ensure_forum_commands(update.message)

        event = self._build_message_event(msg, MessageType.TEXT, update_id=update.update_id)
        
        name = (msg.contact.first_name or "").strip()
        if msg.contact.last_name:
            name += " " + msg.contact.last_name.strip()
        phone = (msg.contact.phone_number or "").strip().replace("+", "")
        
        event.text = f"Contato compartilhado: {name} | {phone}"
        
        await self._cache_replied_media(msg, event)
        event = self._apply_telegram_group_observe_attribution(event)
        self._enqueue_text_event(event)

    # ------------------------------------------------------------------
    # Text message aggregation (handles Telegram client-side splits)
    # ------------------------------------------------------------------'''


def patch(adapter_path):
    with open(adapter_path, 'r', encoding='utf-8') as f:
        src = f.read()

    if '_handle_contact_message' in src:
        print(f'[patch_telegram_adapter] Already patched: {adapter_path}')
        return False

    if HANDLER_OLD not in src:
        print('[patch_telegram_adapter] ERROR: TEXT handler anchor not found')
        sys.exit(1)

    if METHOD_OLD not in src:
        print('[patch_telegram_adapter] ERROR: LOCATION handler end anchor not found')
        sys.exit(1)

    src = src.replace(HANDLER_OLD, HANDLER_NEW, 1)
    src = src.replace(METHOD_OLD, METHOD_NEW, 1)

    with open(adapter_path, 'w', encoding='utf-8') as f:
        f.write(src)

    print(f'[patch_telegram_adapter] Patched: {adapter_path}')
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adapter', default=DEFAULT_ADAPTER,
                        help='Path to adapter.py (default: %(default)s)')
    args = parser.parse_args()

    patch(args.adapter)
