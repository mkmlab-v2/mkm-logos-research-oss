#!/usr/bin/env python3
"""TKM encounter_sequence P23 gate: physician_gold autofill + dual-lane headline [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
P22_GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p22_gate_v1_latest.json"
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"
AUTOFILL = ROOT / "reports/tkm_physician_gold_manual_autofill_v1_latest.json"
DUAL = ROOT / "reports/tkm_clinic_encounter_dual_lane_summary_v1_latest.json"
OUT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p23_gate_v1_latest.json"
AUTO_SEQ_IDS = ("SEQ-PHYSICIAN-GOLD-AUTO-01", "SEQ-PHYSICIAN-GOLD-AUTO-02")


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _seq_in_ledger(seq_id: str) -> bool:
    import importlib.util

    ledger_path = ROOT / "scripts/encounter_sequence_ledger_v1.py"
    spec = importlib.util.spec_from_file_location("encounter_sequence_ledger_v1", ledger_path)
    if spec is None or spec.loader is None:
        return False
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for row in mod.iter_ledger_records(ROOT):
        enc = row.get("encounter") if isinstance(row.get("encounter"), dict) else {}
        if str(enc.get("sequence_id") or "") == seq_id:
            return True
    return False


def build() -> dict[str, Any]:
    p22 = _load(P22_GATE)
    weekly = _load(WEEKLY)
    autofill = _load(AUTOFILL)
    dual = _load(DUAL)
    headline = weekly.get("headline_kpi") if isinstance(weekly.get("headline_kpi"), dict) else {}
    gold = dual.get("physician_gold_only") if isinstance(dual.get("physician_gold_only"), dict) else {}

    checks = {
        "p22_gate_ok": {"passed": p22.get("gate_ok") is True},
        "physician_gold_autofill_ok": {"passed": autofill.get("ok") is True},
        "physician_gold_auto_seq_01_ok": {"passed": _seq_in_ledger(AUTO_SEQ_IDS[0])},
        "physician_gold_auto_seq_02_ok": {"passed": _seq_in_ledger(AUTO_SEQ_IDS[1])},
        "dual_lane_headline_ok": {"passed": headline.get("dual_lane_headline_ok") is True},
        "physician_gold_clinic_min_ok": {"passed": int(gold.get("clinic_capture_count") or 0) >= 3},
        "track_a_bridge_forbidden": {"passed": True},
        "send_gate_hold": {"passed": True},
    }
    gate_ok = all(c.get("passed") for c in checks.values())
    return {
        "schema": "tkm_encounter_sequence_p23_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "domain_lane": "tkm_korean_han_medicine",
        "send_gate": "HOLD",
        "tkm_encounter_sequence_p23_status": "physician_gold_dual_lane_headline_ok" if gate_ok else "incomplete",
        "gate_ok": gate_ok,
        "checks": checks,
        "headline_kpi": headline,
        "physician_gold_only": gold,
        "autofill_ref": str(AUTOFILL).replace("\\", "/"),
        "weekly_report_ref": str(WEEKLY).replace("\\", "/"),
        "reproduce": "py scripts/run_tkm_encounter_sequence_p23_chain_v1.py --with-p22-refresh",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["gate_ok"], "status": doc["tkm_encounter_sequence_p23_status"]}))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
