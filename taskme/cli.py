"""CLI determinístico do TaskMe.

Cada subcomando imprime JSON em stdout. É usado para testes manuais e pode ser
chamado pelo plugin/cron; a lógica vive em `taskme.services`.

Ex.: python -m taskme.cli resolve_contact --owner 5562... --name "João"
"""
from __future__ import annotations

import argparse
import json
import sys

from .services import charges, contacts, queries, reprogram, tasks


def _out(obj) -> None:
    print(json.dumps(obj, default=str, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="taskme")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("resolve_contact")
    s.add_argument("--owner", required=True)
    s.add_argument("--name", required=True)

    s = sub.add_parser("add_contact")
    s.add_argument("--owner", required=True)
    s.add_argument("--name", required=True)
    s.add_argument("--phone", required=True)

    s = sub.add_parser("propose_task")
    s.add_argument("--owner", required=True)
    s.add_argument("--assignee_contact_id", required=True)
    s.add_argument("--title", required=True)
    s.add_argument("--description", default=None)
    s.add_argument("--due", default=None)
    s.add_argument("--due-phrase", dest="due_phrase", default=None)

    s = sub.add_parser("commit_task")
    s.add_argument("--owner", required=True)
    s.add_argument("--owner-name", dest="owner_name", default=None)
    s.add_argument("--assignee_contact_id", required=True)
    s.add_argument("--title", required=True)
    s.add_argument("--description", default=None)
    s.add_argument("--due", required=True)

    s = sub.add_parser("list_pending")
    s.add_argument("--phone", required=True)
    s.add_argument("--role", choices=["assigner", "assignee"], required=True)

    s = sub.add_parser("reprogram")
    s.add_argument("--task_code", required=True)
    s.add_argument("--new_due", required=True)
    s.add_argument("--justification", default=None)
    s.add_argument("--by", choices=["assignante", "assignado"], default="assignado")

    s = sub.add_parser("complete_task")
    s.add_argument("--task_code", required=True)
    s.add_argument("--note", default=None)

    s = sub.add_parser("handle_reply")
    s.add_argument("--phone", required=True)
    s.add_argument("--outcome", choices=["done", "reprogram"], required=True)
    s.add_argument("--task_code", default=None)
    s.add_argument("--new_due", default=None)
    s.add_argument("--justification", default=None)
    s.add_argument("--note", default=None)

    s = sub.add_parser("query_tasks")
    s.add_argument("--phone", required=True)
    s.add_argument("--role", choices=["assigner", "assignee"], required=True)
    s.add_argument("--status", choices=["pendente", "atrasada", "concluida", "reprogramada"], default=None)
    s.add_argument("--assignee_name", default=None)
    s.add_argument("--period", default=None)
    s.add_argument("--order", choices=["due", "completed"], default=None)

    s = sub.add_parser("task_detail")
    s.add_argument("--task_code", required=True)
    s.add_argument("--phone", default=None)

    return p


def run(args: argparse.Namespace):
    c = args.cmd
    if c == "resolve_contact":
        return contacts.resolve_contact(args.owner, args.name)
    if c == "add_contact":
        return contacts.add_contact(args.owner, args.name, args.phone)
    if c == "propose_task":
        return tasks.propose_task(args.owner, args.assignee_contact_id, args.title,
                                  args.description, due=args.due, due_phrase=args.due_phrase)
    if c == "commit_task":
        return tasks.commit_task(args.owner, args.assignee_contact_id, args.title,
                                 args.description, args.due, owner_name=args.owner_name)
    if c == "list_pending":
        return tasks.list_pending(args.phone, args.role)
    if c == "reprogram":
        return reprogram.reprogram(args.task_code, args.new_due, args.justification, by=args.by)
    if c == "complete_task":
        return tasks.complete_task(args.task_code, args.note)
    if c == "handle_reply":
        return charges.handle_reply(args.phone, args.outcome, task_code=args.task_code,
                                    new_due=args.new_due, justification=args.justification, note=args.note)
    if c == "query_tasks":
        return queries.query_tasks(args.phone, args.role, status=args.status,
                                   assignee_name=args.assignee_name, period=args.period, order=args.order)
    if c == "task_detail":
        return queries.task_detail(args.task_code, args.phone)
    return {"error": "unknown_command"}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv if argv is not None else sys.argv[1:])
    try:
        _out(run(args))
        return 0
    except Exception as e:  # erro estruturado para o chamador
        _out({"error": "exception", "detail": str(e)})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
