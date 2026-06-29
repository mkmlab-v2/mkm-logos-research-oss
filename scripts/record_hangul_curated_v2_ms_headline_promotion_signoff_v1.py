#!/usr/bin/env python3
"""Record v2 MS headline policy sign-off (ACTIVE bench KPI; MS submission archive unchanged)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs/final/artifacts/hangul_curated_v2_ms_headline_promotion_signoff_v1_latest.json"
PACKET = ROOT / "reports/hangul_curated_v2_ms_headline_promotion_packet_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--commander-ms-approve", action="store_true")
    ap.add_argument("--reviewer", default="commander")
    ap.add_argument("--note", default="")
    args = ap.parse_args()

    packet = json.loads(PACKET.read_text(encoding="utf-8")) if PACKET.is_file() else {}
    if args.commander_ms_approve and not packet.get("promotion_ready"):
        print("ABORT: v2 ms headline promotion_ready=false")
        return 1

    doc = {
        "schema": "hangul_curated_v2_ms_headline_promotion_signoff_v1",
        "recorded_at_utc": _utc(),
        "reviewer": str(args.reviewer),
        "approved": bool(args.commander_ms_approve),
        "decision": "APPROVED" if args.commander_ms_approve else "PENDING",
        "scope": {
            "headline_policy_write": True,
            "bench_lexicon_pointer_write": True,
            "internal_paste_snippet_write": True,
            "ms_submission_hwp_archive_rewrite": False,
            "multilens_active_report_write": False,
            "fail_comp_004": True,
        },
        "evidence_packet": str(PACKET.relative_to(ROOT)).replace("\\", "/") if PACKET.is_file() else None,
        "commander_note": str(args.note).strip() or None,
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(OUT), "approved": doc["approved"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
