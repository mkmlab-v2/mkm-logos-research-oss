#!/usr/bin/env python3
"""Record commander approval for Multi-Horizon Foresight Verification [HYPO] project."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/multi_horizon_foresight_project_approval_v1.json"
CHARTER = ROOT / "docs/final/artifacts/multi_horizon_foresight_verification_project_v1.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--approve", action="store_true", help="Set approved=true.")
    ap.add_argument("--revoke", action="store_true", help="Set approved=false.")
    ap.add_argument("--by", default="commander", help="Approver label.")
    ap.add_argument("--note", default="", help="Optional commander note.")
    ap.add_argument("--tier", default="T0", choices=("T0", "T1", "T2"))
    args = ap.parse_args()

    if not CHARTER.is_file():
        print(f"Missing charter: {CHARTER}", flush=True)
        return 2

    charter = json.loads(CHARTER.read_text(encoding="utf-8-sig"))
    out = args.output if args.output.is_absolute() else ROOT / args.output
    prev: dict = {}
    if out.is_file():
        prev = json.loads(out.read_text(encoding="utf-8-sig"))

    approved = bool(prev.get("approved"))
    if args.approve:
        approved = True
    if args.revoke:
        approved = False

    doc = {
        "schema": "multi_horizon_foresight_project_approval_v1",
        "project_id": charter.get("project_id", "MHFV-2026-06"),
        "approved": approved,
        "approved_at_utc": _utc_now() if approved else prev.get("approved_at_utc"),
        "approved_by": args.by if approved else prev.get("approved_by"),
        "tier_success_definition": args.tier,
        "forbidden_acknowledged": charter.get("forbidden", []),
        "commander_note": args.note or prev.get("commander_note", ""),
        "charter_path": str(CHARTER.relative_to(ROOT)).replace("\\", "/"),
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out.resolve()} approved={approved}")
    return 0 if approved else 1


if __name__ == "__main__":
    raise SystemExit(main())
