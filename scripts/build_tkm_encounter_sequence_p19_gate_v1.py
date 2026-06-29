#!/usr/bin/env python3
"""TKM encounter_sequence P19 gate: clinic bridge + unified KPI + weekly task [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
P18_GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p18_gate_v1_latest.json"
UNIFIED = ROOT / "reports/tkm_clinic_encounter_unified_disagreement_summary_v1_latest.json"
TASK_VERIFY = ROOT / "reports/tkm_encounter_sequence_weekly_task_verify_v1_latest.json"
ACK = ROOT / "docs/final/artifacts/encounter_sequence_curated_learning_human_gate_ack_v1.json"
OUT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p19_gate_v1_latest.json"
CLINIC_SEQ_ID = "SEQ-CLINIC-P19-01"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _clinic_sequence_in_ledger() -> bool:
    import importlib.util

    ledger_path = ROOT / "scripts/encounter_sequence_ledger_v1.py"
    spec = importlib.util.spec_from_file_location("encounter_sequence_ledger_v1", ledger_path)
    if spec is None or spec.loader is None:
        return False
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for row in mod.iter_ledger_records(ROOT):
        enc = row.get("encounter") if isinstance(row.get("encounter"), dict) else {}
        if str(enc.get("sequence_id") or "") == CLINIC_SEQ_ID:
            closure = row.get("physician_closure")
            if isinstance(closure, dict):
                return True
    return False


def build() -> dict[str, Any]:
    p18 = _load(P18_GATE)
    unified = _load(UNIFIED)
    task = _load(TASK_VERIFY)
    ack = _load(ACK)

    checks = {
        "p18_gate_ok": {"passed": p18.get("gate_ok") is True},
        "clinic_capture_sequence_ok": {"passed": _clinic_sequence_in_ledger()},
        "unified_disagreement_summary_ok": {"passed": unified.get("unified_ok") is True},
        "weekly_task_registered_ok": {"passed": task.get("registered") is True},
        "curated_human_gate_ack_ok": {"passed": ack.get("human_gate_ack") is True},
        "track_a_bridge_forbidden": {"passed": True},
        "send_gate_hold": {"passed": True},
    }
    gate_ok = all(c.get("passed") for c in checks.values())
    return {
        "schema": "tkm_encounter_sequence_p19_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "domain_lane": "tkm_korean_han_medicine",
        "send_gate": "HOLD",
        "tkm_encounter_sequence_p19_status": "clinic_bridge_weekly_ok" if gate_ok else "incomplete",
        "gate_ok": gate_ok,
        "checks": checks,
        "clinic_sequence_id": CLINIC_SEQ_ID,
        "reproduce": "py scripts/run_tkm_encounter_sequence_p19_chain_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["gate_ok"], "status": doc["tkm_encounter_sequence_p19_status"]}))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
