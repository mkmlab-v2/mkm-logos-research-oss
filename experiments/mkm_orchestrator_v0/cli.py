from __future__ import annotations

import argparse
import json
from pathlib import Path

from .ledger import EventLedger
from .status import StatusBoard


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mkm-orchestrator-v0")
    sub = parser.add_subparsers(dest="command", required=True)

    verify = sub.add_parser("verify-ledger")
    verify.add_argument("--ledger", required=True)

    status = sub.add_parser("status")
    status.add_argument("--ledger", required=True)
    status.add_argument("--export")

    events = sub.add_parser("task-events")
    events.add_argument("--ledger", required=True)
    events.add_argument("--task", required=True)

    args = parser.parse_args(argv)
    ledger = EventLedger(Path(args.ledger))

    if args.command == "verify-ledger":
        payload = ledger.verify_chain()
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if payload["valid"] else 2

    if args.command == "status":
        board = StatusBoard(ledger)
        payload = board.build()
        if args.export:
            board.export(args.export)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if payload["ledger"]["integrity"]["valid"] else 2

    if args.command == "task-events":
        print(json.dumps(
            ledger.events(task_id=args.task),
            ensure_ascii=False,
            indent=2,
        ))
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
