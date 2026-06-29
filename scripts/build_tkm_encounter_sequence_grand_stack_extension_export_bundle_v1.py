#!/usr/bin/env python3
"""Build TKM encounter_sequence grand-stack extension export bundle (P33–P60) [HYPO]."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/tkm_encounter_sequence_grand_stack_extension_export_bundle_v1_latest.json"
ARTIFACT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_grand_stack_extension_export_bundle_v1_latest.json"

GATE_KEYS = tuple(f"p{n}" for n in range(33, 61))
GATE_PATHS = {k: ROOT / f"docs/final/artifacts/tkm_encounter_sequence_{k}_gate_v1_latest.json" for k in GATE_KEYS}

POST_EXPORT_EXTENDED = ROOT / "reports/tkm_encounter_sequence_post_export_extended_export_bundle_v1_latest.json"
FULL_GRAND_CLOSURE = ROOT / "reports/tkm_encounter_sequence_full_grand_stack_final_closure_v1_latest.json"
GRAND_VAULT_SYNC = ROOT / "reports/tkm_encounter_sequence_grand_export_bundle_vault_sync_v1_latest.json"
POST_GRAND_OBS = ROOT / "reports/tkm_encounter_sequence_post_grand_passive_observation_v1_latest.json"
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
    post_export_ext = _load(POST_EXPORT_EXTENDED)
    full_grand = _load(FULL_GRAND_CLOSURE)
    grand_vault = _load(GRAND_VAULT_SYNC)
    post_grand = _load(POST_GRAND_OBS)
    weekly = _load(WEEKLY)
    ops = _load(OPS)
    snap = post_export_ext.get("rollup_snapshot") if isinstance(post_export_ext.get("rollup_snapshot"), dict) else {}

    base_rollups_ok = (
        post_export_ext.get("post_export_extended_export_bundle_ok") is True
        and post_export_ext.get("extended_export_bundle_ok") is True
        and snap.get("lens_stack_rollup_ok") is True
        and snap.get("passive_integrated_ok") is True
        and snap.get("clinical_validation_stub_ok") is True
        and snap.get("curated_milestone_ok") is True
        and snap.get("export_sync_ok") is True
        and snap.get("post_export_observation_ok") is True
    )
    grand_rollups_ok = (
        full_grand.get("full_grand_stack_final_closure_ok") is True
        and full_grand.get("grand_post_export_closure_ok") is True
        and grand_vault.get("grand_export_bundle_vault_sync_ok") is True
        and post_grand.get("observation_ok") is True
        and grand_vault.get("cloud_upload_forbidden") is True
    )

    grand_stack_extension_export_bundle_ok = (
        all_gates_ok
        and base_rollups_ok
        and grand_rollups_ok
        and weekly.get("weekly_ok") is True
        and ops.get("closure_ok") is True
        and int(full_grand.get("curated_reviewed_count") or 0) >= 6
    )

    return {
        "schema": "tkm_encounter_sequence_grand_stack_extension_export_bundle_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "domain_lane": "tkm_korean_han_medicine",
        "send_gate": "HOLD",
        "non_gating": True,
        "research_only": True,
        "grand_stack_extension_export_bundle_ok": grand_stack_extension_export_bundle_ok,
        "gates": gates,
        "gates_ok_count": sum(1 for g in gates.values() if g.get("gate_ok") is True),
        "post_export_extended_export_bundle_ok": post_export_ext.get("post_export_extended_export_bundle_ok"),
        "full_grand_stack_final_closure_ok": full_grand.get("full_grand_stack_final_closure_ok"),
        "rollup_snapshot": {
            **snap,
            "grand_post_export_closure_ok": full_grand.get("grand_post_export_closure_ok"),
            "grand_export_bundle_vault_sync_ok": grand_vault.get("grand_export_bundle_vault_sync_ok"),
            "post_grand_passive_observation_ok": post_grand.get("observation_ok"),
            "full_grand_stack_final_closure_ok": full_grand.get("full_grand_stack_final_closure_ok"),
            "manifest_files_present_count": grand_vault.get("manifest_files_present_count"),
            "cloud_upload_forbidden": grand_vault.get("cloud_upload_forbidden"),
            "interpret_gpu_train_attempted": post_grand.get("interpret_gpu_train_attempted"),
            "curated_reviewed_count": full_grand.get("curated_reviewed_count"),
            "curated_pending_human_review": full_grand.get("curated_pending_human_review"),
        },
        "weekly_report_version": weekly.get("version"),
        "ops_closure_version": ops.get("version"),
        "ops_closure_ok": ops.get("closure_ok"),
        "lens_order_ko": "P33–P60 grand-stack extension export — post-export + grand vault + post-grand obs + P60 closure",
        "artifact_refs": {
            "post_export_extended_export_bundle": str(POST_EXPORT_EXTENDED).replace("\\", "/"),
            "full_grand_stack_final_closure": str(FULL_GRAND_CLOSURE).replace("\\", "/"),
            "grand_export_bundle_vault_sync": str(GRAND_VAULT_SYNC).replace("\\", "/"),
            "post_grand_passive_observation": str(POST_GRAND_OBS).replace("\\", "/"),
            "weekly_report": str(WEEKLY).replace("\\", "/"),
        },
        "note_ko": "P33–P60 grand-stack extension export bundle [HYPO][NON_GATING]; NotebookLM/ops 참고용; Track A 합선 금지.",
        "reproduce": "py scripts/build_tkm_encounter_sequence_grand_stack_extension_export_bundle_v1.py",
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
    print(json.dumps({"ok": doc.get("grand_stack_extension_export_bundle_ok"), "gates": doc.get("gates_ok_count")}))
    return 0 if doc.get("grand_stack_extension_export_bundle_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
