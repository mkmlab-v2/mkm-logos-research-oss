#!/usr/bin/env python3
"""Build Oracle Logos Tier-2 incremental append protocol SSOT ([HYPO] / B-track).

Blocker release matrix + repro pointer. Does not auto-create commander signoffs.

  py scripts/build_logos_oracle_tier2_incremental_append_protocol_v1.py
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/final/artifacts/logos_oracle_tier2_incremental_append_protocol_v1_latest.json"

from logos_oracle_tier2_incremental_append_lib_v1 import build_protocol_document  # noqa: E402


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=ROOT)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args()

    root = args.workspace_root.resolve()
    doc = build_protocol_document(root=root)
    doc["generated_at_utc"] = _utc_now()

    text = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    if args.stdout_only:
        print(text)
        return 0

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(
        f"tier2_cursor_rules_full_upgrade_ready={doc['tier2_cursor_rules_full_upgrade_ready']} "
        f"send_gate={doc['send_gate']}"
    )
    released = sum(1 for b in doc["blocker_release_matrix"] if b["released"])
    print(f"blockers_released={released}/4")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
