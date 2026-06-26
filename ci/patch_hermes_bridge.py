"""
Patch bridge.js to handle WhatsApp contact vCard messages.

When a user shares a contact from WhatsApp, Baileys delivers a contactMessage
(not a text message). Without this patch, bridge.js silently drops the message.
After the patch, contact cards are converted to text:
    "Contato compartilhado: Larissa Silva | 5562987654321"
...so the Hermes agent can read them and call taskme_add_contato.

Run once after installing Hermes or after a Hermes update that overwrites bridge.js:
    python3 ci/patch_hermes_bridge.py [--bridge PATH]

Default bridge path: ~/.hermes/hermes-agent/scripts/whatsapp-bridge/bridge.js
After patching, restart the WhatsApp bridge:
    kill $(pgrep -f 'bridge.js') # it auto-restarts via the Hermes gateway supervisor
"""
import argparse
import os
import subprocess
import sys

DEFAULT_BRIDGE = os.path.expanduser(
    '~/.hermes/hermes-agent/scripts/whatsapp-bridge/bridge.js'
)

HELPER = r"""
function _parseVCardToText(vcard, displayName) {
  var waidMatch = vcard.match(/waid=(\d+)/);
  var fnMatch   = vcard.match(/^FN:(.+)/m);
  var name  = (fnMatch ? fnMatch[1].trim() : displayName) || 'Contato';
  var phone = waidMatch ? waidMatch[1] : '';
  if (!phone) {
    var telMatch = vcard.match(/^TEL[^;:]*:([^\r\n]+)/m);
    if (telMatch) { phone = telMatch[1].replace(/\D/g, ''); }
  }
  if (phone) { return 'Contato compartilhado: ' + name + ' | ' + phone; }
  return 'Contato compartilhado: ' + name;
}
"""

HANDLER_OLD = '      }\n\n      // For media without caption, use a placeholder'

HANDLER_NEW = (
    '      } else if (messageContent.contactMessage) {\n'
    '        // Single contact vCard — convert to text so the agent can read it\n'
    "        var _vcard = messageContent.contactMessage.vcard || '';\n"
    "        var _name  = messageContent.contactMessage.displayName || '';\n"
    '        body = _parseVCardToText(_vcard, _name);\n'
    '      } else if (messageContent.contactsArrayMessage) {\n'
    '        // Multiple contacts — join as text\n'
    "        var _contacts = messageContent.contactsArrayMessage.contacts || [];\n"
    "        body = _contacts.map(function(c) { return _parseVCardToText(c.vcard || '', c.displayName || ''); }).join('\\n');\n"
    '      }\n'
    '\n'
    '      // For media without caption, use a placeholder'
)


def patch(bridge_path):
    with open(bridge_path, 'r', encoding='utf-8') as f:
        src = f.read()

    if '_parseVCardToText' in src:
        print(f'[patch_hermes_bridge] Already patched: {bridge_path}')
        return False

    if 'sock.ev.on(' not in src:
        print('[patch_hermes_bridge] ERROR: anchor "sock.ev.on(" not found — wrong file?')
        sys.exit(1)

    if HANDLER_OLD not in src:
        print('[patch_hermes_bridge] ERROR: media-placeholder anchor not found')
        print('  (Hermes may have updated bridge.js — review the patch manually)')
        sys.exit(1)

    idx = src.index('sock.ev.on(')
    src = src[:idx] + HELPER + '\n' + src[idx:]
    src = src.replace(HANDLER_OLD, HANDLER_NEW, 1)

    with open(bridge_path, 'w', encoding='utf-8') as f:
        f.write(src)

    print(f'[patch_hermes_bridge] Patched: {bridge_path}')
    return True


def verify_syntax(bridge_path):
    node = os.path.expanduser('~/.hermes/node/bin/node')
    if not os.path.exists(node):
        node = 'node'
    try:
        result = subprocess.run(
            [node, '--check', bridge_path],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print('[patch_hermes_bridge] Syntax OK')
        else:
            print('[patch_hermes_bridge] SYNTAX ERROR:')
            print(result.stderr)
            sys.exit(1)
    except FileNotFoundError:
        print('[patch_hermes_bridge] Node not found on host, skipping syntax check.')


def restart_bridge():
    result = subprocess.run(
        ['pkill', '-f', 'whatsapp-bridge/bridge.js'],
        capture_output=True
    )
    if result.returncode == 0:
        print('[patch_hermes_bridge] Bridge process killed — will auto-restart')
    else:
        print('[patch_hermes_bridge] No bridge process found (start it manually)')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bridge', default=DEFAULT_BRIDGE,
                        help='Path to bridge.js (default: %(default)s)')
    parser.add_argument('--no-restart', action='store_true',
                        help='Skip killing the bridge process after patching')
    args = parser.parse_args()

    changed = patch(args.bridge)
    verify_syntax(args.bridge)
    if changed and not args.no_restart:
        restart_bridge()
