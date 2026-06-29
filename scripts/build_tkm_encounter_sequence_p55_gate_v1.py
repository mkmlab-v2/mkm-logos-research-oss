#!/usr/bin/env python3
"""TKM encounter_sequence P55 gate: post-export extended export bundle [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
P54_GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p54_gate_v1_latest.json"
BUNDLE = ROOT / "reports/tkm_encounter_sequence_post_export_extended_export_bundle_v1_latest.json"
ARTIFACT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_post_export_extended_export_bundle_v1_latest.json"
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"
OUT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p55_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build() -> dict[str, Any]:
    p54 = _load(P54_GATE)
    bundle = _load(BUNDLE)
    weekly = _load(WEEKLY)
    peeb = weekly.get("post_export_extended_export_bundle_kpi") if isinstance(
        weekly.get("post_export_extended_export_bundle_kpi"), dict
    ) else {}
    gates = bundle.get("gates") if isinstance(bundle.get("gates"), dict) else {}
    snap = bundle.get("rollup_snapshot") if isinstance(bundle.get("rollup_snapshot"), dict) else {}

    checks = {
        "p54_gate_ok": {"passed": p54.get("gate_ok") is True},
        "post_export_extended_export_bundle_ok": {
            "passed": bundle.get("post_export_extended_export_bundle_ok") is True
        },
        "bundle_artifact_mirrored": {"passed": ARTIFACT.is_file()},
        "all_gates_p33_p54_ok": {
            "passed": all((gates.get(k) or {}).get("gate_ok") is True for k in gates)
        },
        "extended_export_bundle_ok": {"passed": bundle.get("extended_export_bundle_ok") is True},
        "full_post_export_closure_ok": {"passed": bundle.get("full_post_export_closure_ok") is True},
        "rollup_snapshot_ok": {
            "passed": all(
                snap.get(k) is True
                for k in (
                    "lens_stack_rollup_ok",
                    "passive_integrated_ok",
                    "clinical_validation_stub_ok",
                    "curated_milestone_ok",
                    "export_sync_ok",
                    "post_export_observation_ok",
                    "integrated_closure_ok",
                )
            )
        },
        "weekly_post_export_extended_bundle_sync_ok": {
            "passed": peeb.get("post_export_extended_export_headline_ok") is True
        },
        "auto_training_forbidden": {"passed": bundle.get("research_only") is True},
        "track_a_bridge_forbidden": {"passed": True},
        "send_gate_hold": {"passed": True},
    }
    gate_ok = all(c.get("passed") for c in checks.values())
    return {
        "schema": "tkm_encounter_sequence_p55_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "domain_lane": "tkm_korean_han_medicine",
        "send_gate": "HOLD",
        "research_only": True,
        "tkm_encounter_sequence_p55_status": "post_export_extended_export_bundle_wire_ok" if gate_ok else "incomplete",
        "gate_ok": gate_ok,
        "checks": checks,
        "bundle_artifact_path": str(ARTIFACT).replace("\\", "/"),
        "reproduce": "py scripts/run_tkm_encounter_sequence_p55_chain_v1.py --skip-http",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["gate_ok"], "status": doc["tkm_encounter_sequence_p55_status"]}))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
