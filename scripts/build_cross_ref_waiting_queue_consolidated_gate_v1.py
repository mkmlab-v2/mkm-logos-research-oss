#!/usr/bin/env python3
"""Consolidated waiting-queue gate for ENTRY_07/08/16 after P11 sequential rail [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SEQ_GATE = ROOT / "docs/final/artifacts/cross_ref_dss_entry_sequential_gate_v1_latest.json"
E07 = ROOT / "docs/final/artifacts/entry07_source_hunt_summary_latest.json"
E08 = ROOT / "docs/final/artifacts/entry08_source_hunt_summary_latest.json"
E16_SUM = ROOT / "docs/final/artifacts/entry16_source_hunt_summary.json"
E16_GATE = ROOT / "docs/final/artifacts/entry16_promotion_gate.json"
E16_LOCK = ROOT / "docs/final/artifacts/entry16_manual_promotion_decision_lock_latest.json"
CROSS = ROOT / "docs/final/artifacts/CROSS_REF_DSS_TO_STATES_DRAFT.json"
OUT_DEFAULT = ROOT / "docs/final/artifacts/cross_ref_waiting_queue_consolidated_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _sat_marker(entry_id: str, marker: str) -> bool:
    cross = _load(CROSS)
    row = next((e for e in cross.get("entries") or [] if e.get("entry_id") == entry_id), {})
    return marker in str(row.get("satellite_ref") or "")


def build() -> dict[str, Any]:
    seq = _load(SEQ_GATE)
    s07 = _load(E07)
    s08 = _load(E08)
    s16 = _load(E16_SUM)
    g16 = _load(E16_GATE)
    lock16 = _load(E16_LOCK)

    checks = {
        "sequential_rail_closed": {
            "passed": seq.get("gate_ok") is True
            and seq.get("sequential_rail_status") == "closed_sequential_documented",
        },
        "entry07_no_false_promotion": {
            "passed": s07.get("ssot_mutation") is False
            and s07.get("has_xlvi_xlvii_direct_witness") is False
            and "comparandum" in str(s07.get("action_recommendation", "")).lower(),
        },
        "entry08_no_false_promotion": {
            "passed": s08.get("ssot_mutation") is False
            and s08.get("has_fragment_line_direct_witness") is False,
        },
        "entry16_cross_ref_still_locked": {
            "passed": _sat_marker("ENTRY_16", "status=missing_anchor_until_source_update"),
        },
        "entry16_manual_review_documented": {
            "passed": g16.get("status") == "candidate_ready_for_manual_review"
            and lock16.get("constraints", {}).get("dss_missing_anchor_fact_lock") is True,
        },
        "send_gate_hold": {"passed": True},
    }
    gate_ok = all(c.get("passed") for c in checks.values())
    return {
        "schema": "cross_ref_waiting_queue_consolidated_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "send_gate": "HOLD",
        "waiting_queue_status": "documented_hold" if gate_ok else "incomplete",
        "gate_ok": gate_ok,
        "checks": checks,
        "entries": {
            "ENTRY_07": {
                "action": s07.get("action_recommendation"),
                "next_gate": s07.get("next_gate"),
                "has_direct_witness": s07.get("has_xlvi_xlvii_direct_witness"),
            },
            "ENTRY_08": {
                "action": s08.get("action_recommendation"),
                "next_gate": s08.get("next_gate"),
                "has_direct_witness": s08.get("has_fragment_line_direct_witness"),
            },
            "ENTRY_16": {
                "promotion_decision": g16.get("decision"),
                "promotion_status": g16.get("status"),
                "manual_lock_final_decision": lock16.get("final_decision"),
                "missing_anchor_lock": lock16.get("constraints", {}).get("dss_missing_anchor_fact_lock"),
            },
        },
        "reproduce": "py scripts/build_cross_ref_waiting_queue_consolidated_gate_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"ok": True, "gate_ok": doc["gate_ok"], "status": doc["waiting_queue_status"]},
            ensure_ascii=False,
        )
    )
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
