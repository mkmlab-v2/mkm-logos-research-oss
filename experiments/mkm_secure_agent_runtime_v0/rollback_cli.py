"""Local-only rollback CLI for MKM Secure Agent Runtime V0.4."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path

from snapshot import SnapshotStore


def _roots() -> list[Path]:
    raw = os.environ.get("MKM_AGENT_ROOTS", "")
    roots = [Path(x) for x in raw.split(os.pathsep) if x.strip()]
    if not roots:
        raise SystemExit("MKM_AGENT_ROOTS is required")
    return roots


def _store() -> SnapshotStore:
    state = os.environ.get("MKM_AGENT_STATE", "").strip()
    if not state:
        raise SystemExit("MKM_AGENT_STATE is required")
    return SnapshotStore(Path(state), protected_roots=_roots())


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="command", required=True)

    p_show = sub.add_parser("show")
    p_show.add_argument("snapshot_id")

    p_restore = sub.add_parser("restore")
    p_restore.add_argument("snapshot_id")

    sub.add_parser("list")
    args = ap.parse_args()
    store = _store()

    if args.command == "show":
        result = asdict(store.metadata(args.snapshot_id))
    elif args.command == "restore":
        result = store.restore(args.snapshot_id)
    elif args.command == "list":
        result = [asdict(x) for x in store.list_metadata()]
    else:
        raise AssertionError(args.command)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
