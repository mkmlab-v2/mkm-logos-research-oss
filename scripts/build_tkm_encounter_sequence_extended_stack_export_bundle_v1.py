#!/usr/bin/env python3
"""Build TKM encounter_sequence extended stack export bundle (P33–P47) [HYPO]."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/tkm_encounter_sequence_extended_stack_export_bundle_v1_latest.json"
ARTIFACT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_extended_stack_export_bundle_v1_latest.json"

GATE_KEYS = tuple(f"p{n}" for n in range(33, 48))
GATE_PATHS = {k: ROOT / f"docs/final/artifacts/tkm_encounter_sequence_{k}_gate_v1_latest.json" for k in GATE_KEYS}

BASE_BUNDLE = ROOT / "reports/tkm_encounter_sequence_full_stack_export_bundle_v1_latest.json"
EXTENSION_CLOSURE = ROOT / "reports/tkm_encounter_sequence_stack_extension_closure_v1_latest.json"
MILESTONE = ROOT / "reports/tkm_encounter_sequence_curated_review_milestone_v1_latest.json"
GPU_INTERPRET = ROOT / "reports/tkm_encounter_sequence_gpu_interpret_observation_v1_latest.json"
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
    return {
        "gate_ok": doc.get("gate_ok") is True,
        "status": doc.get(f"tkm_encounter_sequence_{key}_status"),
    }


def build() -> dict[str, Any]:
    gates = {k: _gate_status(k) for k in GATE_KEYS}
    all_gates_ok = all(g.get("gate_ok") for g in gates.values())
    base = _load(BASE_BUNDLE)
    extension = _load(EXTENSION_CLOSURE)
    milestone = _load(MILESTONE)
    gpu_obs = _load(GPU_INTERPRET)
    weekly = _load(WEEKLY)
    ops = _load(OPS)
    snap = base.get("rollup_snapshot") if isinstance(base.get("rollup_snapshot"), dict) else {}
    counts = milestone.get("curated_review_counts") if isinstance(milestone.get("curated_review_counts"), dict) else {}

    base_rollups_ok = (
        base.get("export_bundle_ok") is True
        and snap.get("lens_stack_rollup_ok") is True
        and snap.get("passive_integrated_ok") is True
        and snap.get("clinical_validation_stub_ok") is True
    )
    extension_rollups_ok = (
        extension.get("extension_closure_ok") is True
        and milestone.get("milestone_ok") is True
        and gpu_obs.get("observation_ok") is True
    )

    extended_export_bundle_ok = (
        all_gates_ok
        and base_rollups_ok
        and extension_rollups_ok
        and weekly.get("weekly_ok") is True
        and ops.get("closure_ok") is True
        and int(counts.get("reviewed") or 0) >= int(milestone.get("milestone_reviewed_min") or 6)
    )

    return {
        "schema": "tkm_encounter_sequence_extended_stack_export_bundle_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "domain_lane": "tkm_korean_han_medicine",
        "send_gate": "HOLD",
        "non_gating": True,
        "research_only": True,
        "extended_export_bundle_ok": extended_export_bundle_ok,
        "gates": gates,
        "gates_ok_count": sum(1 for g in gates.values() if g.get("gate_ok") is True),
        "base_export_bundle_ok": base.get("export_bundle_ok"),
        "extension_closure_ok": extension.get("extension_closure_ok"),
        "rollup_snapshot": {
            **snap,
            "curated_milestone_ok": milestone.get("milestone_ok"),
            "gpu_interpret_observation_ok": gpu_obs.get("observation_ok"),
            "interpret_gpu_train_attempted": gpu_obs.get("interpret_gpu_train_attempted"),
            "curated_reviewed_count": counts.get("reviewed"),
            "curated_pending_human_review": counts.get("pending_human_review"),
            "stack_final_closure_ok": extension.get("stack_final_closure_ok"),
        },
        "weekly_report_version": weekly.get("version"),
        "ops_closure_version": ops.get("version"),
        "ops_closure_ok": ops.get("closure_ok"),
        "lens_order_ko": "Field(L4) → L5 → L6 → L7 → conflict → disagreement → P44 closure → P45 curated → P46 interpret → P47 extension → P48 export",
        "artifact_refs": {
            "base_export_bundle": str(BASE_BUNDLE).replace("\\", "/"),
            "stack_extension_closure": str(EXTENSION_CLOSURE).replace("\\", "/"),
            "curated_review_milestone": str(MILESTONE).replace("\\", "/"),
            "gpu_interpret_observation": str(GPU_INTERPRET).replace("\\", "/"),
            "weekly_report": str(WEEKLY).replace("\\", "/"),
        },
        "note_ko": "P33–P47 extended export bundle [HYPO][NON_GATING]; NotebookLM/ops 참고용; Track A 합선 금지.",
        "reproduce": "py scripts/build_tkm_encounter_sequence_extended_stack_export_bundle_v1.py",
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
    print(json.dumps({"ok": doc.get("extended_export_bundle_ok"), "gates": doc.get("gates_ok_count")}))
    return 0 if doc.get("extended_export_bundle_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
