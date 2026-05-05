#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Print last N lines from athena ECC append-only audit JSONL (Fact-Lock helper)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUDIT = WORKSPACE_ROOT / "reports" / "athena_ecc_audit.jsonl"


def main() -> int:
    ap = argparse.ArgumentParser(description="Show recent Athena ECC audit rows (JSONL).")
    ap.add_argument("--audit-jsonl", type=Path, default=DEFAULT_AUDIT, help="Audit JSONL path.")
    ap.add_argument("--last", type=int, default=20, help="Print last N complete lines.")
    args = ap.parse_args()

    path = args.audit_jsonl
    if not path.is_file():
        print(f"athena_ecc_logs_v1: file not found: {path}", file=sys.stderr)
        return 1

    raw = path.read_text(encoding="utf-8")
    lines = [ln for ln in raw.splitlines() if ln.strip()]
    tail = lines[-args.last :] if args.last > 0 else lines

    for ln in tail:
        try:
            obj = json.loads(ln)
        except json.JSONDecodeError:
            print(ln)
            continue
        print(json.dumps(obj, indent=2, ensure_ascii=False))
        print("---")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
