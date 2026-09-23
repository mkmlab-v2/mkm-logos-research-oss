"""Local human approval CLI for MKM Secure Agent Runtime V0.1."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from approval import ApprovalBroker


def _roots() -> list[Path]:
    raw = os.environ.get("MKM_AGENT_ROOTS", "")
    roots = [Path(x) for x in raw.split(os.pathsep) if x.strip()]
    if not roots:
        raise SystemExit("MKM_AGENT_ROOTS is required")
    return roots


def _broker() -> ApprovalBroker:
    state = os.environ.get("MKM_AGENT_STATE", "").strip()
    if not state:
        raise SystemExit("MKM_AGENT_STATE is required")
    return ApprovalBroker(Path(state), protected_roots=_roots())


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="command", required=True)
    for name in ("show", "approve", "deny"):
        p = sub.add_parser(name)
        p.add_argument("approval_id")
    sub.add_parser("list")
    args = ap.parse_args()
    broker = _broker()

    if args.command == "list":
        result = broker.list_requests()
    elif args.command == "show":
        result = broker.read(args.approval_id)
    elif args.command == "approve":
        result = broker.approve(args.approval_id)
    elif args.command == "deny":
        result = broker.deny(args.approval_id)
    else:
        raise AssertionError(args.command)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
