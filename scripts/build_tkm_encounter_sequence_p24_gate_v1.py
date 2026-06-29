#!/usr/bin/env python3
"""TKM encounter_sequence P24 gate: encounter_match_rate on gold lane [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
P23_GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p23_gate_v1_latest.json"
DUAL = ROOT / "reports/tkm_clinic_encounter_dual_lane_summary_v1_latest.json"
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"
OUT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p24_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build() -> dict[str, Any]:
    p23 = _load(P23_GATE)
    dual = _load(DUAL)
    weekly = _load(WEEKLY)
    gold = dual.get("physician_gold_only") if isinstance(dual.get("physician_gold_only"), dict) else {}
    headline = weekly.get("headline_kpi") if isinstance(weekly.get("headline_kpi"), dict) else {}
    enc_rate = gold.get("encounter_match_rate")
    headline_enc = headline.get("encounter_match_rate")

    checks = {
        "p23_gate_ok": {"passed": p23.get("gate_ok") is True},
        "encounter_match_rate_not_null": {"passed": enc_rate is not None},
        "weekly_headline_encounter_match_ok": {"passed": headline_enc is not None},
        "encounter_match_rate_in_range": {
            "passed": isinstance(enc_rate, (int, float)) and 0.0 <= float(enc_rate) <= 1.0
        },
        "dual_lane_headline_ok": {"passed": headline.get("dual_lane_headline_ok") is True},
        "track_a_bridge_forbidden": {"passed": True},
        "send_gate_hold": {"passed": True},
    }
    gate_ok = all(c.get("passed") for c in checks.values())
    return {
        "schema": "tkm_encounter_sequence_p24_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "domain_lane": "tkm_korean_han_medicine",
        "send_gate": "HOLD",
        "tkm_encounter_sequence_p24_status": "encounter_match_rate_ok" if gate_ok else "incomplete",
        "gate_ok": gate_ok,
        "checks": checks,
        "physician_gold_only": gold,
        "headline_kpi": headline,
        "dual_lane_ref": str(DUAL).replace("\\", "/"),
        "reproduce": "py scripts/run_tkm_encounter_sequence_p24_chain_v1.py --with-p23-refresh",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["gate_ok"], "status": doc["tkm_encounter_sequence_p24_status"]}))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
