#!/usr/bin/env python3
"""Build TKM encounter_sequence post-P64 ultra-grand vault passive observability rollup [HYPO]."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/tkm_encounter_sequence_post_ultra_grand_passive_observation_v1_latest.json"
ARTIFACT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_post_ultra_grand_passive_observation_v1_latest.json"

P64_GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p64_gate_v1_latest.json"
ULTRA_VAULT_SYNC = ROOT / "reports/tkm_encounter_sequence_ultra_grand_export_bundle_vault_sync_v1_latest.json"
ULTRA_CLOSURE = ROOT / "reports/tkm_encounter_sequence_ultra_grand_post_export_closure_v1_latest.json"
PASSIVE = ROOT / "reports/tkm_encounter_sequence_passive_observation_v1_latest.json"
EXPORT_INGEST = ROOT / "reports/tkm_encounter_sequence_export_ingest_kpi_v1_latest.json"
MILESTONE = ROOT / "reports/tkm_encounter_sequence_curated_review_milestone_v1_latest.json"
INTERPRET = ROOT / "reports/myeongri_interpret_micro_retrain_chain_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build() -> dict[str, Any]:
    p64 = _load(P64_GATE)
    ultra_vault = _load(ULTRA_VAULT_SYNC)
    ultra = _load(ULTRA_CLOSURE)
    passive = _load(PASSIVE)
    export_ingest = _load(EXPORT_INGEST)
    milestone = _load(MILESTONE)
    interpret = _load(INTERPRET)
    counts = milestone.get("curated_review_counts") if isinstance(milestone.get("curated_review_counts"), dict) else {}

    interpret_cpu_ok = interpret.get("cpu_guard_ok") is True or not INTERPRET.is_file()
    interpret_gpu_attempted = interpret.get("gpu_train_attempted") is True
    interpret_gpu_ok = interpret.get("gpu_train_ok") if interpret_gpu_attempted else None
    gpu_obs_ok = interpret_gpu_ok is True if interpret_gpu_attempted else interpret_cpu_ok

    reviewed = int(counts.get("reviewed") or 0)
    pending = int(counts.get("pending_human_review") or 0)
    milestone_min = int(milestone.get("milestone_reviewed_min") or 6)
    vault = ultra_vault.get("vault_mirror") if isinstance(ultra_vault.get("vault_mirror"), dict) else {}

    observation_ok = (
        p64.get("gate_ok") is True
        and ultra_vault.get("ultra_grand_export_bundle_vault_sync_ok") is True
        and ultra.get("ultra_grand_post_export_closure_ok") is True
        and passive.get("observation_ok") is True
        and export_ingest.get("kpi_ok") is True
        and milestone.get("milestone_ok") is True
        and reviewed >= milestone_min
        and interpret_cpu_ok
        and gpu_obs_ok
        and passive.get("weekly_task_ready") is True
        and ultra_vault.get("cloud_upload_forbidden") is True
        and vault.get("vault_mirror_ok") is True
    )

    return {
        "schema": "tkm_encounter_sequence_post_ultra_grand_passive_observation_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "domain_lane": "tkm_korean_han_medicine",
        "send_gate": "HOLD",
        "non_gating": True,
        "research_only": True,
        "observation_ok": observation_ok,
        "p64_gate_ok": p64.get("gate_ok"),
        "ultra_grand_export_bundle_vault_sync_ok": ultra_vault.get("ultra_grand_export_bundle_vault_sync_ok"),
        "ultra_grand_post_export_closure_ok": ultra.get("ultra_grand_post_export_closure_ok"),
        "passive_observation_ok": passive.get("observation_ok"),
        "weekly_task_ready": passive.get("weekly_task_ready"),
        "export_ingest_kpi_ok": export_ingest.get("kpi_ok"),
        "export_ingest_live_ok": export_ingest.get("live_ingest_ok"),
        "curated_milestone_ok": milestone.get("milestone_ok"),
        "curated_reviewed_count": reviewed,
        "curated_pending_human_review": pending,
        "milestone_reviewed_min": milestone_min,
        "interpret_cpu_guard_ok": interpret_cpu_ok,
        "interpret_gpu_train_attempted": interpret_gpu_attempted,
        "interpret_gpu_train_ok": interpret_gpu_ok,
        "manifest_files_present_count": ultra_vault.get("manifest_files_present_count"),
        "gates_ok_count": ultra.get("gates_ok_count"),
        "auto_training_forbidden": True,
        "note_ko": "P65 post-ultra-grand passive+vault observability [HYPO][NON_GATING]; auto-training·Track A 금지.",
        "reproduce": "py scripts/build_tkm_encounter_sequence_post_ultra_grand_passive_observation_v1.py",
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
    print(
        json.dumps(
            {
                "ok": doc.get("observation_ok"),
                "ultra_vault_sync": doc.get("ultra_grand_export_bundle_vault_sync_ok"),
                "curated_reviewed": doc.get("curated_reviewed_count"),
                "pending": doc.get("curated_pending_human_review"),
            }
        )
    )
    return 0 if doc.get("observation_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
