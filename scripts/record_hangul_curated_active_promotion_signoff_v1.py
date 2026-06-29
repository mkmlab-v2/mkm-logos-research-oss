#!/usr/bin/env python3
"""Record ACTIVE report promotion sign-off (Hangul curated 41687 candidate)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs/final/artifacts/hangul_curated_active_promotion_signoff_v1_latest.json"
PACKET = ROOT / "reports/hangul_curated_active_promotion_packet_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--commander-active-approve",
        action="store_true",
        help="Approve MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT write from curated candidate.",
    )
    ap.add_argument("--reviewer", default="commander")
    ap.add_argument("--note", default="")
    args = ap.parse_args()

    packet = json.loads(PACKET.read_text(encoding="utf-8")) if PACKET.is_file() else {}
    ready = bool(packet.get("promotion_ready"))

    if args.commander_active_approve and not ready:
        print("ABORT: active promotion packet promotion_ready=false")
        return 1

    doc = {
        "schema": "hangul_curated_active_promotion_signoff_v1",
        "recorded_at_utc": _utc(),
        "reviewer": str(args.reviewer),
        "approved": bool(args.commander_active_approve),
        "decision": "APPROVED" if args.commander_active_approve else "PENDING",
        "scope": {
            "multilens_active_report_write": True,
            "ms_paste_headline_update": False,
            "central_frozen_headline_update": False,
            "live_trading": False,
            "fail_comp_004": True,
        },
        "evidence_packet": str(PACKET.relative_to(ROOT)).replace("\\", "/") if PACKET.is_file() else None,
        "promotion_gates_snapshot": packet.get("promotion_gates"),
        "golden40_delta": (packet.get("golden40_compare") or {}).get("delta"),
        "commander_note": str(args.note).strip() or None,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(OUT), "approved": doc["approved"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
