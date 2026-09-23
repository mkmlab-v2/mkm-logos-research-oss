"""Local-only secret management CLI for MKM Secure Agent Runtime V0.3.

Raw secret input is accepted only through getpass on the local terminal.
The CLI never has a command that prints the decrypted secret.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import getpass
import json
import os
from pathlib import Path

from secrets_dpapi import DPAPISecretStore


def _store() -> DPAPISecretStore:
    state = os.environ.get("MKM_AGENT_STATE", "").strip()
    if not state:
        raise SystemExit("MKM_AGENT_STATE is required")
    return DPAPISecretStore(Path(state))


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="command", required=True)

    p_set = sub.add_parser("set")
    p_set.add_argument("handle")
    p_set.add_argument("--service", required=True)
    p_set.add_argument("--label", default="")

    p_show = sub.add_parser("show")
    p_show.add_argument("handle")

    p_verify = sub.add_parser("verify")
    p_verify.add_argument("handle")

    p_remove = sub.add_parser("remove")
    p_remove.add_argument("handle")

    sub.add_parser("list")
    args = ap.parse_args()
    store = _store()

    if args.command == "set":
        first = getpass.getpass("Secret: ")
        second = getpass.getpass("Confirm: ")
        if first != second:
            raise SystemExit("secret confirmation mismatch")
        if not first:
            raise SystemExit("secret must not be empty")
        meta = store.set_secret(
            args.handle,
            first.encode("utf-8"),
            service=args.service,
            label=args.label,
        )
        result = asdict(meta)
    elif args.command == "show":
        result = asdict(store.metadata(args.handle))
    elif args.command == "verify":
        result = store.verify(args.handle)
    elif args.command == "remove":
        result = {"removed": store.remove(args.handle)}
    elif args.command == "list":
        result = [asdict(x) for x in store.list_metadata()]
    else:
        raise AssertionError(args.command)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
