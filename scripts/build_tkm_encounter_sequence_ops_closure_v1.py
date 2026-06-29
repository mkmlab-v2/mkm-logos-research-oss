#!/usr/bin/env python3
"""Build TKM encounter_sequence ops closure status (items 1–8) [HYPO]."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
OUT = ROOT / "reports/tkm_encounter_sequence_ops_closure_v1_latest.json"
HTTP_ALERTS = ROOT / "reports/tkm_encounter_sequence_http_smoke_alerts_v1.jsonl"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _task_registered(name: str) -> bool:
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-Command", f"(Get-ScheduledTask -TaskName '{name}' -ErrorAction SilentlyContinue) -ne $null"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0 and (proc.stdout or "").strip().lower() == "true"


def build() -> dict[str, Any]:
    daily = _load(ROOT / "reports/tkm_physician_gold_daily_capture_v1_latest.json")
    human_ack = _load(ROOT / "reports/encounter_sequence_curated_learning_ack_v1_latest.json")
    export = _load(ROOT / "reports/tkm_physician_gold_capture_export_ingest_v1_latest.json")
    export_kpi = _load(ROOT / "reports/tkm_encounter_sequence_export_ingest_kpi_v1_latest.json")
    p38 = _load(ROOT / "docs/final/artifacts/tkm_encounter_sequence_p38_gate_v1_latest.json")
    p36 = _load(ROOT / "docs/final/artifacts/tkm_encounter_sequence_p36_gate_v1_latest.json")
    p35 = _load(ROOT / "docs/final/artifacts/tkm_encounter_sequence_p35_gate_v1_latest.json")
    p34 = _load(ROOT / "docs/final/artifacts/tkm_encounter_sequence_p34_gate_v1_latest.json")
    p33 = _load(ROOT / "docs/final/artifacts/tkm_encounter_sequence_p33_gate_v1_latest.json")
    rollup = _load(ROOT / "reports/tkm_encounter_sequence_lens_stack_rollup_v1_latest.json")
    rollup_artifact = ROOT / "docs/final/artifacts/tkm_encounter_sequence_lens_stack_rollup_v1_latest.json"
    passive_integrated = _load(ROOT / "reports/tkm_encounter_sequence_passive_integrated_rollup_v1_latest.json")
    passive_integrated_artifact = ROOT / "docs/final/artifacts/tkm_encounter_sequence_passive_integrated_rollup_v1_latest.json"
    clinical_stub = _load(ROOT / "reports/tkm_encounter_sequence_clinical_validation_stub_v1_latest.json")
    clinical_stub_artifact = ROOT / "docs/final/artifacts/tkm_encounter_sequence_clinical_validation_stub_v1_latest.json"
    full_stack_bundle = _load(ROOT / "reports/tkm_encounter_sequence_full_stack_export_bundle_v1_latest.json")
    full_stack_bundle_artifact = ROOT / "docs/final/artifacts/tkm_encounter_sequence_full_stack_export_bundle_v1_latest.json"
    p43_observability = _load(ROOT / "reports/tkm_encounter_sequence_p43_observability_rollup_v1_latest.json")
    p43_observability_artifact = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p43_observability_rollup_v1_latest.json"
    stack_final_closure = _load(ROOT / "reports/tkm_encounter_sequence_stack_final_closure_v1_latest.json")
    stack_final_closure_artifact = ROOT / "docs/final/artifacts/tkm_encounter_sequence_stack_final_closure_v1_latest.json"
    curated_milestone = _load(ROOT / "reports/tkm_encounter_sequence_curated_review_milestone_v1_latest.json")
    curated_milestone_artifact = ROOT / "docs/final/artifacts/tkm_encounter_sequence_curated_review_milestone_v1_latest.json"
    gpu_interpret_obs = _load(ROOT / "reports/tkm_encounter_sequence_gpu_interpret_observation_v1_latest.json")
    gpu_interpret_obs_artifact = ROOT / "docs/final/artifacts/tkm_encounter_sequence_gpu_interpret_observation_v1_latest.json"
    stack_extension_closure = _load(ROOT / "reports/tkm_encounter_sequence_stack_extension_closure_v1_latest.json")
    stack_extension_closure_artifact = ROOT / "docs/final/artifacts/tkm_encounter_sequence_stack_extension_closure_v1_latest.json"
    extended_export_bundle = _load(ROOT / "reports/tkm_encounter_sequence_extended_stack_export_bundle_v1_latest.json")
    extended_export_bundle_artifact = ROOT / "docs/final/artifacts/tkm_encounter_sequence_extended_stack_export_bundle_v1_latest.json"
    full_extension_closure = _load(ROOT / "reports/tkm_encounter_sequence_full_extension_closure_v1_latest.json")
    full_extension_closure_artifact = ROOT / "docs/final/artifacts/tkm_encounter_sequence_full_extension_closure_v1_latest.json"
    post_extension_obs = _load(ROOT / "reports/tkm_encounter_sequence_post_extension_observation_v1_latest.json")
    post_extension_obs_artifact = ROOT / "docs/final/artifacts/tkm_encounter_sequence_post_extension_observation_v1_latest.json"
    integrated_stack_closure = _load(ROOT / "reports/tkm_encounter_sequence_integrated_stack_closure_v1_latest.json")
    integrated_stack_closure_artifact = ROOT / "docs/final/artifacts/tkm_encounter_sequence_integrated_stack_closure_v1_latest.json"
    notebooklm_export_sync = _load(ROOT / "reports/tkm_encounter_sequence_notebooklm_export_sync_v1_latest.json")
    notebooklm_export_sync_artifact = ROOT / "docs/final/artifacts/tkm_encounter_sequence_notebooklm_export_sync_v1_latest.json"
    post_export_passive_obs = _load(ROOT / "reports/tkm_encounter_sequence_post_export_passive_observation_v1_latest.json")
    post_export_passive_obs_artifact = ROOT / "docs/final/artifacts/tkm_encounter_sequence_post_export_passive_observation_v1_latest.json"
    full_post_export_closure = _load(ROOT / "reports/tkm_encounter_sequence_full_post_export_closure_v1_latest.json")
    full_post_export_closure_artifact = ROOT / "docs/final/artifacts/tkm_encounter_sequence_full_post_export_closure_v1_latest.json"
    post_export_extended_bundle = _load(ROOT / "reports/tkm_encounter_sequence_post_export_extended_export_bundle_v1_latest.json")
    post_export_extended_bundle_artifact = ROOT / "docs/final/artifacts/tkm_encounter_sequence_post_export_extended_export_bundle_v1_latest.json"
    post_export_stack_closure = _load(ROOT / "reports/tkm_encounter_sequence_post_export_stack_closure_v1_latest.json")
    post_export_stack_closure_artifact = ROOT / "docs/final/artifacts/tkm_encounter_sequence_post_export_stack_closure_v1_latest.json"
    grand_post_export_closure = _load(ROOT / "reports/tkm_encounter_sequence_grand_post_export_closure_v1_latest.json")
    grand_post_export_closure_artifact = ROOT / "docs/final/artifacts/tkm_encounter_sequence_grand_post_export_closure_v1_latest.json"
    grand_export_bundle_vault_sync = _load(ROOT / "reports/tkm_encounter_sequence_grand_export_bundle_vault_sync_v1_latest.json")
    grand_export_bundle_vault_sync_artifact = ROOT / "docs/final/artifacts/tkm_encounter_sequence_grand_export_bundle_vault_sync_v1_latest.json"
    post_grand_passive_obs = _load(ROOT / "reports/tkm_encounter_sequence_post_grand_passive_observation_v1_latest.json")
    post_grand_passive_obs_artifact = ROOT / "docs/final/artifacts/tkm_encounter_sequence_post_grand_passive_observation_v1_latest.json"
    full_grand_stack_final_closure = _load(ROOT / "reports/tkm_encounter_sequence_full_grand_stack_final_closure_v1_latest.json")
    full_grand_stack_final_closure_artifact = ROOT / "docs/final/artifacts/tkm_encounter_sequence_full_grand_stack_final_closure_v1_latest.json"
    grand_stack_extension_export_bundle = _load(ROOT / "reports/tkm_encounter_sequence_grand_stack_extension_export_bundle_v1_latest.json")
    grand_stack_extension_export_bundle_artifact = ROOT / "docs/final/artifacts/tkm_encounter_sequence_grand_stack_extension_export_bundle_v1_latest.json"
    grand_stack_stack_closure = _load(ROOT / "reports/tkm_encounter_sequence_grand_stack_stack_closure_v1_latest.json")
    grand_stack_stack_closure_artifact = ROOT / "docs/final/artifacts/tkm_encounter_sequence_grand_stack_stack_closure_v1_latest.json"
    ultra_grand_post_export_closure = _load(ROOT / "reports/tkm_encounter_sequence_ultra_grand_post_export_closure_v1_latest.json")
    ultra_grand_post_export_closure_artifact = ROOT / "docs/final/artifacts/tkm_encounter_sequence_ultra_grand_post_export_closure_v1_latest.json"
    ultra_grand_export_bundle_vault_sync = _load(ROOT / "reports/tkm_encounter_sequence_ultra_grand_export_bundle_vault_sync_v1_latest.json")
    ultra_grand_export_bundle_vault_sync_artifact = ROOT / "docs/final/artifacts/tkm_encounter_sequence_ultra_grand_export_bundle_vault_sync_v1_latest.json"
    post_ultra_grand_passive_obs = _load(ROOT / "reports/tkm_encounter_sequence_post_ultra_grand_passive_observation_v1_latest.json")
    post_ultra_grand_passive_obs_artifact = ROOT / "docs/final/artifacts/tkm_encounter_sequence_post_ultra_grand_passive_observation_v1_latest.json"
    full_ultra_grand_stack_final_closure = _load(ROOT / "reports/tkm_encounter_sequence_full_ultra_grand_stack_final_closure_v1_latest.json")
    full_ultra_grand_stack_final_closure_artifact = ROOT / "docs/final/artifacts/tkm_encounter_sequence_full_ultra_grand_stack_final_closure_v1_latest.json"
    ultra_grand_extension_export_bundle = _load(ROOT / "reports/tkm_encounter_sequence_ultra_grand_extension_export_bundle_v1_latest.json")
    ultra_grand_extension_export_bundle_artifact = ROOT / "docs/final/artifacts/tkm_encounter_sequence_ultra_grand_extension_export_bundle_v1_latest.json"
    ultra_grand_stack_stack_closure = _load(ROOT / "reports/tkm_encounter_sequence_ultra_grand_stack_stack_closure_v1_latest.json")
    ultra_grand_stack_stack_closure_artifact = ROOT / "docs/final/artifacts/tkm_encounter_sequence_ultra_grand_stack_stack_closure_v1_latest.json"
    post_breakpoint_passive_drift = _load(ROOT / "reports/tkm_encounter_sequence_post_breakpoint_passive_drift_observation_v1_latest.json")
    post_breakpoint_passive_drift_artifact = ROOT / "docs/final/artifacts/tkm_encounter_sequence_post_breakpoint_passive_drift_observation_v1_latest.json"
    curated_bulk_human_review = _load(ROOT / "reports/tkm_encounter_sequence_curated_bulk_human_review_v1_latest.json")
    curated_bulk_human_review_artifact = ROOT / "docs/final/artifacts/tkm_encounter_sequence_curated_bulk_human_review_v1_latest.json"
    http_smoke = _load(ROOT / "reports/no1kmedi_encounter_sequence_api_http_smoke_v1_latest.json")
    disagreement_cross = _load(ROOT / "reports/tkm_encounter_sequence_disagreement_resolver_cross_kpi_v1_latest.json")

    fact_lock_smoke = _load(ROOT / "reports/tkm_encounter_sequence_fact_lock_smoke_v1_latest.json")
    fact_lock_has_flag = "SkipTkmEncounterSequenceSmoke" in (
        (ROOT / "scripts/run_fact_lock_bundle.ps1").read_text(encoding="utf-8")
    )

    items = {
        "1_daily_capture": {
            "ok": daily.get("ok") is True,
            "ref": str(ROOT / "scripts/run_tkm_physician_gold_daily_capture_v1.py").replace("\\", "/"),
        },
        "2_curated_learning_ack": {
            "ok": human_ack.get("ok") is True and human_ack.get("mode") == "human",
            "ref": str(ROOT / "scripts/run_encounter_sequence_curated_learning_ack_v1.py").replace("\\", "/"),
        },
        "3_fact_lock_bundle": {
            "ok": fact_lock_has_flag and fact_lock_smoke.get("ok") is True,
            "skip_flag": "SkipTkmEncounterSequenceSmoke",
            "smoke_ok": fact_lock_smoke.get("ok"),
        },
        "4_weekly_scheduler": {
            "ok": _task_registered("MKM-TkmEncounterSequence-Weekly"),
            "task_name": "MKM-TkmEncounterSequence-Weekly",
            "chain_ref": "scripts/run_tkm_encounter_sequence_post_p68_maintenance_chain_v1.py",
        },
        "5_http_smoke_alerts": {
            "ok": http_smoke.get("http_smoke_ok") is True or http_smoke.get("skipped") is True,
            "log": str(HTTP_ALERTS).replace("\\", "/"),
        },
        "6_export_ingest": {
            "ok": export.get("ok") is True and export_kpi.get("kpi_ok") is True,
            "ref": str(ROOT / "scripts/run_tkm_physician_gold_capture_export_ingest_v1.py").replace("\\", "/"),
            "live_ingest_ok": export_kpi.get("live_ingest_ok"),
            "lens_stack_ok": export_kpi.get("lens_stack_ok"),
        },
        "7_disagreement_resolver_cross": {
            "ok": disagreement_cross.get("kpi_ok") is True,
            "ref": str(ROOT / "scripts/build_tkm_encounter_sequence_disagreement_resolver_cross_kpi_v1.py").replace("\\", "/"),
            "disagreement_count": disagreement_cross.get("disagreement_count"),
        },
        "8_mission_log_routine": {
            "ok": (ROOT / "MISSION_LOG.md").is_file(),
            "routine": "physician_gold 1/day: run_tkm_physician_gold_daily_capture_v1.py",
        },
        "9_cross_lens_p33": {
            "ok": p33.get("gate_ok") is True,
            "status": p33.get("tkm_encounter_sequence_p33_status"),
        },
        "10_passive_observation_p34": {
            "ok": p34.get("gate_ok") is True,
            "status": p34.get("tkm_encounter_sequence_p34_status"),
        },
        "11_conflict_resolver_p35": {
            "ok": p35.get("gate_ok") is True,
            "status": p35.get("tkm_encounter_sequence_p35_status"),
        },
        "12_disagreement_cross_p36": {
            "ok": p36.get("gate_ok") is True,
            "status": p36.get("tkm_encounter_sequence_p36_status"),
        },
        "13_lens_stack_rollup_p39": {
            "ok": rollup.get("rollup_ok") is True and rollup_artifact.is_file(),
            "status": "lens_stack_rollup_wire_ok" if rollup.get("rollup_ok") is True else "incomplete",
            "rollup_artifact": str(ROOT / "docs/final/artifacts/tkm_encounter_sequence_lens_stack_rollup_v1_latest.json").replace("\\", "/"),
            "p38_status": p38.get("tkm_encounter_sequence_p38_status"),
        },
        "14_passive_integrated_p40": {
            "ok": passive_integrated.get("integrated_ok") is True and passive_integrated_artifact.is_file(),
            "status": "passive_integrated_observation_wire_ok" if passive_integrated.get("integrated_ok") is True else "incomplete",
            "rollup_artifact": str(passive_integrated_artifact).replace("\\", "/"),
            "interpret_gpu_train_attempted": passive_integrated.get("interpret_gpu_train_attempted"),
        },
        "15_clinical_validation_p41": {
            "ok": clinical_stub.get("validation_stub_ok") is True and clinical_stub_artifact.is_file(),
            "status": "clinical_validation_stub_wire_ok" if clinical_stub.get("validation_stub_ok") is True else "incomplete",
            "stub_artifact": str(clinical_stub_artifact).replace("\\", "/"),
            "physician_gold_sequence_count": clinical_stub.get("physician_gold_sequence_count"),
        },
        "16_full_stack_export_p42": {
            "ok": full_stack_bundle.get("export_bundle_ok") is True and full_stack_bundle_artifact.is_file(),
            "status": "full_stack_export_bundle_wire_ok" if full_stack_bundle.get("export_bundle_ok") is True else "incomplete",
            "bundle_artifact": str(full_stack_bundle_artifact).replace("\\", "/"),
            "gates_ok_count": sum(
                1
                for g in (full_stack_bundle.get("gates") or {}).values()
                if isinstance(g, dict) and g.get("gate_ok") is True
            ),
        },
        "17_gpu_passive_curated_p43": {
            "ok": p43_observability.get("observability_ok") is True and p43_observability_artifact.is_file(),
            "status": "gpu_passive_curated_observation_wire_ok" if p43_observability.get("observability_ok") is True else "incomplete",
            "rollup_artifact": str(p43_observability_artifact).replace("\\", "/"),
            "curated_reviewed_count": (p43_observability.get("curated_review_counts") or {}).get("reviewed"),
            "interpret_gpu_train_attempted": p43_observability.get("interpret_gpu_train_attempted"),
        },
        "18_stack_final_closure_p44": {
            "ok": stack_final_closure.get("final_closure_ok") is True and stack_final_closure_artifact.is_file(),
            "status": "stack_final_closure_wire_ok" if stack_final_closure.get("final_closure_ok") is True else "incomplete",
            "closure_artifact": str(stack_final_closure_artifact).replace("\\", "/"),
            "gates_ok_count": stack_final_closure.get("gates_ok_count"),
        },
        "19_curated_milestone_p45": {
            "ok": curated_milestone.get("milestone_ok") is True and curated_milestone_artifact.is_file(),
            "status": "curated_human_review_milestone_wire_ok" if curated_milestone.get("milestone_ok") is True else "incomplete",
            "milestone_artifact": str(curated_milestone_artifact).replace("\\", "/"),
            "curated_reviewed_count": (curated_milestone.get("curated_review_counts") or {}).get("reviewed"),
            "curated_pending_human_review": (curated_milestone.get("curated_review_counts") or {}).get("pending_human_review"),
        },
        "20_gpu_interpret_observation_p46": {
            "ok": gpu_interpret_obs.get("observation_ok") is True and gpu_interpret_obs_artifact.is_file(),
            "status": "gpu_interpret_observation_wire_ok" if gpu_interpret_obs.get("observation_ok") is True else "incomplete",
            "observation_artifact": str(gpu_interpret_obs_artifact).replace("\\", "/"),
            "interpret_gpu_train_attempted": gpu_interpret_obs.get("interpret_gpu_train_attempted"),
            "interpret_gpu_train_ok": gpu_interpret_obs.get("interpret_gpu_train_ok"),
        },
        "21_stack_extension_closure_p47": {
            "ok": stack_extension_closure.get("extension_closure_ok") is True and stack_extension_closure_artifact.is_file(),
            "status": "stack_extension_closure_wire_ok" if stack_extension_closure.get("extension_closure_ok") is True else "incomplete",
            "closure_artifact": str(stack_extension_closure_artifact).replace("\\", "/"),
            "gates_ok_count": stack_extension_closure.get("gates_ok_count"),
        },
        "22_extended_export_bundle_p48": {
            "ok": extended_export_bundle.get("extended_export_bundle_ok") is True and extended_export_bundle_artifact.is_file(),
            "status": "extended_stack_export_bundle_wire_ok" if extended_export_bundle.get("extended_export_bundle_ok") is True else "incomplete",
            "bundle_artifact": str(extended_export_bundle_artifact).replace("\\", "/"),
            "gates_ok_count": extended_export_bundle.get("gates_ok_count"),
        },
        "23_full_extension_closure_p49": {
            "ok": full_extension_closure.get("full_extension_closure_ok") is True and full_extension_closure_artifact.is_file(),
            "status": "full_extension_closure_wire_ok" if full_extension_closure.get("full_extension_closure_ok") is True else "incomplete",
            "closure_artifact": str(full_extension_closure_artifact).replace("\\", "/"),
            "gates_ok_count": full_extension_closure.get("gates_ok_count"),
        },
        "24_post_extension_observation_p50": {
            "ok": post_extension_obs.get("observation_ok") is True and post_extension_obs_artifact.is_file(),
            "status": "post_extension_passive_observation_wire_ok" if post_extension_obs.get("observation_ok") is True else "incomplete",
            "observation_artifact": str(post_extension_obs_artifact).replace("\\", "/"),
            "weekly_task_ready": post_extension_obs.get("weekly_task_ready"),
            "export_ingest_kpi_ok": post_extension_obs.get("export_ingest_kpi_ok"),
        },
        "25_integrated_stack_closure_p51": {
            "ok": integrated_stack_closure.get("integrated_closure_ok") is True and integrated_stack_closure_artifact.is_file(),
            "status": "integrated_stack_closure_wire_ok" if integrated_stack_closure.get("integrated_closure_ok") is True else "incomplete",
            "closure_artifact": str(integrated_stack_closure_artifact).replace("\\", "/"),
            "gates_ok_count": integrated_stack_closure.get("gates_ok_count"),
            "full_extension_closure_ok": integrated_stack_closure.get("full_extension_closure_ok"),
            "post_extension_observation_ok": integrated_stack_closure.get("post_extension_observation_ok"),
        },
        "26_notebooklm_export_sync_p52": {
            "ok": notebooklm_export_sync.get("export_sync_ok") is True and notebooklm_export_sync_artifact.is_file(),
            "status": "notebooklm_export_sync_wire_ok" if notebooklm_export_sync.get("export_sync_ok") is True else "incomplete",
            "sync_artifact": str(notebooklm_export_sync_artifact).replace("\\", "/"),
            "manifest_files_present_count": notebooklm_export_sync.get("manifest_files_present_count"),
            "cloud_upload_forbidden": notebooklm_export_sync.get("cloud_upload_forbidden"),
            "vault_mirror_skipped": (notebooklm_export_sync.get("vault_mirror") or {}).get("vault_mirror_skipped"),
        },
        "27_post_export_passive_observation_p53": {
            "ok": post_export_passive_obs.get("observation_ok") is True and post_export_passive_obs_artifact.is_file(),
            "status": "post_export_passive_observation_wire_ok" if post_export_passive_obs.get("observation_ok") is True else "incomplete",
            "observation_artifact": str(post_export_passive_obs_artifact).replace("\\", "/"),
            "export_sync_ok": post_export_passive_obs.get("export_sync_ok"),
            "curated_reviewed_count": post_export_passive_obs.get("curated_reviewed_count"),
            "curated_pending_human_review": post_export_passive_obs.get("curated_pending_human_review"),
            "weekly_task_ready": post_export_passive_obs.get("weekly_task_ready"),
        },
        "28_full_post_export_closure_p54": {
            "ok": full_post_export_closure.get("full_post_export_closure_ok") is True and full_post_export_closure_artifact.is_file(),
            "status": "full_post_export_closure_wire_ok" if full_post_export_closure.get("full_post_export_closure_ok") is True else "incomplete",
            "closure_artifact": str(full_post_export_closure_artifact).replace("\\", "/"),
            "gates_ok_count": full_post_export_closure.get("gates_ok_count"),
            "export_sync_ok": full_post_export_closure.get("export_sync_ok"),
            "post_export_observation_ok": full_post_export_closure.get("post_export_observation_ok"),
        },
        "29_post_export_extended_export_bundle_p55": {
            "ok": post_export_extended_bundle.get("post_export_extended_export_bundle_ok") is True and post_export_extended_bundle_artifact.is_file(),
            "status": "post_export_extended_export_bundle_wire_ok" if post_export_extended_bundle.get("post_export_extended_export_bundle_ok") is True else "incomplete",
            "bundle_artifact": str(post_export_extended_bundle_artifact).replace("\\", "/"),
            "gates_ok_count": post_export_extended_bundle.get("gates_ok_count"),
            "extended_export_bundle_ok": post_export_extended_bundle.get("extended_export_bundle_ok"),
            "full_post_export_closure_ok": post_export_extended_bundle.get("full_post_export_closure_ok"),
        },
        "30_post_export_stack_closure_p56": {
            "ok": post_export_stack_closure.get("post_export_stack_closure_ok") is True and post_export_stack_closure_artifact.is_file(),
            "status": "post_export_stack_closure_wire_ok" if post_export_stack_closure.get("post_export_stack_closure_ok") is True else "incomplete",
            "closure_artifact": str(post_export_stack_closure_artifact).replace("\\", "/"),
            "gates_ok_count": post_export_stack_closure.get("gates_ok_count"),
            "export_sync_ok": post_export_stack_closure.get("export_sync_ok"),
            "post_export_extended_export_bundle_ok": post_export_stack_closure.get("post_export_extended_export_bundle_ok"),
        },
        "31_grand_post_export_closure_p57": {
            "ok": grand_post_export_closure.get("grand_post_export_closure_ok") is True and grand_post_export_closure_artifact.is_file(),
            "status": "grand_post_export_closure_wire_ok" if grand_post_export_closure.get("grand_post_export_closure_ok") is True else "incomplete",
            "closure_artifact": str(grand_post_export_closure_artifact).replace("\\", "/"),
            "gates_ok_count": grand_post_export_closure.get("gates_ok_count"),
            "post_export_stack_closure_ok": grand_post_export_closure.get("post_export_stack_closure_ok"),
            "full_extension_closure_ok": grand_post_export_closure.get("full_extension_closure_ok"),
        },
        "32_grand_export_bundle_vault_sync_p58": {
            "ok": grand_export_bundle_vault_sync.get("grand_export_bundle_vault_sync_ok") is True and grand_export_bundle_vault_sync_artifact.is_file(),
            "status": "grand_export_bundle_vault_sync_wire_ok" if grand_export_bundle_vault_sync.get("grand_export_bundle_vault_sync_ok") is True else "incomplete",
            "sync_artifact": str(grand_export_bundle_vault_sync_artifact).replace("\\", "/"),
            "manifest_files_present_count": grand_export_bundle_vault_sync.get("manifest_files_present_count"),
            "base_export_sync_ok": grand_export_bundle_vault_sync.get("base_export_sync_ok"),
            "cloud_upload_forbidden": grand_export_bundle_vault_sync.get("cloud_upload_forbidden"),
            "vault_mirror_skipped": (grand_export_bundle_vault_sync.get("vault_mirror") or {}).get("vault_mirror_skipped"),
        },
        "33_post_grand_passive_observation_p59": {
            "ok": post_grand_passive_obs.get("observation_ok") is True and post_grand_passive_obs_artifact.is_file(),
            "status": "post_grand_passive_observation_wire_ok" if post_grand_passive_obs.get("observation_ok") is True else "incomplete",
            "observation_artifact": str(post_grand_passive_obs_artifact).replace("\\", "/"),
            "grand_export_bundle_vault_sync_ok": post_grand_passive_obs.get("grand_export_bundle_vault_sync_ok"),
            "curated_reviewed_count": post_grand_passive_obs.get("curated_reviewed_count"),
            "curated_pending_human_review": post_grand_passive_obs.get("curated_pending_human_review"),
            "weekly_task_ready": post_grand_passive_obs.get("weekly_task_ready"),
        },
        "34_full_grand_stack_final_closure_p60": {
            "ok": full_grand_stack_final_closure.get("full_grand_stack_final_closure_ok") is True and full_grand_stack_final_closure_artifact.is_file(),
            "status": "full_grand_stack_final_closure_wire_ok" if full_grand_stack_final_closure.get("full_grand_stack_final_closure_ok") is True else "incomplete",
            "closure_artifact": str(full_grand_stack_final_closure_artifact).replace("\\", "/"),
            "gates_ok_count": full_grand_stack_final_closure.get("gates_ok_count"),
            "grand_post_export_closure_ok": full_grand_stack_final_closure.get("grand_post_export_closure_ok"),
            "post_grand_passive_observation_ok": full_grand_stack_final_closure.get("post_grand_passive_observation_ok"),
            "curated_reviewed_count": full_grand_stack_final_closure.get("curated_reviewed_count"),
        },
        "35_grand_stack_extension_export_bundle_p61": {
            "ok": grand_stack_extension_export_bundle.get("grand_stack_extension_export_bundle_ok") is True and grand_stack_extension_export_bundle_artifact.is_file(),
            "status": "grand_stack_extension_export_bundle_wire_ok" if grand_stack_extension_export_bundle.get("grand_stack_extension_export_bundle_ok") is True else "incomplete",
            "bundle_artifact": str(grand_stack_extension_export_bundle_artifact).replace("\\", "/"),
            "gates_ok_count": grand_stack_extension_export_bundle.get("gates_ok_count"),
            "post_export_extended_export_bundle_ok": grand_stack_extension_export_bundle.get("post_export_extended_export_bundle_ok"),
            "full_grand_stack_final_closure_ok": grand_stack_extension_export_bundle.get("full_grand_stack_final_closure_ok"),
            "curated_reviewed_count": (grand_stack_extension_export_bundle.get("rollup_snapshot") or {}).get("curated_reviewed_count"),
        },
        "36_grand_stack_stack_closure_p62": {
            "ok": grand_stack_stack_closure.get("grand_stack_stack_closure_ok") is True and grand_stack_stack_closure_artifact.is_file(),
            "status": "grand_stack_stack_closure_wire_ok" if grand_stack_stack_closure.get("grand_stack_stack_closure_ok") is True else "incomplete",
            "closure_artifact": str(grand_stack_stack_closure_artifact).replace("\\", "/"),
            "gates_ok_count": grand_stack_stack_closure.get("gates_ok_count"),
            "grand_post_export_closure_ok": grand_stack_stack_closure.get("grand_post_export_closure_ok"),
            "grand_stack_extension_export_bundle_ok": grand_stack_stack_closure.get("grand_stack_extension_export_bundle_ok"),
            "curated_reviewed_count": grand_stack_stack_closure.get("curated_reviewed_count"),
        },
        "37_ultra_grand_post_export_closure_p63": {
            "ok": ultra_grand_post_export_closure.get("ultra_grand_post_export_closure_ok") is True and ultra_grand_post_export_closure_artifact.is_file(),
            "status": "ultra_grand_post_export_closure_wire_ok" if ultra_grand_post_export_closure.get("ultra_grand_post_export_closure_ok") is True else "incomplete",
            "closure_artifact": str(ultra_grand_post_export_closure_artifact).replace("\\", "/"),
            "gates_ok_count": ultra_grand_post_export_closure.get("gates_ok_count"),
            "grand_stack_stack_closure_ok": ultra_grand_post_export_closure.get("grand_stack_stack_closure_ok"),
            "full_grand_stack_final_closure_ok": ultra_grand_post_export_closure.get("full_grand_stack_final_closure_ok"),
            "curated_reviewed_count": ultra_grand_post_export_closure.get("curated_reviewed_count"),
        },
        "38_ultra_grand_export_bundle_vault_sync_p64": {
            "ok": ultra_grand_export_bundle_vault_sync.get("ultra_grand_export_bundle_vault_sync_ok") is True and ultra_grand_export_bundle_vault_sync_artifact.is_file(),
            "status": "ultra_grand_export_bundle_vault_sync_wire_ok" if ultra_grand_export_bundle_vault_sync.get("ultra_grand_export_bundle_vault_sync_ok") is True else "incomplete",
            "sync_artifact": str(ultra_grand_export_bundle_vault_sync_artifact).replace("\\", "/"),
            "manifest_files_present_count": ultra_grand_export_bundle_vault_sync.get("manifest_files_present_count"),
            "ultra_grand_post_export_closure_ok": ultra_grand_export_bundle_vault_sync.get("ultra_grand_post_export_closure_ok"),
            "grand_export_bundle_vault_sync_ok": ultra_grand_export_bundle_vault_sync.get("grand_export_bundle_vault_sync_ok"),
            "cloud_upload_forbidden": ultra_grand_export_bundle_vault_sync.get("cloud_upload_forbidden"),
            "vault_mirror_skipped": (ultra_grand_export_bundle_vault_sync.get("vault_mirror") or {}).get("vault_mirror_skipped"),
        },
        "39_post_ultra_grand_passive_observation_p65": {
            "ok": post_ultra_grand_passive_obs.get("observation_ok") is True and post_ultra_grand_passive_obs_artifact.is_file(),
            "status": "post_ultra_grand_passive_observation_wire_ok" if post_ultra_grand_passive_obs.get("observation_ok") is True else "incomplete",
            "observation_artifact": str(post_ultra_grand_passive_obs_artifact).replace("\\", "/"),
            "ultra_grand_export_bundle_vault_sync_ok": post_ultra_grand_passive_obs.get("ultra_grand_export_bundle_vault_sync_ok"),
            "curated_reviewed_count": post_ultra_grand_passive_obs.get("curated_reviewed_count"),
            "curated_pending_human_review": post_ultra_grand_passive_obs.get("curated_pending_human_review"),
            "weekly_task_ready": post_ultra_grand_passive_obs.get("weekly_task_ready"),
        },
        "40_full_ultra_grand_stack_final_closure_p66": {
            "ok": full_ultra_grand_stack_final_closure.get("full_ultra_grand_stack_final_closure_ok") is True and full_ultra_grand_stack_final_closure_artifact.is_file(),
            "status": "full_ultra_grand_stack_final_closure_wire_ok" if full_ultra_grand_stack_final_closure.get("full_ultra_grand_stack_final_closure_ok") is True else "incomplete",
            "closure_artifact": str(full_ultra_grand_stack_final_closure_artifact).replace("\\", "/"),
            "gates_ok_count": full_ultra_grand_stack_final_closure.get("gates_ok_count"),
            "ultra_grand_post_export_closure_ok": full_ultra_grand_stack_final_closure.get("ultra_grand_post_export_closure_ok"),
            "ultra_grand_export_bundle_vault_sync_ok": full_ultra_grand_stack_final_closure.get("ultra_grand_export_bundle_vault_sync_ok"),
            "post_ultra_grand_passive_observation_ok": full_ultra_grand_stack_final_closure.get("post_ultra_grand_passive_observation_ok"),
            "curated_reviewed_count": full_ultra_grand_stack_final_closure.get("curated_reviewed_count"),
        },
        "41_ultra_grand_extension_export_bundle_p67": {
            "ok": ultra_grand_extension_export_bundle.get("ultra_grand_extension_export_bundle_ok") is True and ultra_grand_extension_export_bundle_artifact.is_file(),
            "status": "ultra_grand_extension_export_bundle_wire_ok" if ultra_grand_extension_export_bundle.get("ultra_grand_extension_export_bundle_ok") is True else "incomplete",
            "bundle_artifact": str(ultra_grand_extension_export_bundle_artifact).replace("\\", "/"),
            "gates_ok_count": ultra_grand_extension_export_bundle.get("gates_ok_count"),
            "post_export_extended_export_bundle_ok": ultra_grand_extension_export_bundle.get("post_export_extended_export_bundle_ok"),
            "full_ultra_grand_stack_final_closure_ok": ultra_grand_extension_export_bundle.get("full_ultra_grand_stack_final_closure_ok"),
            "curated_reviewed_count": (ultra_grand_extension_export_bundle.get("rollup_snapshot") or {}).get("curated_reviewed_count"),
        },
        "42_ultra_grand_stack_stack_closure_p68": {
            "ok": ultra_grand_stack_stack_closure.get("ultra_grand_stack_stack_closure_ok") is True and ultra_grand_stack_stack_closure_artifact.is_file(),
            "status": "ultra_grand_stack_stack_closure_wire_ok" if ultra_grand_stack_stack_closure.get("ultra_grand_stack_stack_closure_ok") is True else "incomplete",
            "closure_artifact": str(ultra_grand_stack_stack_closure_artifact).replace("\\", "/"),
            "gates_ok_count": ultra_grand_stack_stack_closure.get("gates_ok_count"),
            "ultra_grand_post_export_closure_ok": ultra_grand_stack_stack_closure.get("ultra_grand_post_export_closure_ok"),
            "ultra_grand_extension_export_bundle_ok": ultra_grand_stack_stack_closure.get("ultra_grand_extension_export_bundle_ok"),
            "ultra_grand_stack_breakpoint_freeze": ultra_grand_stack_stack_closure.get("ultra_grand_stack_breakpoint_freeze"),
            "curated_reviewed_count": ultra_grand_stack_stack_closure.get("curated_reviewed_count"),
        },
        "43_post_p68_maintenance_bundle": {
            "ok": post_breakpoint_passive_drift.get("observation_ok") is True
            and curated_bulk_human_review.get("bulk_human_review_ok") is True
            and post_breakpoint_passive_drift_artifact.is_file()
            and curated_bulk_human_review_artifact.is_file(),
            "status": "post_p68_maintenance_wire_ok"
            if post_breakpoint_passive_drift.get("observation_ok") is True
            and curated_bulk_human_review.get("bulk_human_review_ok") is True
            else "incomplete",
            "passive_drift_artifact": str(post_breakpoint_passive_drift_artifact).replace("\\", "/"),
            "curated_bulk_artifact": str(curated_bulk_human_review_artifact).replace("\\", "/"),
            "drift_regression_detected": post_breakpoint_passive_drift.get("drift_regression_detected"),
            "ultra_grand_stack_breakpoint_freeze": post_breakpoint_passive_drift.get("ultra_grand_stack_breakpoint_freeze"),
            "curated_reviewed_count": curated_bulk_human_review.get("curated_reviewed_count"),
            "curated_pending_human_review": curated_bulk_human_review.get("curated_pending_human_review"),
            "tier_inflation_forbidden": True,
        },
    }
    closure_ok = all((items[k] or {}).get("ok") for k in ("1_daily_capture", "2_curated_learning_ack", "3_fact_lock_bundle", "4_weekly_scheduler", "5_http_smoke_alerts", "6_export_ingest", "8_mission_log_routine"))
    full_stack_closure_ok = all(v.get("ok") for v in items.values())
    return {
        "schema": "tkm_encounter_sequence_ops_closure_v1",
        "version": "5.2.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "send_gate": "HOLD",
        "closure_ok": closure_ok,
        "full_stack_closure_ok": full_stack_closure_ok,
        "items": items,
        "reproduce": "py scripts/build_tkm_encounter_sequence_ops_closure_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ok = doc.get("full_stack_closure_ok") if doc.get("version") in ("2.0.0", "2.1.0", "2.2.0", "2.3.0", "2.4.0", "2.5.0", "2.6.0", "2.7.0", "2.8.0", "2.9.0", "3.0.0", "3.1.0", "3.2.0", "3.3.0") else doc.get("closure_ok")
    print(json.dumps({"ok": ok, "closure_ok": doc.get("closure_ok"), "full_stack_closure_ok": doc.get("full_stack_closure_ok")}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
