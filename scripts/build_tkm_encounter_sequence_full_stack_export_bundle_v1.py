#!/usr/bin/env python3
"""Build TKM encounter_sequence full-stack export bundle (P33–P41) [HYPO]."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/tkm_encounter_sequence_full_stack_export_bundle_v1_latest.json"
ARTIFACT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_full_stack_export_bundle_v1_latest.json"

GATE_KEYS = ("p33", "p34", "p35", "p36", "p37", "p38", "p39", "p40", "p41")
GATE_PATHS = {k: ROOT / f"docs/final/artifacts/tkm_encounter_sequence_{k}_gate_v1_latest.json" for k in GATE_KEYS}

LENS_ROLLUP = ROOT / "reports/tkm_encounter_sequence_lens_stack_rollup_v1_latest.json"
PASSIVE_INTEGRATED = ROOT / "reports/tkm_encounter_sequence_passive_integrated_rollup_v1_latest.json"
CLINICAL_STUB = ROOT / "reports/tkm_encounter_sequence_clinical_validation_stub_v1_latest.json"
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"
OPS = ROOT / "reports/tkm_encounter_sequence_ops_closure_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _gate_status(key: str) -> dict[str, Any]:
    doc = _load(GATE_PATHS[key])
    status_key = f"tkm_encounter_sequence_{key}_status"
    return {
        "gate_ok": doc.get("gate_ok") is True,
        "status": doc.get(status_key),
    }


def build() -> dict[str, Any]:
    gates = {k: _gate_status(k) for k in GATE_KEYS}
    all_gates_ok = all(g.get("gate_ok") for g in gates.values())
    lens = _load(LENS_ROLLUP)
    passive = _load(PASSIVE_INTEGRATED)
    clinical = _load(CLINICAL_STUB)
    weekly = _load(WEEKLY)
    ops = _load(OPS)

    rollups_ok = (
        lens.get("rollup_ok") is True
        and passive.get("integrated_ok") is True
        and clinical.get("validation_stub_ok") is True
    )
    export_bundle_ok = (
        all_gates_ok
        and rollups_ok
        and weekly.get("weekly_ok") is True
        and ops.get("closure_ok") is True
    )

    return {
        "schema": "tkm_encounter_sequence_full_stack_export_bundle_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "domain_lane": "tkm_korean_han_medicine",
        "send_gate": "HOLD",
        "non_gating": True,
        "research_only": True,
        "export_bundle_ok": export_bundle_ok,
        "gates": gates,
        "rollup_snapshot": {
            "lens_stack_rollup_ok": lens.get("rollup_ok"),
            "passive_integrated_ok": passive.get("integrated_ok"),
            "clinical_validation_stub_ok": clinical.get("validation_stub_ok"),
            "physician_gold_sequence_count": clinical.get("physician_gold_sequence_count"),
            "cross_lens_resonance_index": lens.get("kpi_snapshot", {}).get("cross_lens_resonance_index")
            if isinstance(lens.get("kpi_snapshot"), dict)
            else None,
            "disagreement_physician_authority_rate": lens.get("kpi_snapshot", {}).get(
                "disagreement_physician_authority_rate"
            )
            if isinstance(lens.get("kpi_snapshot"), dict)
            else None,
            "interpret_gpu_train_attempted": passive.get("interpret_gpu_train_attempted"),
            "curated_learning_registry_row_count": passive.get("curated_learning_registry_row_count"),
        },
        "weekly_report_version": weekly.get("version"),
        "ops_closure_version": ops.get("version"),
        "ops_closure_ok": ops.get("closure_ok"),
        "lens_order_ko": "Field(L4 사상) → L5 명리 → L6 성경 → L7 cross-lens → conflict → disagreement×resolver → passive → clinical stub",
        "artifact_refs": {
            "lens_stack_rollup": str(LENS_ROLLUP).replace("\\", "/"),
            "passive_integrated": str(PASSIVE_INTEGRATED).replace("\\", "/"),
            "clinical_validation_stub": str(CLINICAL_STUB).replace("\\", "/"),
            "weekly_report": str(WEEKLY).replace("\\", "/"),
        },
        "note_ko": "P33–P41 full-stack export bundle [HYPO][NON_GATING]; NotebookLM/ops 참고용; Track A 합선 금지.",
        "reproduce": "py scripts/build_tkm_encounter_sequence_full_stack_export_bundle_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--mirror-artifact", action="store_true", default=True)
    ap.add_argument("--no-mirror-artifact", action="store_false", dest="mirror_artifact")
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.mirror_artifact:
        ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(args.out, ARTIFACT)
    print(json.dumps({"ok": doc.get("export_bundle_ok"), "gates": len(doc.get("gates") or {})}))
    return 0 if doc.get("export_bundle_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
