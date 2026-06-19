"""Entrypoints dos cron jobs (modo `hermes cron --no-agent --script`).

Cada job consulta o banco e envia por-destinatário via `hermes send`. O stdout
(resumo curto) é entregue verbatim ao canal de admin pelo cron.

Uso: python -m taskme.dispatch <monday_digests|assigner_digests|due_charges>
"""
from __future__ import annotations

import sys

from .services import charges, digests


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    job = argv[0] if argv else ""
    if job == "monday_digests":
        r = digests.build_monday_digests()
        print(f"TaskMe: {len(r)} digest(s) de segunda enviados.")
    elif job == "assigner_digests":
        r = digests.build_assigner_digests()
        print(f"TaskMe: {len(r)} resumo(s) diário(s) enviados.")
    elif job == "due_charges":
        r = charges.build_due_charges()
        print(f"TaskMe: {len(r)} cobrança(s) processada(s).")
    else:
        print("uso: dispatch <monday_digests|assigner_digests|due_charges>")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
