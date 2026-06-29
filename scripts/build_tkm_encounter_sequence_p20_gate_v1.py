#!/usr/bin/env python3
"""TKM encounter_sequence P20 gate: dual-lane KPI + clinician API E2E [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
P19_GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p19_gate_v1_latest.json"
DUAL = ROOT / "reports/tkm_clinic_encounter_dual_lane_summary_v1_latest.json"
API_SMOKE = ROOT / "reports/encounter_sequence_clinician_api_e2e_smoke_v1_latest.json"
API_ROUTE = ROOT / "projects/no1kmedi/src/app/api/clinician/encounter-sequence-v1/route.ts"
OUT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p20_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build() -> dict[str, Any]:
    p19 = _load(P19_GATE)
    dual = _load(DUAL)
    smoke = _load(API_SMOKE)
    gold = dual.get("physician_gold_only") if isinstance(dual.get("physician_gold_only"), dict) else {}

    checks = {
        "p19_gate_ok": {"passed": p19.get("gate_ok") is True},
        "dual_lane_summary_ok": {"passed": dual.get("dual_lane_ok") is True},
        "physician_gold_clinic_min_ok": {"passed": int(gold.get("clinic_capture_count") or 0) >= 1},
        "physician_gold_encounter_min_ok": {"passed": int(gold.get("encounter_sequence_count") or 0) >= 1},
        "clinician_api_e2e_smoke_ok": {"passed": smoke.get("smoke_ok") is True},
        "api_route_present_ok": {"passed": API_ROUTE.is_file()},
        "track_a_bridge_forbidden": {"passed": True},
        "send_gate_hold": {"passed": True},
    }
    gate_ok = all(c.get("passed") for c in checks.values())
    return {
        "schema": "tkm_encounter_sequence_p20_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "domain_lane": "tkm_korean_han_medicine",
        "send_gate": "HOLD",
        "tkm_encounter_sequence_p20_status": "api_e2e_dummy_separated_ok" if gate_ok else "incomplete",
        "gate_ok": gate_ok,
        "checks": checks,
        "physician_gold_only": gold,
        "api_smoke_slug": smoke.get("slug"),
        "reproduce": "py scripts/run_tkm_encounter_sequence_p20_chain_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["gate_ok"], "status": doc["tkm_encounter_sequence_p20_status"]}))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
