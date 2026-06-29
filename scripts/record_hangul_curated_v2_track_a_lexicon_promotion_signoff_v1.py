#!/usr/bin/env python3
"""Record v2 Track A lexicon promotion sign-off (41708 · not ACTIVE)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs/final/artifacts/hangul_curated_v2_track_a_lexicon_promotion_signoff_v1_latest.json"
PACKET_DEFAULT = ROOT / "reports/hangul_curated_v2_track_a_promotion_packet_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--commander-v2-lexicon-approve", action="store_true")
    ap.add_argument("--packet", type=Path, default=PACKET_DEFAULT)
    ap.add_argument("--reviewer", default="commander")
    ap.add_argument("--note", default="")
    args = ap.parse_args()

    packet_path = args.packet if args.packet.is_absolute() else (ROOT / args.packet)
    packet = json.loads(packet_path.read_text(encoding="utf-8")) if packet_path.is_file() else {}
    ready = bool(packet.get("promotion_ready"))
    wave = str(packet.get("wave") or "v2_50_lemmas")
    cand_path = (packet.get("evidence") or {}).get("export_candidate")
    cand_doc = {}
    if cand_path:
        cp = ROOT / str(cand_path).replace("/", "\\")
        if cp.is_file():
            cand_doc = json.loads(cp.read_text(encoding="utf-8"))
    ko_n = sum(1 for e in cand_doc.get("entries") or [] if str(e.get("lang", "")).lower() == "ko")
    row_count = int(cand_doc.get("row_count") or len(cand_doc.get("entries") or []) or 0)

    if args.commander_v2_lexicon_approve and not ready:
        print("ABORT: v2 promotion_ready=false")
        return 1

    doc = {
        "schema": "hangul_curated_v2_track_a_lexicon_promotion_signoff_v1",
        "recorded_at_utc": _utc(),
        "reviewer": str(args.reviewer),
        "approved": bool(args.commander_v2_lexicon_approve),
        "decision": "APPROVED" if args.commander_v2_lexicon_approve else "PENDING",
        "scope": {
            "lexicon_production_ssot_swap": True,
            "target_row_count": row_count or None,
            "lemma_count_curated": ko_n or None,
            "wave": wave,
            "multilens_active_report_write": False,
            "ms_paste_headline_update": False,
            "fail_comp_004": True,
        },
        "evidence_packet": str(packet_path.relative_to(ROOT)).replace("\\", "/") if packet_path.is_file() else None,
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
