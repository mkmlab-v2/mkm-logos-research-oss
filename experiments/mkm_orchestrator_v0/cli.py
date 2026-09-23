from __future__ import annotations

import argparse
import json
from pathlib import Path

from .ledger import EventLedger
from .measurement import MeasurementRecorder
from .shared_status import SharedStatusPublisher
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

    shared_publish = sub.add_parser("shared-publish")
    shared_publish.add_argument("--ledger", required=True)
    shared_publish.add_argument("--directory", required=True)

    shared_verify = sub.add_parser("shared-verify")
    shared_verify.add_argument("--ledger", required=True)
    shared_verify.add_argument("--directory", required=True)

    dogfood_summary = sub.add_parser("dogfood-summary")
    dogfood_summary.add_argument("--ledger", required=True)

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

    if args.command == "shared-publish":
        payload = SharedStatusPublisher(ledger).publish(args.directory)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if args.command == "shared-verify":
        payload = SharedStatusPublisher(ledger).verify(args.directory)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if payload.get("state") in {"CURRENT", "STALE"} else 2

    if args.command == "dogfood-summary":
        payload = MeasurementRecorder(ledger).summarize()
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
