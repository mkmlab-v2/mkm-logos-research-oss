#!/usr/bin/env python3
"""Record commander signoff for Hangul v3 Golden-40 B-track extension (not production SSOT swap)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs/final/artifacts/hangul_v3_golden40_btrack_extension_commander_signoff_v1_latest.json"
P3_GATE = ROOT / "reports/p3_root_generator_bench_gate_hangul41676_v1_latest.json"
V3_PILOT = ROOT / "reports/lexicon_hangul_curated_pilot_v3_golden40_evidence_latest.json"
V3_EXPORT = ROOT / "reports/hangul_ko_lemma_v3_export_candidate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return p.relative_to(ROOT).as_posix()
    except ValueError:
        return p.as_posix()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--commander-btrack-extension-approve",
        action="store_true",
        help="Approve B-track P3 extension lane only (production_ssot_swap remains false).",
    )
    ap.add_argument("--note", default="")
    args = ap.parse_args()

    p3 = json.loads(P3_GATE.read_text(encoding="utf-8")) if P3_GATE.is_file() else {}
    pilot = json.loads(V3_PILOT.read_text(encoding="utf-8")) if V3_PILOT.is_file() else {}
    export = json.loads(V3_EXPORT.read_text(encoding="utf-8")) if V3_EXPORT.is_file() else {}

    p3_ok = p3.get("decision") == "ADVANCE_EXTENSION_CANDIDATE"
    both_pass = bool((pilot.get("double_gate") or {}).get("both_pass"))
    pilot_blocks_prod = not bool((pilot.get("verdict") or {}).get("promote_production_ssot"))

    if args.commander_btrack_extension_approve and not p3_ok:
        print("ABORT: P3 hangul41676 gate not ADVANCE_EXTENSION_CANDIDATE")
        return 1
    if args.commander_btrack_extension_approve and not both_pass:
        print("ABORT: v3 pilot double_gate.both_pass is false")
        return 1

    doc = {
        "schema": "hangul_v3_golden40_btrack_extension_commander_signoff_v1",
        "recorded_at_utc": _utc(),
        "approved": bool(args.commander_btrack_extension_approve),
        "decision": "APPROVED_BTRACK_EXTENSION_ONLY" if args.commander_btrack_extension_approve else "PENDING",
        "scope": {
            "p3_extension_lane": True,
            "production_ssot_swap": False,
            "track_a_active_report_write": False,
            "ms_paste_headline_update": False,
            "live_trading": False,
        },
        "evidence": {
            "p3_gate": _rel(P3_GATE) if P3_GATE.is_file() else None,
            "p3_decision": p3.get("decision"),
            "v3_pilot": _rel(V3_PILOT) if V3_PILOT.is_file() else None,
            "double_gate_both_pass": both_pass,
            "pilot_promote_production_ssot": (pilot.get("verdict") or {}).get("promote_production_ssot"),
            "v3_export_report": _rel(V3_EXPORT) if V3_EXPORT.is_file() else None,
            "export_promotion_hold": export.get("promotion"),
        },
        "production_pointer_policy": {
            "current_ssot_note": "41708_rows_latest (v2 50-ko) remains production until separate Track A gate",
            "v3_41676_role": "Golden-40 evidence extension candidate only",
            "pilot_blocks_auto_prod_swap": pilot_blocks_prod,
        },
        "commander_note": str(args.note).strip() or None,
        "send_gate": "HOLD",
        "research_only": True,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": _rel(OUT), "approved": doc["approved"], "production_ssot_swap": False}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
