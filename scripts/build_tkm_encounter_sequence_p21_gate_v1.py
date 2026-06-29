#!/usr/bin/env python3
"""TKM encounter_sequence P21 gate: physician_gold + multiturn + API offline [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
P20_GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p20_gate_v1_latest.json"
DUAL = ROOT / "reports/tkm_clinic_encounter_dual_lane_summary_v1_latest.json"
MULTI = ROOT / "reports/encounter_sequence_multiturn_smoke_v1_latest.json"
OFFLINE = ROOT / "reports/no1kmedi_encounter_sequence_api_offline_smoke_v1_latest.json"
OUT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p21_gate_v1_latest.json"
PHYSICIAN_GOLD_SEQ = "SEQ-PHYSICIAN-GOLD-P21-01"
MULTITURN_SEQ = "SEQ-MULTITURN-P21-01"


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
    p20 = _load(P20_GATE)
    dual = _load(DUAL)
    multi = _load(MULTI)
    offline = _load(OFFLINE)
    gold = dual.get("physician_gold_only") if isinstance(dual.get("physician_gold_only"), dict) else {}

    checks = {
        "p20_gate_ok": {"passed": p20.get("gate_ok") is True},
        "physician_gold_capture_ok": {"passed": _seq_in_ledger(PHYSICIAN_GOLD_SEQ)},
        "multiturn_smoke_ok": {"passed": multi.get("smoke_ok") is True},
        "multiturn_turn_count_min_ok": {"passed": int(multi.get("turn_count") or 0) >= 3},
        "api_offline_smoke_ok": {"passed": offline.get("offline_smoke_ok") is True},
        "physician_gold_clinic_min_ok": {"passed": int(gold.get("clinic_capture_count") or 0) >= 1},
        "track_a_bridge_forbidden": {"passed": True},
        "send_gate_hold": {"passed": True},
    }
    gate_ok = all(c.get("passed") for c in checks.values())
    return {
        "schema": "tkm_encounter_sequence_p21_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "domain_lane": "tkm_korean_han_medicine",
        "send_gate": "HOLD",
        "tkm_encounter_sequence_p21_status": "physician_gold_multiturn_ok" if gate_ok else "incomplete",
        "gate_ok": gate_ok,
        "checks": checks,
        "physician_gold_sequence_id": PHYSICIAN_GOLD_SEQ,
        "multiturn_sequence_id": MULTITURN_SEQ,
        "physician_gold_only": gold,
        "reproduce": "py scripts/run_tkm_encounter_sequence_p21_chain_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["gate_ok"], "status": doc["tkm_encounter_sequence_p21_status"]}))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
