#!/usr/bin/env python3
"""Record commander Track A signoff for v3 merge production lexicon swap."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs/final/artifacts/hangul_v3_track_a_merge_commander_signoff_v1_latest.json"
PACKET = ROOT / "reports/hangul_v3_track_a_merge_preflight_packet_v1_latest.json"
GATE = ROOT / "reports/hangul_v3_track_a_merge_preflight_gate_v1_latest.json"
MERGE_CANDIDATE = (
    ROOT
    / "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41708_hangul_curated_export_candidate_v3_track_a_merge_preflight.json"
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    return str(p.relative_to(ROOT)).replace("\\", "/")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--commander-track-a-merge-approve",
        action="store_true",
        help="Approve v3 merge candidate → production 41708_rows_latest swap.",
    )
    ap.add_argument("--reviewer", default="commander")
    ap.add_argument("--note", default="")
    args = ap.parse_args()

    missing = [p for p in (PACKET, GATE, MERGE_CANDIDATE) if not p.is_file()]
    if missing:
        print("ABORT: missing", [_rel(p) for p in missing])
        return 1

    packet = json.loads(PACKET.read_text(encoding="utf-8"))
    gate = json.loads(GATE.read_text(encoding="utf-8"))
    ready = bool(packet.get("preflight_ready")) and bool(gate.get("preflight_ready"))
    decision_ok = gate.get("decision") == "ADVANCE_TRACK_A_MERGE_CANDIDATE"

    if args.commander_track_a_merge_approve and (not ready or not decision_ok):
        print("ABORT: preflight not ready or gate decision not ADVANCE_TRACK_A_MERGE_CANDIDATE")
        return 1

    doc = {
        "schema": "hangul_v3_track_a_merge_commander_signoff_v1",
        "recorded_at_utc": _utc(),
        "reviewer": str(args.reviewer),
        "approved": bool(args.commander_track_a_merge_approve),
        "decision": "APPROVED_TRACK_A_MERGE_APPLY" if args.commander_track_a_merge_approve else "PENDING",
        "scope": {
            "lexicon_production_ssot_swap": True,
            "multilens_active_report_write": False,
            "ms_paste_headline_auto_update": False,
            "send_gate_unlock": False,
            "live_trading": False,
            "fail_comp_004": True,
        },
        "evidence": {
            "preflight_packet": _rel(PACKET),
            "preflight_gate": _rel(GATE),
            "merge_candidate": _rel(MERGE_CANDIDATE),
            "preflight_gates": packet.get("preflight_gates"),
            "philosophy_summary": packet.get("philosophy_summary"),
            "golden40_delta_merge_vs_production": (packet.get("golden40_compare") or {}).get(
                "delta_merge_vs_production"
            ),
        },
        "commander_note": str(args.note).strip() or "commander chat approval: Track A v3 merge apply",
        "send_gate": "HOLD",
        "research_only": False,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": _rel(OUT), "approved": doc["approved"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
