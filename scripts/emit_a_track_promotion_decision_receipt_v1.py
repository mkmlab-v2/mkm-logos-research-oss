#!/usr/bin/env python3
"""Emit A-track promotion decision receipt consumed by build_a_track_go_nogo_status.py."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "reports" / "a_track_promotion_decision_latest.json"
ALLOWED_STAGE = {"S2_PAPER_STRICT", "S3_PAPER_SCALED", "S4_LIMITED_LIVE"}


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _write(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Emit A-track stage approval receipt.")
    ap.add_argument("--stage", default="S2_PAPER_STRICT", choices=sorted(ALLOWED_STAGE))
    ap.add_argument("--approver", default="PRO")
    ap.add_argument("--status", default="accepted", choices=("accepted", "rejected"))
    ap.add_argument("--action", default="approve", choices=("approve", "reject"))
    ap.add_argument("--note", default="Manual operator receipt for A-track stage gate.")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    payload = {
        "schema": "a_track_promotion_decision_v1",
        "generated_at": _now_utc(),
        "action": args.action,
        "status": args.status,
        "requested_stage": args.stage,
        "approver": args.approver,
        "note": args.note,
    }
    _write(out_path, payload)
    print(f"WROTE: {out_path}")
    print(f"requested_stage: {payload['requested_stage']}")
    print(f"status: {payload['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
