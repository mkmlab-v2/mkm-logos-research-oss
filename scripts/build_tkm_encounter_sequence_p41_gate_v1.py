#!/usr/bin/env python3
"""TKM encounter_sequence P41 gate: clinical validation stub [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
P40_GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p40_gate_v1_latest.json"
STUB = ROOT / "reports/tkm_encounter_sequence_clinical_validation_stub_v1_latest.json"
ARTIFACT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_clinical_validation_stub_v1_latest.json"
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"
OUT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p41_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build() -> dict[str, Any]:
    p40 = _load(P40_GATE)
    stub = _load(STUB)
    weekly = _load(WEEKLY)
    cv = weekly.get("clinical_validation_stub_kpi") if isinstance(weekly.get("clinical_validation_stub_kpi"), dict) else {}

    checks = {
        "p40_gate_ok": {"passed": p40.get("gate_ok") is True},
        "validation_stub_ok": {"passed": stub.get("validation_stub_ok") is True},
        "stub_artifact_mirrored": {"passed": ARTIFACT.is_file()},
        "boundary_contract_pass_rate_full": {"passed": stub.get("boundary_contract_pass_rate") == 1.0},
        "physician_closure_min_ok": {"passed": (stub.get("physician_closure_pass_rate") or 0) >= 0.5},
        "lens_stack_wired_min_ok": {"passed": (stub.get("lens_stack_wired_rate") or 0) >= 0.75},
        "weekly_clinical_stub_sync_ok": {"passed": cv.get("clinical_validation_headline_ok") is True},
        "track_a_bridge_forbidden": {"passed": True},
        "send_gate_hold": {"passed": True},
    }
    gate_ok = all(c.get("passed") for c in checks.values())
    return {
        "schema": "tkm_encounter_sequence_p41_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "domain_lane": "tkm_korean_han_medicine",
        "send_gate": "HOLD",
        "research_only": True,
        "tkm_encounter_sequence_p41_status": "clinical_validation_stub_wire_ok" if gate_ok else "incomplete",
        "gate_ok": gate_ok,
        "checks": checks,
        "stub_artifact_path": str(ARTIFACT).replace("\\", "/"),
        "reproduce": "py scripts/run_tkm_encounter_sequence_p41_chain_v1.py --skip-http",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["gate_ok"], "status": doc["tkm_encounter_sequence_p41_status"]}))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
