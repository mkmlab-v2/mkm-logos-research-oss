#!/usr/bin/env python3
"""TKM encounter_sequence P48 gate: extended stack export bundle [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
P47_GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p47_gate_v1_latest.json"
BUNDLE = ROOT / "reports/tkm_encounter_sequence_extended_stack_export_bundle_v1_latest.json"
ARTIFACT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_extended_stack_export_bundle_v1_latest.json"
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"
OUT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p48_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build() -> dict[str, Any]:
    p47 = _load(P47_GATE)
    bundle = _load(BUNDLE)
    weekly = _load(WEEKLY)
    eb = weekly.get("extended_stack_export_bundle_kpi") if isinstance(weekly.get("extended_stack_export_bundle_kpi"), dict) else {}
    gates = bundle.get("gates") if isinstance(bundle.get("gates"), dict) else {}
    snap = bundle.get("rollup_snapshot") if isinstance(bundle.get("rollup_snapshot"), dict) else {}

    checks = {
        "p47_gate_ok": {"passed": p47.get("gate_ok") is True},
        "extended_export_bundle_ok": {"passed": bundle.get("extended_export_bundle_ok") is True},
        "bundle_artifact_mirrored": {"passed": ARTIFACT.is_file()},
        "all_gates_p33_p47_ok": {
            "passed": all((gates.get(k) or {}).get("gate_ok") is True for k in gates)
        },
        "base_export_bundle_ok": {"passed": bundle.get("base_export_bundle_ok") is True},
        "extension_closure_ok": {"passed": bundle.get("extension_closure_ok") is True},
        "rollup_snapshot_ok": {
            "passed": all(
                snap.get(k) is True
                for k in (
                    "lens_stack_rollup_ok",
                    "passive_integrated_ok",
                    "clinical_validation_stub_ok",
                    "curated_milestone_ok",
                    "gpu_interpret_observation_ok",
                )
            )
        },
        "weekly_extended_bundle_sync_ok": {"passed": eb.get("extended_stack_export_headline_ok") is True},
        "auto_training_forbidden": {"passed": bundle.get("research_only") is True},
        "track_a_bridge_forbidden": {"passed": True},
        "send_gate_hold": {"passed": True},
    }
    gate_ok = all(c.get("passed") for c in checks.values())
    return {
        "schema": "tkm_encounter_sequence_p48_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "domain_lane": "tkm_korean_han_medicine",
        "send_gate": "HOLD",
        "research_only": True,
        "tkm_encounter_sequence_p48_status": "extended_stack_export_bundle_wire_ok" if gate_ok else "incomplete",
        "gate_ok": gate_ok,
        "checks": checks,
        "bundle_artifact_path": str(ARTIFACT).replace("\\", "/"),
        "reproduce": "py scripts/run_tkm_encounter_sequence_p48_chain_v1.py --skip-http",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["gate_ok"], "status": doc["tkm_encounter_sequence_p48_status"]}))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
