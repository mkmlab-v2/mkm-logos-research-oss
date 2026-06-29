#!/usr/bin/env python3
"""Weekly TKM encounter_sequence rollup — KPI + curated drafts [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / "reports/encounter_sequence_summary_v1_latest.json"
DRAFTS = ROOT / "docs/final/artifacts/encounter_sequence_curated_learning_draft_v1_latest.json"
MULTI = ROOT / "reports/encounter_sequence_multiturn_smoke_v1_latest.json"
DUAL = ROOT / "reports/tkm_clinic_encounter_dual_lane_summary_v1_latest.json"
DELTA = ROOT / "reports/tkm_match_rate_delta_report_v1_latest.json"
MYEONGNI_KPI = ROOT / "reports/tkm_encounter_sequence_myeongni_kpi_v1_latest.json"
LOGOS_KPI = ROOT / "reports/tkm_encounter_sequence_logos_kpi_v1_latest.json"
CROSS_LENS_KPI = ROOT / "reports/tkm_encounter_sequence_cross_lens_kpi_v1_latest.json"
PASSIVE_OBS = ROOT / "reports/tkm_encounter_sequence_passive_observation_v1_latest.json"
CONFLICT_RESOLVER = ROOT / "reports/tkm_encounter_sequence_conflict_resolver_kpi_v1_latest.json"
DISAGREEMENT_CROSS = ROOT / "reports/tkm_encounter_sequence_disagreement_resolver_cross_kpi_v1_latest.json"
EXPORT_INGEST_KPI = ROOT / "reports/tkm_encounter_sequence_export_ingest_kpi_v1_latest.json"
LENS_STACK_ROLLUP = ROOT / "reports/tkm_encounter_sequence_lens_stack_rollup_v1_latest.json"
PASSIVE_INTEGRATED = ROOT / "reports/tkm_encounter_sequence_passive_integrated_rollup_v1_latest.json"
CLINICAL_STUB = ROOT / "reports/tkm_encounter_sequence_clinical_validation_stub_v1_latest.json"
FULL_STACK_BUNDLE = ROOT / "reports/tkm_encounter_sequence_full_stack_export_bundle_v1_latest.json"
EXTENDED_STACK_BUNDLE = ROOT / "reports/tkm_encounter_sequence_extended_stack_export_bundle_v1_latest.json"
P43_OBSERVABILITY = ROOT / "reports/tkm_encounter_sequence_p43_observability_rollup_v1_latest.json"
STACK_FINAL_CLOSURE = ROOT / "reports/tkm_encounter_sequence_stack_final_closure_v1_latest.json"
CURATED_MILESTONE = ROOT / "reports/tkm_encounter_sequence_curated_review_milestone_v1_latest.json"
GPU_INTERPRET_OBS = ROOT / "reports/tkm_encounter_sequence_gpu_interpret_observation_v1_latest.json"
STACK_EXTENSION_CLOSURE = ROOT / "reports/tkm_encounter_sequence_stack_extension_closure_v1_latest.json"
FULL_EXTENSION_CLOSURE = ROOT / "reports/tkm_encounter_sequence_full_extension_closure_v1_latest.json"
POST_EXTENSION_OBS = ROOT / "reports/tkm_encounter_sequence_post_extension_observation_v1_latest.json"
INTEGRATED_STACK_CLOSURE = ROOT / "reports/tkm_encounter_sequence_integrated_stack_closure_v1_latest.json"
NOTEBOOKLM_EXPORT_SYNC = ROOT / "reports/tkm_encounter_sequence_notebooklm_export_sync_v1_latest.json"
POST_EXPORT_PASSIVE_OBS = ROOT / "reports/tkm_encounter_sequence_post_export_passive_observation_v1_latest.json"
FULL_POST_EXPORT_CLOSURE = ROOT / "reports/tkm_encounter_sequence_full_post_export_closure_v1_latest.json"
POST_EXPORT_EXTENDED_BUNDLE = ROOT / "reports/tkm_encounter_sequence_post_export_extended_export_bundle_v1_latest.json"
POST_EXPORT_STACK_CLOSURE = ROOT / "reports/tkm_encounter_sequence_post_export_stack_closure_v1_latest.json"
GRAND_POST_EXPORT_CLOSURE = ROOT / "reports/tkm_encounter_sequence_grand_post_export_closure_v1_latest.json"
GRAND_EXPORT_BUNDLE_VAULT_SYNC = ROOT / "reports/tkm_encounter_sequence_grand_export_bundle_vault_sync_v1_latest.json"
POST_GRAND_PASSIVE_OBS = ROOT / "reports/tkm_encounter_sequence_post_grand_passive_observation_v1_latest.json"
FULL_GRAND_STACK_FINAL_CLOSURE = ROOT / "reports/tkm_encounter_sequence_full_grand_stack_final_closure_v1_latest.json"
GRAND_STACK_EXTENSION_EXPORT_BUNDLE = ROOT / "reports/tkm_encounter_sequence_grand_stack_extension_export_bundle_v1_latest.json"
GRAND_STACK_STACK_CLOSURE = ROOT / "reports/tkm_encounter_sequence_grand_stack_stack_closure_v1_latest.json"
ULTRA_GRAND_POST_EXPORT_CLOSURE = ROOT / "reports/tkm_encounter_sequence_ultra_grand_post_export_closure_v1_latest.json"
ULTRA_GRAND_EXPORT_BUNDLE_VAULT_SYNC = ROOT / "reports/tkm_encounter_sequence_ultra_grand_export_bundle_vault_sync_v1_latest.json"
POST_ULTRA_GRAND_PASSIVE_OBS = ROOT / "reports/tkm_encounter_sequence_post_ultra_grand_passive_observation_v1_latest.json"
FULL_ULTRA_GRAND_STACK_FINAL_CLOSURE = ROOT / "reports/tkm_encounter_sequence_full_ultra_grand_stack_final_closure_v1_latest.json"
ULTRA_GRAND_EXTENSION_EXPORT_BUNDLE = ROOT / "reports/tkm_encounter_sequence_ultra_grand_extension_export_bundle_v1_latest.json"
ULTRA_GRAND_STACK_STACK_CLOSURE = ROOT / "reports/tkm_encounter_sequence_ultra_grand_stack_stack_closure_v1_latest.json"
POST_BREAKPOINT_PASSIVE_DRIFT = ROOT / "reports/tkm_encounter_sequence_post_breakpoint_passive_drift_observation_v1_latest.json"
CURATED_BULK_HUMAN_REVIEW = ROOT / "reports/tkm_encounter_sequence_curated_bulk_human_review_v1_latest.json"
OPS_CLOSURE = ROOT / "reports/tkm_encounter_sequence_ops_closure_v1_latest.json"
L0_KPI = ROOT / "reports/tkm_encounter_sequence_l0_kpi_v1_latest.json"
OUT = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _iter_ledger_records() -> list[dict[str, Any]]:
    import importlib.util

    ledger_path = ROOT / "scripts/encounter_sequence_ledger_v1.py"
    spec = importlib.util.spec_from_file_location("encounter_sequence_ledger_v1", ledger_path)
    if spec is None or spec.loader is None:
        return []
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return list(mod.iter_ledger_records(ROOT))


def _multiturn_churn_kpi(summary: dict[str, Any], multi: dict[str, Any]) -> dict[str, Any]:
    deltas: list[float] = []
    label_change_sequences = 0
    for row in _iter_ledger_records():
        seq_summary = row.get("sequence_summary") if isinstance(row.get("sequence_summary"), dict) else {}
        confs = seq_summary.get("confidence_trajectory")
        if isinstance(confs, list) and len(confs) >= 2:
            deltas.append(float(confs[-1]) - float(confs[0]))
        traj = seq_summary.get("constitution_trajectory")
        if isinstance(traj, list) and len(traj) >= 2 and len(set(traj)) > 1:
            label_change_sequences += 1

    avg_delta = round(sum(deltas) / len(deltas), 4) if deltas else None
    smoke_delta = multi.get("confidence_delta_last_minus_first")
    avg_turns = summary.get("avg_turn_count")
    label_changes = int(summary.get("sequences_with_label_change") or label_change_sequences)
    churn_signal = label_changes >= 1 or (avg_delta is not None and avg_delta > 0) or (
        isinstance(smoke_delta, (int, float)) and float(smoke_delta) > 0
    )
    multiturn_churn_ok = summary.get("summary_ok") is True and (avg_turns or 0) >= 1.0 and churn_signal
    return {
        "avg_turn_count": avg_turns,
        "sequences_with_label_change": label_changes,
        "avg_confidence_delta_multiturn": avg_delta,
        "multiturn_sequence_count_with_delta": len(deltas),
        "multiturn_smoke_confidence_delta": smoke_delta,
        "multiturn_churn_ok": multiturn_churn_ok,
    }


def _dual_lane_headline_kpi(dual: dict[str, Any]) -> dict[str, Any]:
    gold = dual.get("physician_gold_only") if isinstance(dual.get("physician_gold_only"), dict) else {}
    dummy = dual.get("operational_dummy") if isinstance(dual.get("operational_dummy"), dict) else {}
    clinic_n = int(gold.get("clinic_capture_count") or 0)
    enc_n = int(gold.get("encounter_sequence_count") or 0)
    headline_ok = dual.get("dual_lane_ok") is True and clinic_n >= 3 and enc_n >= 3
    return {
        "lane": "physician_gold_only",
        "clinic_capture_count": clinic_n,
        "encounter_sequence_count": enc_n,
        "clinic_match_rate": gold.get("clinic_match_rate"),
        "encounter_match_rate": gold.get("encounter_match_rate"),
        "dual_lane_headline_ok": headline_ok,
        "operational_dummy_lane": {
            "clinic_capture_count": int(dummy.get("clinic_capture_count") or 0),
            "encounter_sequence_count": int(dummy.get("encounter_sequence_count") or 0),
            "label": dummy.get("label"),
        },
        "note_ko": "헤드라인 KPI는 physician_gold_only만. blended_all_ledger는 운영 참고.",
    }


def _l5_myeongni_kpi(myeongni: dict[str, Any]) -> dict[str, Any]:
    gold = myeongni.get("physician_gold_only") if isinstance(myeongni.get("physician_gold_only"), dict) else {}
    all_ledger = myeongni.get("all_ledger") if isinstance(myeongni.get("all_ledger"), dict) else {}
    headline_ok = (
        myeongni.get("kpi_ok") is True
        and int(gold.get("myeongni_sidecar_count") or 0) >= 1
        and gold.get("myeongni_report_linked_rate") is not None
        and int((all_ledger.get("cross_check_computed_count") or 0)) >= 1
        and int(gold.get("engine_report_linked_count") or 0) >= 1
        and int(gold.get("stub_report_linked_count") or 0) == 0
    )
    return {
        "lane": "physician_gold_only",
        "birth_profile_present_rate": gold.get("birth_profile_present_rate"),
        "myeongni_sidecar_count": gold.get("myeongni_sidecar_count"),
        "myeongni_report_linked_rate": gold.get("myeongni_report_linked_rate"),
        "engine_report_linked_count": gold.get("engine_report_linked_count"),
        "stub_report_linked_count": gold.get("stub_report_linked_count"),
        "engine_report_linked_rate": gold.get("engine_report_linked_rate"),
        "cross_check_status_counts": all_ledger.get("cross_check_status_counts"),
        "cross_check_computed_count": all_ledger.get("cross_check_computed_count"),
        "cross_check_computed_rate": all_ledger.get("cross_check_computed_rate"),
        "l5_myeongni_headline_ok": headline_ok,
        "non_gating": True,
        "note_ko": "L5 명리 [HYPO] — 사상 헤드라인 KPI와 분리.",
    }


def _l6_logos_kpi(logos: dict[str, Any]) -> dict[str, Any]:
    gold = logos.get("physician_gold_only") if isinstance(logos.get("physician_gold_only"), dict) else {}
    all_ledger = logos.get("all_ledger") if isinstance(logos.get("all_ledger"), dict) else {}
    headline_ok = (
        logos.get("kpi_ok") is True
        and logos.get("physician_gold_logos_ok") is True
        and int(gold.get("logos_sidecar_count") or 0) >= 1
        and gold.get("logos_anchor_linked_rate") == 1.0
        and int(all_ledger.get("non_gating_count") or 0) == int(all_ledger.get("logos_sidecar_count") or 0)
    )
    return {
        "lane": "physician_gold_only",
        "logos_sidecar_count": gold.get("logos_sidecar_count"),
        "logos_anchor_linked_rate": gold.get("logos_anchor_linked_rate"),
        "motif_file_stem_counts": all_ledger.get("motif_file_stem_counts"),
        "l6_logos_headline_ok": headline_ok,
        "non_gating": True,
        "note_ko": "L6 Logos cosmic anchor [HYPO][NON_GATING] — 사상·명리 헤드라인 분리.",
    }


def _cross_lens_kpi(cross: dict[str, Any]) -> dict[str, Any]:
    resonance = cross.get("cross_lens_resonance_index")
    headline_ok = (
        cross.get("kpi_ok") is True
        and cross.get("non_gating") is True
        and cross.get("motif_skew_gate_ok") is True
        and isinstance(resonance, (int, float))
        and float(resonance) >= 0.3
    )
    return {
        "lane": "physician_gold_only",
        "cross_lens_resonance_index": resonance,
        "l4_l5_l6_complete_row_count": cross.get("l4_l5_l6_complete_row_count"),
        "l4_sasang_encounter_match_rate": cross.get("l4_sasang_encounter_match_rate"),
        "l5_myeongni_engine_linked_rate": cross.get("l5_myeongni_engine_linked_rate"),
        "l6_logos_anchor_linked_rate": cross.get("l6_logos_anchor_linked_rate"),
        "motif_top1_share": cross.get("motif_top1_share"),
        "motif_skew_gate_ok": cross.get("motif_skew_gate_ok"),
        "cross_lens_headline_ok": headline_ok,
        "non_gating": True,
        "note_ko": "L7 Cross-lens [HYPO][NON_GATING] — 성경/명리/사상 지표 공진 관측.",
    }


def _passive_observation_kpi(passive: dict[str, Any]) -> dict[str, Any]:
    return {
        "observation_ok": passive.get("observation_ok"),
        "weekly_task_ready": passive.get("weekly_task_ready"),
        "interpret_cpu_guard_ok": passive.get("interpret_cpu_guard_ok"),
        "interpret_gpu_train_attempted": passive.get("interpret_gpu_train_attempted"),
        "motif_top1_share": passive.get("motif_top1_share"),
        "motif_skew_gate_ok": passive.get("motif_skew_gate_ok"),
        "non_gating": True,
        "note_ko": "패시브 관측 [HYPO] — L5/L6/L7 + Interpret CPU guard; Track A 합선 금지.",
    }


def _export_ingest_kpi(export_kpi: dict[str, Any]) -> dict[str, Any]:
    headline_ok = (
        export_kpi.get("kpi_ok") is True
        and export_kpi.get("live_ingest_ok") is True
        and export_kpi.get("lens_stack_ok") is True
        and export_kpi.get("has_l6_logos_ref") is True
        and export_kpi.get("has_l7_conflict_resolver_ref") is True
    )
    return {
        "live_ingest_ok": export_kpi.get("live_ingest_ok"),
        "lens_stack_ok": export_kpi.get("lens_stack_ok"),
        "sequence_id": export_kpi.get("sequence_id"),
        "has_l6_logos_ref": export_kpi.get("has_l6_logos_ref"),
        "has_l7_conflict_resolver_ref": export_kpi.get("has_l7_conflict_resolver_ref"),
        "export_ingest_headline_ok": headline_ok,
        "non_gating": True,
        "note_ko": "Export/ingest live [HYPO] — clinic→ledger L6/L7 attach 검증.",
    }


def _lens_stack_rollup_kpi(rollup: dict[str, Any]) -> dict[str, Any]:
    gates = rollup.get("gates") if isinstance(rollup.get("gates"), dict) else {}
    headline_ok = (
        rollup.get("rollup_ok") is True
        and rollup.get("non_gating") is True
        and all((gates.get(k) or {}).get("gate_ok") is True for k in ("p33", "p34", "p35", "p36", "p37", "p38"))
        and int((rollup.get("ledger_layer_counts") or {}).get("physician_gold_sequence_count") or 0) >= 1
    )
    snap = rollup.get("kpi_snapshot") if isinstance(rollup.get("kpi_snapshot"), dict) else {}
    return {
        "rollup_ok": rollup.get("rollup_ok"),
        "gates_ok_count": sum(1 for g in gates.values() if isinstance(g, dict) and g.get("gate_ok") is True),
        "cross_lens_resonance_index": snap.get("cross_lens_resonance_index"),
        "disagreement_physician_authority_rate": snap.get("disagreement_physician_authority_rate"),
        "export_ingest_live_ok": snap.get("export_ingest_live_ok"),
        "full_stack_closure_ok": snap.get("full_stack_closure_ok"),
        "lens_stack_rollup_headline_ok": headline_ok,
        "non_gating": True,
        "note_ko": "P33–P38 lens stack rollup [HYPO][NON_GATING]; NotebookLM/ops 참고용.",
    }


def _passive_integrated_rollup_kpi(rollup: dict[str, Any]) -> dict[str, Any]:
    headline_ok = (
        rollup.get("integrated_ok") is True
        and rollup.get("non_gating") is True
        and rollup.get("passive_observation_ok") is True
        and rollup.get("interpret_cpu_guard_ok") is True
        and rollup.get("curated_learning_ack_ok") is True
        and int(rollup.get("curated_learning_registry_row_count") or 0) >= 1
    )
    return {
        "integrated_ok": rollup.get("integrated_ok"),
        "passive_observation_ok": rollup.get("passive_observation_ok"),
        "interpret_cpu_guard_ok": rollup.get("interpret_cpu_guard_ok"),
        "interpret_gpu_train_attempted": rollup.get("interpret_gpu_train_attempted"),
        "interpret_gpu_train_ok": rollup.get("interpret_gpu_train_ok"),
        "curated_learning_ack_ok": rollup.get("curated_learning_ack_ok"),
        "curated_learning_registry_row_count": rollup.get("curated_learning_registry_row_count"),
        "passive_integrated_headline_ok": headline_ok,
        "non_gating": True,
        "note_ko": "P40 패시브+Interpret+curated 통합 [HYPO][NON_GATING]; auto-training 금지.",
    }


def _clinical_validation_stub_kpi(stub: dict[str, Any]) -> dict[str, Any]:
    headline_ok = (
        stub.get("validation_stub_ok") is True
        and stub.get("non_gating") is True
        and stub.get("research_only") is True
        and stub.get("boundary_contract_pass_rate") == 1.0
        and (stub.get("physician_closure_pass_rate") or 0) >= 0.5
        and (stub.get("lens_stack_wired_rate") or 0) >= 0.75
        and int(stub.get("physician_gold_sequence_count") or 0) >= 3
    )
    review = stub.get("curated_learning_review") if isinstance(stub.get("curated_learning_review"), dict) else {}
    return {
        "validation_stub_ok": stub.get("validation_stub_ok"),
        "physician_gold_sequence_count": stub.get("physician_gold_sequence_count"),
        "boundary_contract_pass_rate": stub.get("boundary_contract_pass_rate"),
        "physician_closure_pass_rate": stub.get("physician_closure_pass_rate"),
        "lens_stack_wired_rate": stub.get("lens_stack_wired_rate"),
        "curated_pending_human_review": review.get("pending_human_review"),
        "clinical_validation_headline_ok": headline_ok,
        "non_gating": True,
        "research_only": True,
        "note_ko": "P41 임상 validation stub [HYPO][NON_GATING]; Track A·진단·처방 금지.",
    }


def _full_stack_export_bundle_kpi(bundle: dict[str, Any]) -> dict[str, Any]:
    gates = bundle.get("gates") if isinstance(bundle.get("gates"), dict) else {}
    snap = bundle.get("rollup_snapshot") if isinstance(bundle.get("rollup_snapshot"), dict) else {}
    headline_ok = (
        bundle.get("export_bundle_ok") is True
        and bundle.get("non_gating") is True
        and all((gates.get(k) or {}).get("gate_ok") is True for k in ("p39", "p40", "p41"))
        and snap.get("lens_stack_rollup_ok") is True
        and snap.get("passive_integrated_ok") is True
        and snap.get("clinical_validation_stub_ok") is True
    )
    return {
        "export_bundle_ok": bundle.get("export_bundle_ok"),
        "gates_ok_count": sum(1 for g in gates.values() if isinstance(g, dict) and g.get("gate_ok") is True),
        "physician_gold_sequence_count": snap.get("physician_gold_sequence_count"),
        "cross_lens_resonance_index": snap.get("cross_lens_resonance_index"),
        "full_stack_export_headline_ok": headline_ok,
        "non_gating": True,
        "research_only": True,
        "note_ko": "P42 full-stack export bundle [HYPO][NON_GATING]; NotebookLM/ops 참고용.",
    }


def _extended_stack_export_bundle_kpi(bundle: dict[str, Any]) -> dict[str, Any]:
    gates = bundle.get("gates") if isinstance(bundle.get("gates"), dict) else {}
    snap = bundle.get("rollup_snapshot") if isinstance(bundle.get("rollup_snapshot"), dict) else {}
    headline_ok = (
        bundle.get("extended_export_bundle_ok") is True
        and bundle.get("non_gating") is True
        and int(bundle.get("gates_ok_count") or 0) >= 15
        and bundle.get("base_export_bundle_ok") is True
        and bundle.get("extension_closure_ok") is True
        and snap.get("curated_milestone_ok") is True
        and snap.get("gpu_interpret_observation_ok") is True
    )
    return {
        "extended_export_bundle_ok": bundle.get("extended_export_bundle_ok"),
        "gates_ok_count": bundle.get("gates_ok_count"),
        "base_export_bundle_ok": bundle.get("base_export_bundle_ok"),
        "extension_closure_ok": bundle.get("extension_closure_ok"),
        "curated_reviewed_count": snap.get("curated_reviewed_count"),
        "extended_stack_export_headline_ok": headline_ok,
        "non_gating": True,
        "research_only": True,
        "note_ko": "P48 extended export bundle [HYPO][NON_GATING]; P33–P47 NotebookLM/ops 참고용.",
    }


def _p43_observability_kpi(rollup: dict[str, Any]) -> dict[str, Any]:
    counts = rollup.get("curated_review_counts") if isinstance(rollup.get("curated_review_counts"), dict) else {}
    headline_ok = (
        rollup.get("observability_ok") is True
        and rollup.get("non_gating") is True
        and rollup.get("passive_observation_ok") is True
        and rollup.get("interpret_cpu_guard_ok") is True
        and rollup.get("curated_review_mark_ok") is True
        and int(counts.get("reviewed") or 0) >= 1
    )
    return {
        "observability_ok": rollup.get("observability_ok"),
        "interpret_gpu_train_attempted": rollup.get("interpret_gpu_train_attempted"),
        "interpret_gpu_train_ok": rollup.get("interpret_gpu_train_ok"),
        "curated_reviewed_count": counts.get("reviewed"),
        "curated_pending_human_review": counts.get("pending_human_review"),
        "p43_observability_headline_ok": headline_ok,
        "non_gating": True,
        "research_only": True,
        "note_ko": "P43 GPU+passive+curated observability [HYPO][NON_GATING]; auto-training 금지.",
    }


def _stack_final_closure_kpi(closure: dict[str, Any]) -> dict[str, Any]:
    gates = closure.get("gates") if isinstance(closure.get("gates"), dict) else {}
    headline_ok = (
        closure.get("final_closure_ok") is True
        and closure.get("non_gating") is True
        and int(closure.get("gates_ok_count") or 0) >= 11
        and closure.get("export_bundle_ok") is True
        and closure.get("observability_ok") is True
        and int(closure.get("curated_reviewed_count") or 0) >= 1
    )
    return {
        "final_closure_ok": closure.get("final_closure_ok"),
        "gates_ok_count": closure.get("gates_ok_count"),
        "export_bundle_ok": closure.get("export_bundle_ok"),
        "observability_ok": closure.get("observability_ok"),
        "curated_reviewed_count": closure.get("curated_reviewed_count"),
        "stack_final_closure_headline_ok": headline_ok,
        "non_gating": True,
        "research_only": True,
        "note_ko": "P44 stack final closure [HYPO][NON_GATING]; P33–P43 전체 wired.",
    }


def _curated_review_milestone_kpi(milestone: dict[str, Any]) -> dict[str, Any]:
    counts = milestone.get("curated_review_counts") if isinstance(milestone.get("curated_review_counts"), dict) else {}
    headline_ok = (
        milestone.get("milestone_ok") is True
        and milestone.get("non_gating") is True
        and milestone.get("human_gate_ack_ok") is True
        and milestone.get("milestone_threshold_met") is True
        and int(counts.get("reviewed") or 0) >= int(milestone.get("milestone_reviewed_min") or 6)
    )
    return {
        "milestone_ok": milestone.get("milestone_ok"),
        "milestone_reviewed_min": milestone.get("milestone_reviewed_min"),
        "milestone_threshold_met": milestone.get("milestone_threshold_met"),
        "human_gate_ack_ok": milestone.get("human_gate_ack_ok"),
        "curated_reviewed_count": counts.get("reviewed"),
        "curated_pending_human_review": counts.get("pending_human_review"),
        "curated_review_milestone_headline_ok": headline_ok,
        "non_gating": True,
        "research_only": True,
        "note_ko": "P45 curated human-review milestone [HYPO][NON_GATING]; human-gate only; auto-training 금지.",
    }


def _gpu_interpret_observation_kpi(obs: dict[str, Any]) -> dict[str, Any]:
    counts = obs.get("curated_review_counts") if isinstance(obs.get("curated_review_counts"), dict) else {}
    headline_ok = (
        obs.get("observation_ok") is True
        and obs.get("non_gating") is True
        and obs.get("interpret_cpu_guard_ok") is True
        and obs.get("passive_observation_ok") is True
        and obs.get("curated_milestone_ok") is True
        and int(counts.get("reviewed") or 0) >= 6
    )
    return {
        "observation_ok": obs.get("observation_ok"),
        "interpret_cpu_guard_ok": obs.get("interpret_cpu_guard_ok"),
        "interpret_gpu_train_attempted": obs.get("interpret_gpu_train_attempted"),
        "interpret_gpu_train_ok": obs.get("interpret_gpu_train_ok"),
        "interpret_gpu_skipped_reason": obs.get("interpret_gpu_skipped_reason"),
        "curated_reviewed_count": counts.get("reviewed"),
        "gpu_interpret_observation_headline_ok": headline_ok,
        "non_gating": True,
        "research_only": True,
        "note_ko": "P46 GPU+Interpret observability [HYPO][NON_GATING]; CPU guard 기본·GPU optional; auto-training 금지.",
    }


def _stack_extension_closure_kpi(closure: dict[str, Any]) -> dict[str, Any]:
    headline_ok = (
        closure.get("extension_closure_ok") is True
        and closure.get("non_gating") is True
        and int(closure.get("gates_ok_count") or 0) >= 14
        and closure.get("stack_final_closure_ok") is True
        and closure.get("curated_milestone_ok") is True
        and closure.get("gpu_interpret_observation_ok") is True
        and int(closure.get("curated_reviewed_count") or 0) >= 6
    )
    return {
        "extension_closure_ok": closure.get("extension_closure_ok"),
        "gates_ok_count": closure.get("gates_ok_count"),
        "stack_final_closure_ok": closure.get("stack_final_closure_ok"),
        "curated_milestone_ok": closure.get("curated_milestone_ok"),
        "gpu_interpret_observation_ok": closure.get("gpu_interpret_observation_ok"),
        "curated_reviewed_count": closure.get("curated_reviewed_count"),
        "stack_extension_closure_headline_ok": headline_ok,
        "non_gating": True,
        "research_only": True,
        "note_ko": "P47 stack extension closure [HYPO][NON_GATING]; P33–P46 전체 wired.",
    }


def _full_extension_closure_kpi(closure: dict[str, Any]) -> dict[str, Any]:
    headline_ok = (
        closure.get("full_extension_closure_ok") is True
        and closure.get("non_gating") is True
        and int(closure.get("gates_ok_count") or 0) >= 16
        and closure.get("stack_final_closure_ok") is True
        and closure.get("stack_extension_closure_ok") is True
        and closure.get("extended_export_bundle_ok") is True
        and int(closure.get("curated_reviewed_count") or 0) >= 6
    )
    return {
        "full_extension_closure_ok": closure.get("full_extension_closure_ok"),
        "gates_ok_count": closure.get("gates_ok_count"),
        "stack_final_closure_ok": closure.get("stack_final_closure_ok"),
        "stack_extension_closure_ok": closure.get("stack_extension_closure_ok"),
        "extended_export_bundle_ok": closure.get("extended_export_bundle_ok"),
        "curated_reviewed_count": closure.get("curated_reviewed_count"),
        "full_extension_closure_headline_ok": headline_ok,
        "non_gating": True,
        "research_only": True,
        "note_ko": "P49 full extension closure [HYPO][NON_GATING]; P33–P48 전체 wired.",
    }


def _post_extension_observation_kpi(obs: dict[str, Any]) -> dict[str, Any]:
    headline_ok = (
        obs.get("observation_ok") is True
        and obs.get("non_gating") is True
        and obs.get("full_extension_closure_ok") is True
        and obs.get("passive_observation_ok") is True
        and obs.get("export_ingest_kpi_ok") is True
        and obs.get("weekly_task_ready") is True
        and obs.get("interpret_cpu_guard_ok") is True
    )
    return {
        "observation_ok": obs.get("observation_ok"),
        "full_extension_closure_ok": obs.get("full_extension_closure_ok"),
        "passive_observation_ok": obs.get("passive_observation_ok"),
        "export_ingest_kpi_ok": obs.get("export_ingest_kpi_ok"),
        "weekly_task_ready": obs.get("weekly_task_ready"),
        "interpret_gpu_train_attempted": obs.get("interpret_gpu_train_attempted"),
        "post_extension_observation_headline_ok": headline_ok,
        "non_gating": True,
        "research_only": True,
        "note_ko": "P50 post-extension passive+export observability [HYPO][NON_GATING]; auto-training 금지.",
    }


def _integrated_stack_closure_kpi(closure: dict[str, Any]) -> dict[str, Any]:
    headline_ok = (
        closure.get("integrated_closure_ok") is True
        and closure.get("non_gating") is True
        and int(closure.get("gates_ok_count") or 0) >= 18
        and closure.get("full_extension_closure_ok") is True
        and closure.get("post_extension_observation_ok") is True
        and closure.get("extended_export_bundle_ok") is True
        and closure.get("weekly_task_ready") is True
    )
    return {
        "integrated_closure_ok": closure.get("integrated_closure_ok"),
        "gates_ok_count": closure.get("gates_ok_count"),
        "full_extension_closure_ok": closure.get("full_extension_closure_ok"),
        "post_extension_observation_ok": closure.get("post_extension_observation_ok"),
        "extended_export_bundle_ok": closure.get("extended_export_bundle_ok"),
        "weekly_task_ready": closure.get("weekly_task_ready"),
        "integrated_stack_closure_headline_ok": headline_ok,
        "non_gating": True,
        "research_only": True,
        "note_ko": "P51 integrated stack closure [HYPO][NON_GATING]; P33–P50 전체 wired.",
    }


def _notebooklm_export_sync_kpi(sync: dict[str, Any]) -> dict[str, Any]:
    vault = sync.get("vault_mirror") if isinstance(sync.get("vault_mirror"), dict) else {}
    headline_ok = (
        sync.get("export_sync_ok") is True
        and sync.get("non_gating") is True
        and sync.get("integrated_closure_ok") is True
        and sync.get("cloud_upload_forbidden") is True
        and sync.get("cloud_upload_attempted") is False
        and int(sync.get("manifest_files_present_count") or 0) >= 11
        and vault.get("vault_mirror_ok") is True
    )
    return {
        "export_sync_ok": sync.get("export_sync_ok"),
        "integrated_closure_ok": sync.get("integrated_closure_ok"),
        "manifest_files_present_count": sync.get("manifest_files_present_count"),
        "cloud_upload_forbidden": sync.get("cloud_upload_forbidden"),
        "vault_mirror_skipped": vault.get("vault_mirror_skipped"),
        "notebooklm_export_sync_headline_ok": headline_ok,
        "non_gating": True,
        "research_only": True,
        "note_ko": "P52 NotebookLM export sync manifest [HYPO][NON_GATING]; vault mirror only; cloud upload 금지.",
    }


def _post_export_passive_observation_kpi(obs: dict[str, Any]) -> dict[str, Any]:
    headline_ok = (
        obs.get("observation_ok") is True
        and obs.get("non_gating") is True
        and obs.get("export_sync_ok") is True
        and obs.get("passive_observation_ok") is True
        and obs.get("export_ingest_kpi_ok") is True
        and obs.get("curated_milestone_ok") is True
        and obs.get("weekly_task_ready") is True
        and obs.get("interpret_cpu_guard_ok") is True
    )
    return {
        "observation_ok": obs.get("observation_ok"),
        "export_sync_ok": obs.get("export_sync_ok"),
        "passive_observation_ok": obs.get("passive_observation_ok"),
        "export_ingest_kpi_ok": obs.get("export_ingest_kpi_ok"),
        "curated_milestone_ok": obs.get("curated_milestone_ok"),
        "curated_reviewed_count": obs.get("curated_reviewed_count"),
        "curated_pending_human_review": obs.get("curated_pending_human_review"),
        "weekly_task_ready": obs.get("weekly_task_ready"),
        "interpret_gpu_train_attempted": obs.get("interpret_gpu_train_attempted"),
        "post_export_passive_observation_headline_ok": headline_ok,
        "non_gating": True,
        "research_only": True,
        "note_ko": "P53 post-export passive+curated observability [HYPO][NON_GATING]; auto-training 금지.",
    }


def _full_post_export_closure_kpi(closure: dict[str, Any]) -> dict[str, Any]:
    headline_ok = (
        closure.get("full_post_export_closure_ok") is True
        and closure.get("non_gating") is True
        and int(closure.get("gates_ok_count") or 0) >= 21
        and closure.get("integrated_closure_ok") is True
        and closure.get("export_sync_ok") is True
        and closure.get("post_export_observation_ok") is True
        and closure.get("full_extension_closure_ok") is True
        and int(closure.get("curated_reviewed_count") or 0) >= 6
    )
    return {
        "full_post_export_closure_ok": closure.get("full_post_export_closure_ok"),
        "gates_ok_count": closure.get("gates_ok_count"),
        "integrated_closure_ok": closure.get("integrated_closure_ok"),
        "export_sync_ok": closure.get("export_sync_ok"),
        "post_export_observation_ok": closure.get("post_export_observation_ok"),
        "full_extension_closure_ok": closure.get("full_extension_closure_ok"),
        "curated_reviewed_count": closure.get("curated_reviewed_count"),
        "full_post_export_closure_headline_ok": headline_ok,
        "non_gating": True,
        "research_only": True,
        "note_ko": "P54 full post-export closure [HYPO][NON_GATING]; P33–P53 전체 wired.",
    }


def _post_export_extended_export_bundle_kpi(bundle: dict[str, Any]) -> dict[str, Any]:
    gates = bundle.get("gates") if isinstance(bundle.get("gates"), dict) else {}
    snap = bundle.get("rollup_snapshot") if isinstance(bundle.get("rollup_snapshot"), dict) else {}
    headline_ok = (
        bundle.get("post_export_extended_export_bundle_ok") is True
        and bundle.get("non_gating") is True
        and int(bundle.get("gates_ok_count") or 0) >= 22
        and bundle.get("extended_export_bundle_ok") is True
        and bundle.get("full_post_export_closure_ok") is True
        and snap.get("export_sync_ok") is True
        and snap.get("post_export_observation_ok") is True
        and snap.get("integrated_closure_ok") is True
    )
    return {
        "post_export_extended_export_bundle_ok": bundle.get("post_export_extended_export_bundle_ok"),
        "gates_ok_count": bundle.get("gates_ok_count"),
        "extended_export_bundle_ok": bundle.get("extended_export_bundle_ok"),
        "full_post_export_closure_ok": bundle.get("full_post_export_closure_ok"),
        "curated_reviewed_count": snap.get("curated_reviewed_count"),
        "post_export_extended_export_headline_ok": headline_ok,
        "non_gating": True,
        "research_only": True,
        "note_ko": "P55 post-export extended export bundle [HYPO][NON_GATING]; P33–P54 NotebookLM/ops 참고용.",
    }


def _post_export_stack_closure_kpi(closure: dict[str, Any]) -> dict[str, Any]:
    headline_ok = (
        closure.get("post_export_stack_closure_ok") is True
        and closure.get("non_gating") is True
        and int(closure.get("gates_ok_count") or 0) >= 5
        and closure.get("integrated_closure_ok") is True
        and closure.get("export_sync_ok") is True
        and closure.get("post_export_observation_ok") is True
        and closure.get("full_post_export_closure_ok") is True
        and closure.get("post_export_extended_export_bundle_ok") is True
        and int(closure.get("curated_reviewed_count") or 0) >= 6
    )
    return {
        "post_export_stack_closure_ok": closure.get("post_export_stack_closure_ok"),
        "gates_ok_count": closure.get("gates_ok_count"),
        "integrated_closure_ok": closure.get("integrated_closure_ok"),
        "export_sync_ok": closure.get("export_sync_ok"),
        "post_export_observation_ok": closure.get("post_export_observation_ok"),
        "full_post_export_closure_ok": closure.get("full_post_export_closure_ok"),
        "post_export_extended_export_bundle_ok": closure.get("post_export_extended_export_bundle_ok"),
        "curated_reviewed_count": closure.get("curated_reviewed_count"),
        "post_export_stack_closure_headline_ok": headline_ok,
        "non_gating": True,
        "research_only": True,
        "note_ko": "P56 post-export stack closure [HYPO][NON_GATING]; P51–P55 전체 wired.",
    }


def _grand_post_export_closure_kpi(closure: dict[str, Any]) -> dict[str, Any]:
    headline_ok = (
        closure.get("grand_post_export_closure_ok") is True
        and closure.get("non_gating") is True
        and int(closure.get("gates_ok_count") or 0) >= 24
        and closure.get("post_export_stack_closure_ok") is True
        and closure.get("post_export_extended_export_bundle_ok") is True
        and closure.get("full_post_export_closure_ok") is True
        and closure.get("full_extension_closure_ok") is True
        and closure.get("integrated_closure_ok") is True
        and int(closure.get("curated_reviewed_count") or 0) >= 6
    )
    return {
        "grand_post_export_closure_ok": closure.get("grand_post_export_closure_ok"),
        "gates_ok_count": closure.get("gates_ok_count"),
        "post_export_stack_closure_ok": closure.get("post_export_stack_closure_ok"),
        "post_export_extended_export_bundle_ok": closure.get("post_export_extended_export_bundle_ok"),
        "full_post_export_closure_ok": closure.get("full_post_export_closure_ok"),
        "full_extension_closure_ok": closure.get("full_extension_closure_ok"),
        "integrated_closure_ok": closure.get("integrated_closure_ok"),
        "curated_reviewed_count": closure.get("curated_reviewed_count"),
        "grand_post_export_closure_headline_ok": headline_ok,
        "non_gating": True,
        "research_only": True,
        "note_ko": "P57 grand post-export closure [HYPO][NON_GATING]; P33–P56 전체 wired.",
    }


def _grand_export_bundle_vault_sync_kpi(sync: dict[str, Any]) -> dict[str, Any]:
    vault = sync.get("vault_mirror") if isinstance(sync.get("vault_mirror"), dict) else {}
    headline_ok = (
        sync.get("grand_export_bundle_vault_sync_ok") is True
        and sync.get("non_gating") is True
        and sync.get("grand_post_export_closure_ok") is True
        and sync.get("base_export_sync_ok") is True
        and sync.get("cloud_upload_forbidden") is True
        and sync.get("cloud_upload_attempted") is False
        and int(sync.get("manifest_files_present_count") or 0) >= 16
        and vault.get("vault_mirror_ok") is True
    )
    return {
        "grand_export_bundle_vault_sync_ok": sync.get("grand_export_bundle_vault_sync_ok"),
        "grand_post_export_closure_ok": sync.get("grand_post_export_closure_ok"),
        "base_export_sync_ok": sync.get("base_export_sync_ok"),
        "manifest_files_present_count": sync.get("manifest_files_present_count"),
        "gates_ok_count": sync.get("gates_ok_count"),
        "cloud_upload_forbidden": sync.get("cloud_upload_forbidden"),
        "vault_mirror_skipped": vault.get("vault_mirror_skipped"),
        "grand_export_bundle_vault_sync_headline_ok": headline_ok,
        "non_gating": True,
        "research_only": True,
        "note_ko": "P58 grand export bundle vault sync [HYPO][NON_GATING]; P57 closure + vault grand/ mirror; cloud upload 금지.",
    }


def _post_grand_passive_observation_kpi(obs: dict[str, Any]) -> dict[str, Any]:
    headline_ok = (
        obs.get("observation_ok") is True
        and obs.get("non_gating") is True
        and obs.get("grand_export_bundle_vault_sync_ok") is True
        and obs.get("grand_post_export_closure_ok") is True
        and obs.get("passive_observation_ok") is True
        and obs.get("export_ingest_kpi_ok") is True
        and obs.get("curated_milestone_ok") is True
        and obs.get("weekly_task_ready") is True
        and obs.get("interpret_cpu_guard_ok") is True
    )
    return {
        "observation_ok": obs.get("observation_ok"),
        "grand_export_bundle_vault_sync_ok": obs.get("grand_export_bundle_vault_sync_ok"),
        "grand_post_export_closure_ok": obs.get("grand_post_export_closure_ok"),
        "passive_observation_ok": obs.get("passive_observation_ok"),
        "export_ingest_kpi_ok": obs.get("export_ingest_kpi_ok"),
        "curated_milestone_ok": obs.get("curated_milestone_ok"),
        "curated_reviewed_count": obs.get("curated_reviewed_count"),
        "curated_pending_human_review": obs.get("curated_pending_human_review"),
        "weekly_task_ready": obs.get("weekly_task_ready"),
        "interpret_gpu_train_attempted": obs.get("interpret_gpu_train_attempted"),
        "post_grand_passive_observation_headline_ok": headline_ok,
        "non_gating": True,
        "research_only": True,
        "note_ko": "P59 post-grand passive+vault observability [HYPO][NON_GATING]; auto-training 금지.",
    }


def _full_grand_stack_final_closure_kpi(closure: dict[str, Any]) -> dict[str, Any]:
    headline_ok = (
        closure.get("full_grand_stack_final_closure_ok") is True
        and closure.get("non_gating") is True
        and int(closure.get("gates_ok_count") or 0) >= 27
        and closure.get("grand_post_export_closure_ok") is True
        and closure.get("grand_export_bundle_vault_sync_ok") is True
        and closure.get("post_grand_passive_observation_ok") is True
        and closure.get("post_export_stack_closure_ok") is True
        and closure.get("full_post_export_closure_ok") is True
        and closure.get("full_extension_closure_ok") is True
        and closure.get("integrated_closure_ok") is True
        and int(closure.get("curated_reviewed_count") or 0) >= 6
    )
    return {
        "full_grand_stack_final_closure_ok": closure.get("full_grand_stack_final_closure_ok"),
        "gates_ok_count": closure.get("gates_ok_count"),
        "grand_post_export_closure_ok": closure.get("grand_post_export_closure_ok"),
        "grand_export_bundle_vault_sync_ok": closure.get("grand_export_bundle_vault_sync_ok"),
        "post_grand_passive_observation_ok": closure.get("post_grand_passive_observation_ok"),
        "post_export_stack_closure_ok": closure.get("post_export_stack_closure_ok"),
        "full_post_export_closure_ok": closure.get("full_post_export_closure_ok"),
        "full_extension_closure_ok": closure.get("full_extension_closure_ok"),
        "integrated_closure_ok": closure.get("integrated_closure_ok"),
        "curated_reviewed_count": closure.get("curated_reviewed_count"),
        "full_grand_stack_final_closure_headline_ok": headline_ok,
        "non_gating": True,
        "research_only": True,
        "note_ko": "P60 full grand-stack final closure [HYPO][NON_GATING]; P33–P59 전체 wired.",
    }


def _grand_stack_extension_export_bundle_kpi(bundle: dict[str, Any]) -> dict[str, Any]:
    gates = bundle.get("gates") if isinstance(bundle.get("gates"), dict) else {}
    snap = bundle.get("rollup_snapshot") if isinstance(bundle.get("rollup_snapshot"), dict) else {}
    headline_ok = (
        bundle.get("grand_stack_extension_export_bundle_ok") is True
        and bundle.get("non_gating") is True
        and int(bundle.get("gates_ok_count") or 0) >= 28
        and bundle.get("post_export_extended_export_bundle_ok") is True
        and bundle.get("full_grand_stack_final_closure_ok") is True
        and snap.get("grand_export_bundle_vault_sync_ok") is True
        and snap.get("post_grand_passive_observation_ok") is True
        and snap.get("full_grand_stack_final_closure_ok") is True
        and snap.get("cloud_upload_forbidden") is True
    )
    return {
        "grand_stack_extension_export_bundle_ok": bundle.get("grand_stack_extension_export_bundle_ok"),
        "gates_ok_count": bundle.get("gates_ok_count"),
        "post_export_extended_export_bundle_ok": bundle.get("post_export_extended_export_bundle_ok"),
        "full_grand_stack_final_closure_ok": bundle.get("full_grand_stack_final_closure_ok"),
        "curated_reviewed_count": snap.get("curated_reviewed_count"),
        "grand_stack_extension_export_headline_ok": headline_ok,
        "non_gating": True,
        "research_only": True,
        "note_ko": "P61 grand-stack extension export bundle [HYPO][NON_GATING]; P33–P60 NotebookLM/ops 참고용.",
    }


def _grand_stack_stack_closure_kpi(closure: dict[str, Any]) -> dict[str, Any]:
    headline_ok = (
        closure.get("grand_stack_stack_closure_ok") is True
        and closure.get("non_gating") is True
        and int(closure.get("gates_ok_count") or 0) >= 5
        and closure.get("grand_post_export_closure_ok") is True
        and closure.get("grand_export_bundle_vault_sync_ok") is True
        and closure.get("post_grand_passive_observation_ok") is True
        and closure.get("full_grand_stack_final_closure_ok") is True
        and closure.get("grand_stack_extension_export_bundle_ok") is True
        and int(closure.get("curated_reviewed_count") or 0) >= 6
    )
    return {
        "grand_stack_stack_closure_ok": closure.get("grand_stack_stack_closure_ok"),
        "gates_ok_count": closure.get("gates_ok_count"),
        "grand_post_export_closure_ok": closure.get("grand_post_export_closure_ok"),
        "grand_export_bundle_vault_sync_ok": closure.get("grand_export_bundle_vault_sync_ok"),
        "post_grand_passive_observation_ok": closure.get("post_grand_passive_observation_ok"),
        "full_grand_stack_final_closure_ok": closure.get("full_grand_stack_final_closure_ok"),
        "grand_stack_extension_export_bundle_ok": closure.get("grand_stack_extension_export_bundle_ok"),
        "curated_reviewed_count": closure.get("curated_reviewed_count"),
        "grand_stack_stack_closure_headline_ok": headline_ok,
        "non_gating": True,
        "research_only": True,
        "note_ko": "P62 grand-stack stack closure [HYPO][NON_GATING]; P57–P61 전체 wired.",
    }


def _ultra_grand_post_export_closure_kpi(closure: dict[str, Any]) -> dict[str, Any]:
    headline_ok = (
        closure.get("ultra_grand_post_export_closure_ok") is True
        and closure.get("non_gating") is True
        and int(closure.get("gates_ok_count") or 0) >= 30
        and closure.get("grand_stack_stack_closure_ok") is True
        and closure.get("grand_stack_extension_export_bundle_ok") is True
        and closure.get("full_grand_stack_final_closure_ok") is True
        and closure.get("grand_post_export_closure_ok") is True
        and closure.get("post_export_stack_closure_ok") is True
        and closure.get("full_extension_closure_ok") is True
        and closure.get("integrated_closure_ok") is True
        and int(closure.get("curated_reviewed_count") or 0) >= 6
    )
    return {
        "ultra_grand_post_export_closure_ok": closure.get("ultra_grand_post_export_closure_ok"),
        "gates_ok_count": closure.get("gates_ok_count"),
        "grand_stack_stack_closure_ok": closure.get("grand_stack_stack_closure_ok"),
        "grand_stack_extension_export_bundle_ok": closure.get("grand_stack_extension_export_bundle_ok"),
        "full_grand_stack_final_closure_ok": closure.get("full_grand_stack_final_closure_ok"),
        "grand_post_export_closure_ok": closure.get("grand_post_export_closure_ok"),
        "post_export_stack_closure_ok": closure.get("post_export_stack_closure_ok"),
        "full_extension_closure_ok": closure.get("full_extension_closure_ok"),
        "integrated_closure_ok": closure.get("integrated_closure_ok"),
        "curated_reviewed_count": closure.get("curated_reviewed_count"),
        "ultra_grand_post_export_closure_headline_ok": headline_ok,
        "non_gating": True,
        "research_only": True,
        "note_ko": "P63 ultra-grand post-export closure [HYPO][NON_GATING]; P33–P62 전체 wired.",
    }


def _ultra_grand_export_bundle_vault_sync_kpi(sync: dict[str, Any]) -> dict[str, Any]:
    vault = sync.get("vault_mirror") if isinstance(sync.get("vault_mirror"), dict) else {}
    headline_ok = (
        sync.get("ultra_grand_export_bundle_vault_sync_ok") is True
        and sync.get("non_gating") is True
        and sync.get("ultra_grand_post_export_closure_ok") is True
        and sync.get("grand_export_bundle_vault_sync_ok") is True
        and sync.get("cloud_upload_forbidden") is True
        and sync.get("cloud_upload_attempted") is False
        and int(sync.get("manifest_files_present_count") or 0) >= 30
        and vault.get("vault_mirror_ok") is True
    )
    return {
        "ultra_grand_export_bundle_vault_sync_ok": sync.get("ultra_grand_export_bundle_vault_sync_ok"),
        "ultra_grand_post_export_closure_ok": sync.get("ultra_grand_post_export_closure_ok"),
        "grand_export_bundle_vault_sync_ok": sync.get("grand_export_bundle_vault_sync_ok"),
        "manifest_files_present_count": sync.get("manifest_files_present_count"),
        "gates_ok_count": sync.get("gates_ok_count"),
        "cloud_upload_forbidden": sync.get("cloud_upload_forbidden"),
        "vault_mirror_skipped": vault.get("vault_mirror_skipped"),
        "ultra_grand_export_bundle_vault_sync_headline_ok": headline_ok,
        "non_gating": True,
        "research_only": True,
        "note_ko": "P64 ultra-grand export bundle vault sync [HYPO][NON_GATING]; P63 closure + vault ultra_grand/ mirror; cloud upload 금지.",
    }


def _post_ultra_grand_passive_observation_kpi(obs: dict[str, Any]) -> dict[str, Any]:
    headline_ok = (
        obs.get("observation_ok") is True
        and obs.get("non_gating") is True
        and obs.get("ultra_grand_export_bundle_vault_sync_ok") is True
        and obs.get("ultra_grand_post_export_closure_ok") is True
        and obs.get("passive_observation_ok") is True
        and obs.get("export_ingest_kpi_ok") is True
        and obs.get("curated_milestone_ok") is True
        and obs.get("weekly_task_ready") is True
        and obs.get("interpret_cpu_guard_ok") is True
    )
    return {
        "observation_ok": obs.get("observation_ok"),
        "ultra_grand_export_bundle_vault_sync_ok": obs.get("ultra_grand_export_bundle_vault_sync_ok"),
        "ultra_grand_post_export_closure_ok": obs.get("ultra_grand_post_export_closure_ok"),
        "passive_observation_ok": obs.get("passive_observation_ok"),
        "export_ingest_kpi_ok": obs.get("export_ingest_kpi_ok"),
        "curated_milestone_ok": obs.get("curated_milestone_ok"),
        "curated_reviewed_count": obs.get("curated_reviewed_count"),
        "curated_pending_human_review": obs.get("curated_pending_human_review"),
        "weekly_task_ready": obs.get("weekly_task_ready"),
        "interpret_gpu_train_attempted": obs.get("interpret_gpu_train_attempted"),
        "post_ultra_grand_passive_observation_headline_ok": headline_ok,
        "non_gating": True,
        "research_only": True,
        "note_ko": "P65 post-ultra-grand passive+vault observability [HYPO][NON_GATING]; auto-training 금지.",
    }


def _full_ultra_grand_stack_final_closure_kpi(closure: dict[str, Any]) -> dict[str, Any]:
    headline_ok = (
        closure.get("full_ultra_grand_stack_final_closure_ok") is True
        and closure.get("non_gating") is True
        and int(closure.get("gates_ok_count") or 0) >= 33
        and closure.get("ultra_grand_post_export_closure_ok") is True
        and closure.get("ultra_grand_export_bundle_vault_sync_ok") is True
        and closure.get("post_ultra_grand_passive_observation_ok") is True
        and closure.get("post_export_stack_closure_ok") is True
        and closure.get("full_post_export_closure_ok") is True
        and closure.get("full_extension_closure_ok") is True
        and closure.get("integrated_closure_ok") is True
        and int(closure.get("curated_reviewed_count") or 0) >= 6
    )
    return {
        "full_ultra_grand_stack_final_closure_ok": closure.get("full_ultra_grand_stack_final_closure_ok"),
        "gates_ok_count": closure.get("gates_ok_count"),
        "ultra_grand_post_export_closure_ok": closure.get("ultra_grand_post_export_closure_ok"),
        "ultra_grand_export_bundle_vault_sync_ok": closure.get("ultra_grand_export_bundle_vault_sync_ok"),
        "post_ultra_grand_passive_observation_ok": closure.get("post_ultra_grand_passive_observation_ok"),
        "post_export_stack_closure_ok": closure.get("post_export_stack_closure_ok"),
        "full_post_export_closure_ok": closure.get("full_post_export_closure_ok"),
        "full_extension_closure_ok": closure.get("full_extension_closure_ok"),
        "integrated_closure_ok": closure.get("integrated_closure_ok"),
        "curated_reviewed_count": closure.get("curated_reviewed_count"),
        "full_ultra_grand_stack_final_closure_headline_ok": headline_ok,
        "non_gating": True,
        "research_only": True,
        "note_ko": "P66 full ultra-grand-stack final closure [HYPO][NON_GATING]; P33–P65 전체 wired.",
    }


def _ultra_grand_extension_export_bundle_kpi(bundle: dict[str, Any]) -> dict[str, Any]:
    snap = bundle.get("rollup_snapshot") if isinstance(bundle.get("rollup_snapshot"), dict) else {}
    headline_ok = (
        bundle.get("ultra_grand_extension_export_bundle_ok") is True
        and bundle.get("non_gating") is True
        and int(bundle.get("gates_ok_count") or 0) >= 34
        and bundle.get("post_export_extended_export_bundle_ok") is True
        and bundle.get("full_ultra_grand_stack_final_closure_ok") is True
        and snap.get("ultra_grand_export_bundle_vault_sync_ok") is True
        and snap.get("post_ultra_grand_passive_observation_ok") is True
        and snap.get("full_ultra_grand_stack_final_closure_ok") is True
        and snap.get("cloud_upload_forbidden") is True
    )
    return {
        "ultra_grand_extension_export_bundle_ok": bundle.get("ultra_grand_extension_export_bundle_ok"),
        "gates_ok_count": bundle.get("gates_ok_count"),
        "post_export_extended_export_bundle_ok": bundle.get("post_export_extended_export_bundle_ok"),
        "full_ultra_grand_stack_final_closure_ok": bundle.get("full_ultra_grand_stack_final_closure_ok"),
        "curated_reviewed_count": snap.get("curated_reviewed_count"),
        "ultra_grand_extension_export_headline_ok": headline_ok,
        "non_gating": True,
        "research_only": True,
        "note_ko": "P67 ultra-grand extension export bundle [HYPO][NON_GATING]; P33–P66 NotebookLM/ops 참고용.",
    }


def _ultra_grand_stack_stack_closure_kpi(closure: dict[str, Any]) -> dict[str, Any]:
    headline_ok = (
        closure.get("ultra_grand_stack_stack_closure_ok") is True
        and closure.get("non_gating") is True
        and int(closure.get("gates_ok_count") or 0) >= 5
        and closure.get("ultra_grand_post_export_closure_ok") is True
        and closure.get("ultra_grand_export_bundle_vault_sync_ok") is True
        and closure.get("post_ultra_grand_passive_observation_ok") is True
        and closure.get("full_ultra_grand_stack_final_closure_ok") is True
        and closure.get("ultra_grand_extension_export_bundle_ok") is True
        and closure.get("ultra_grand_stack_breakpoint_freeze") is True
        and int(closure.get("curated_reviewed_count") or 0) >= 6
    )
    return {
        "ultra_grand_stack_stack_closure_ok": closure.get("ultra_grand_stack_stack_closure_ok"),
        "ultra_grand_stack_breakpoint_freeze": closure.get("ultra_grand_stack_breakpoint_freeze"),
        "gates_ok_count": closure.get("gates_ok_count"),
        "ultra_grand_post_export_closure_ok": closure.get("ultra_grand_post_export_closure_ok"),
        "ultra_grand_export_bundle_vault_sync_ok": closure.get("ultra_grand_export_bundle_vault_sync_ok"),
        "post_ultra_grand_passive_observation_ok": closure.get("post_ultra_grand_passive_observation_ok"),
        "full_ultra_grand_stack_final_closure_ok": closure.get("full_ultra_grand_stack_final_closure_ok"),
        "ultra_grand_extension_export_bundle_ok": closure.get("ultra_grand_extension_export_bundle_ok"),
        "curated_reviewed_count": closure.get("curated_reviewed_count"),
        "ultra_grand_stack_stack_closure_headline_ok": headline_ok,
        "non_gating": True,
        "research_only": True,
        "note_ko": "P68 ultra-grand stack closure [HYPO][NON_GATING]; P63–P67 B-track breakpoint freeze.",
    }


def _post_breakpoint_passive_drift_observation_kpi(obs: dict[str, Any]) -> dict[str, Any]:
    snap = obs.get("snapshot") if isinstance(obs.get("snapshot"), dict) else {}
    headline_ok = (
        obs.get("observation_ok") is True
        and obs.get("non_gating") is True
        and obs.get("ultra_grand_stack_breakpoint_freeze") is True
        and obs.get("drift_regression_detected") is False
        and obs.get("passive_observation_ok") is True
        and obs.get("weekly_task_ready") is True
        and snap.get("ultra_grand_stack_stack_closure_headline_ok") is True
        and obs.get("tier_inflation_forbidden") is True
    )
    return {
        "observation_ok": obs.get("observation_ok"),
        "ultra_grand_stack_breakpoint_freeze": obs.get("ultra_grand_stack_breakpoint_freeze"),
        "drift_regression_detected": obs.get("drift_regression_detected"),
        "passive_observation_ok": obs.get("passive_observation_ok"),
        "weekly_task_ready": obs.get("weekly_task_ready"),
        "gates_ok_count": snap.get("gates_ok_count"),
        "weekly_version": snap.get("weekly_version"),
        "post_breakpoint_passive_drift_headline_ok": headline_ok,
        "non_gating": True,
        "research_only": True,
        "note_ko": "Post-P68 passive drift observation [HYPO][NON_GATING]; P69+ tier inflation 금지.",
    }


def _curated_bulk_human_review_kpi(bulk: dict[str, Any]) -> dict[str, Any]:
    headline_ok = (
        bulk.get("bulk_human_review_ok") is True
        and bulk.get("non_gating") is True
        and bulk.get("ultra_grand_stack_breakpoint_freeze") is True
        and bulk.get("human_gate_ack_ok") is True
        and int(bulk.get("curated_reviewed_count") or 0) >= 6
        and bulk.get("milestone_ok") is True
        and bulk.get("tier_inflation_forbidden") is True
    )
    return {
        "bulk_human_review_ok": bulk.get("bulk_human_review_ok"),
        "curated_reviewed_count": bulk.get("curated_reviewed_count"),
        "curated_pending_human_review": bulk.get("curated_pending_human_review"),
        "curated_registry_total": bulk.get("curated_registry_total"),
        "human_gate_ack_ok": bulk.get("human_gate_ack_ok"),
        "milestone_ok": bulk.get("milestone_ok"),
        "curated_bulk_human_review_headline_ok": headline_ok,
        "non_gating": True,
        "research_only": True,
        "note_ko": "Post-P68 curated bulk human review [HYPO][NON_GATING]; human-gate only.",
    }


def _ops_closure_kpi(ops: dict[str, Any]) -> dict[str, Any]:
    headline_ok = (
        ops.get("closure_ok") is True
        and ops.get("full_stack_closure_ok") is True
        and ops.get("version") in ("2.0.0", "2.1.0", "2.2.0", "2.3.0", "2.4.0", "2.5.0", "2.6.0", "2.7.0", "2.8.0", "2.9.0", "3.0.0", "3.1.0", "3.2.0", "3.3.0", "3.4.0", "3.5.0", "3.6.0", "3.7.0", "3.8.0", "3.9.0", "4.0.0", "4.1.0", "4.2.0", "4.3.0", "4.4.0", "4.5.0", "4.6.0", "4.7.0", "4.8.0", "4.9.0", "5.0.0", "5.1.0", "5.2.0")
    )
    items = ops.get("items") if isinstance(ops.get("items"), dict) else {}
    return {
        "closure_ok": ops.get("closure_ok"),
        "full_stack_closure_ok": ops.get("full_stack_closure_ok"),
        "ops_closure_version": ops.get("version"),
        "lens_stack_items_ok": all(
            (items.get(k) or {}).get("ok") is True
            for k in (
                "9_cross_lens_p33",
                "10_passive_observation_p34",
                "11_conflict_resolver_p35",
                "12_disagreement_cross_p36",
                "13_lens_stack_rollup_p39",
                "14_passive_integrated_p40",
                "15_clinical_validation_p41",
                "16_full_stack_export_p42",
                "17_gpu_passive_curated_p43",
                "18_stack_final_closure_p44",
                "19_curated_milestone_p45",
                "20_gpu_interpret_observation_p46",
                "21_stack_extension_closure_p47",
                "22_extended_export_bundle_p48",
                "23_full_extension_closure_p49",
                "24_post_extension_observation_p50",
                "25_integrated_stack_closure_p51",
                "26_notebooklm_export_sync_p52",
                "27_post_export_passive_observation_p53",
                "28_full_post_export_closure_p54",
                "29_post_export_extended_export_bundle_p55",
                "30_post_export_stack_closure_p56",
                "31_grand_post_export_closure_p57",
                "32_grand_export_bundle_vault_sync_p58",
                "33_post_grand_passive_observation_p59",
                "34_full_grand_stack_final_closure_p60",
                "35_grand_stack_extension_export_bundle_p61",
                "36_grand_stack_stack_closure_p62",
                "37_ultra_grand_post_export_closure_p63",
                "38_ultra_grand_export_bundle_vault_sync_p64",
                "39_post_ultra_grand_passive_observation_p65",
                "40_full_ultra_grand_stack_final_closure_p66",
                "41_ultra_grand_extension_export_bundle_p67",
                "42_ultra_grand_stack_stack_closure_p68",
                "43_post_p68_maintenance_bundle",
            )
        ),
        "full_stack_closure_headline_ok": headline_ok,
        "non_gating": True,
        "note_ko": "Ops closure v2 [HYPO] — P26 기본 8항 + P33–P36 lens stack; Track A 합선 금지.",
    }


def _disagreement_resolver_cross_kpi(cross: dict[str, Any]) -> dict[str, Any]:
    headline_ok = (
        cross.get("kpi_ok") is True
        and cross.get("non_gating") is True
        and int(cross.get("disagreement_count") or 0) >= 1
        and int(cross.get("disagreement_resolver_wired_count") or 0) >= 1
        and int(cross.get("curated_learning_pointer_count") or 0) >= 1
    )
    return {
        "lane": "physician_gold_only",
        "disagreement_count": cross.get("disagreement_count"),
        "disagreement_resolver_wired_count": cross.get("disagreement_resolver_wired_count"),
        "disagreement_lens_conflict_cross_rate": cross.get("disagreement_lens_conflict_cross_rate"),
        "disagreement_physician_authority_rate": cross.get("disagreement_physician_authority_rate"),
        "curated_learning_pointer_count": cross.get("curated_learning_pointer_count"),
        "disagreement_resolver_headline_ok": headline_ok,
        "non_gating": True,
        "note_ko": "불일치×resolver 교차 [HYPO][NON_GATING]; human-curated만; auto-training 금지.",
    }


def _conflict_resolver_kpi(resolver: dict[str, Any]) -> dict[str, Any]:
    agreement = resolver.get("agreement_rate_l5_aligned")
    headline_ok = (
        resolver.get("kpi_ok") is True
        and resolver.get("non_gating") is True
        and resolver.get("physician_gold_conflict_resolver_ok") is True
        and int(resolver.get("conflict_resolver_wired_count") or 0) >= 1
        and isinstance(agreement, (int, float))
    )
    return {
        "lane": "physician_gold_only",
        "conflict_resolver_wired_count": resolver.get("conflict_resolver_wired_count"),
        "agreement_rate_l5_aligned": agreement,
        "resolver_status_counts": resolver.get("resolver_status_counts"),
        "final_action_observed_counts": resolver.get("final_action_observed_counts"),
        "conflict_resolver_headline_ok": headline_ok,
        "non_gating": True,
        "note_ko": "Field→Lens(3)→Conflict [HYPO][NON_GATING] — 사상 주·명리/성경 보; constitution overwrite 금지.",
    }


def _l0_safety_kpi(l0: dict[str, Any]) -> dict[str, Any]:
    all_ledger = l0.get("all_ledger") if isinstance(l0.get("all_ledger"), dict) else {}
    gold = l0.get("physician_gold_only") if isinstance(l0.get("physician_gold_only"), dict) else {}
    headline_ok = (
        l0.get("kpi_ok") is True
        and int(all_ledger.get("l0_router_wired_count") or 0) >= 1
        and int(all_ledger.get("l0_summary_trigger_events") or 0) >= 1
    )
    return {
        "lane": "physician_gold_only",
        "l0_router_wired_rate": all_ledger.get("l0_router_wired_rate"),
        "l0_router_wired_count": all_ledger.get("l0_router_wired_count"),
        "l0_trigger_count": all_ledger.get("l0_trigger_count"),
        "l0_summary_trigger_events": all_ledger.get("l0_summary_trigger_events"),
        "physician_gold_l0_wired_rate": gold.get("l0_router_wired_rate"),
        "l0_safety_headline_ok": headline_ok,
        "non_gating": True,
        "note_ko": "L0 red-flag [HYPO] — 응급 자동 dispatch·사상 헤드라인 합선 금지.",
    }


def build() -> dict[str, Any]:
    summary = _load(SUMMARY)
    drafts = _load(DRAFTS)
    multi = _load(MULTI)
    dual = _load(DUAL)
    delta = _load(DELTA)
    myeongni = _load(MYEONGNI_KPI)
    logos = _load(LOGOS_KPI)
    cross = _load(CROSS_LENS_KPI)
    passive = _load(PASSIVE_OBS)
    resolver = _load(CONFLICT_RESOLVER)
    disagreement_cross = _load(DISAGREEMENT_CROSS)
    export_ingest = _load(EXPORT_INGEST_KPI)
    lens_stack_rollup = _load(LENS_STACK_ROLLUP)
    passive_integrated = _load(PASSIVE_INTEGRATED)
    clinical_stub = _load(CLINICAL_STUB)
    full_stack_bundle = _load(FULL_STACK_BUNDLE)
    extended_stack_bundle = _load(EXTENDED_STACK_BUNDLE)
    p43_observability = _load(P43_OBSERVABILITY)
    stack_final_closure = _load(STACK_FINAL_CLOSURE)
    curated_milestone = _load(CURATED_MILESTONE)
    gpu_interpret_obs = _load(GPU_INTERPRET_OBS)
    stack_extension_closure = _load(STACK_EXTENSION_CLOSURE)
    full_extension_closure = _load(FULL_EXTENSION_CLOSURE)
    post_extension_obs = _load(POST_EXTENSION_OBS)
    integrated_stack_closure = _load(INTEGRATED_STACK_CLOSURE)
    notebooklm_export_sync = _load(NOTEBOOKLM_EXPORT_SYNC)
    post_export_passive_obs = _load(POST_EXPORT_PASSIVE_OBS)
    full_post_export_closure = _load(FULL_POST_EXPORT_CLOSURE)
    post_export_extended_bundle = _load(POST_EXPORT_EXTENDED_BUNDLE)
    post_export_stack_closure = _load(POST_EXPORT_STACK_CLOSURE)
    grand_post_export_closure = _load(GRAND_POST_EXPORT_CLOSURE)
    grand_export_bundle_vault_sync = _load(GRAND_EXPORT_BUNDLE_VAULT_SYNC)
    post_grand_passive_obs = _load(POST_GRAND_PASSIVE_OBS)
    full_grand_stack_final_closure = _load(FULL_GRAND_STACK_FINAL_CLOSURE)
    grand_stack_extension_export_bundle = _load(GRAND_STACK_EXTENSION_EXPORT_BUNDLE)
    grand_stack_stack_closure = _load(GRAND_STACK_STACK_CLOSURE)
    ultra_grand_post_export_closure = _load(ULTRA_GRAND_POST_EXPORT_CLOSURE)
    ultra_grand_export_bundle_vault_sync = _load(ULTRA_GRAND_EXPORT_BUNDLE_VAULT_SYNC)
    post_ultra_grand_passive_obs = _load(POST_ULTRA_GRAND_PASSIVE_OBS)
    full_ultra_grand_stack_final_closure = _load(FULL_ULTRA_GRAND_STACK_FINAL_CLOSURE)
    ultra_grand_extension_export_bundle = _load(ULTRA_GRAND_EXTENSION_EXPORT_BUNDLE)
    ultra_grand_stack_stack_closure = _load(ULTRA_GRAND_STACK_STACK_CLOSURE)
    post_breakpoint_passive_drift = _load(POST_BREAKPOINT_PASSIVE_DRIFT)
    curated_bulk_human_review = _load(CURATED_BULK_HUMAN_REVIEW)
    ops_closure = _load(OPS_CLOSURE)
    l0 = _load(L0_KPI)
    churn = _multiturn_churn_kpi(summary, multi)
    headline = _dual_lane_headline_kpi(dual)
    l5_myeongni = _l5_myeongni_kpi(myeongni)
    l6_logos = _l6_logos_kpi(logos)
    l7_cross_lens = _cross_lens_kpi(cross)
    passive_obs = _passive_observation_kpi(passive)
    conflict_resolver = _conflict_resolver_kpi(resolver)
    disagreement_resolver_cross = _disagreement_resolver_cross_kpi(disagreement_cross)
    export_ingest_kpi = _export_ingest_kpi(export_ingest)
    lens_stack_rollup_kpi = _lens_stack_rollup_kpi(lens_stack_rollup)
    passive_integrated_rollup_kpi = _passive_integrated_rollup_kpi(passive_integrated)
    clinical_validation_stub_kpi = _clinical_validation_stub_kpi(clinical_stub)
    full_stack_export_bundle_kpi = _full_stack_export_bundle_kpi(full_stack_bundle)
    extended_stack_export_bundle_kpi = _extended_stack_export_bundle_kpi(extended_stack_bundle)
    p43_observability_kpi = _p43_observability_kpi(p43_observability)
    stack_final_closure_kpi = _stack_final_closure_kpi(stack_final_closure)
    curated_review_milestone_kpi = _curated_review_milestone_kpi(curated_milestone)
    gpu_interpret_observation_kpi = _gpu_interpret_observation_kpi(gpu_interpret_obs)
    stack_extension_closure_kpi = _stack_extension_closure_kpi(stack_extension_closure)
    full_extension_closure_kpi = _full_extension_closure_kpi(full_extension_closure)
    post_extension_observation_kpi = _post_extension_observation_kpi(post_extension_obs)
    integrated_stack_closure_kpi = _integrated_stack_closure_kpi(integrated_stack_closure)
    notebooklm_export_sync_kpi = _notebooklm_export_sync_kpi(notebooklm_export_sync)
    post_export_passive_observation_kpi = _post_export_passive_observation_kpi(post_export_passive_obs)
    full_post_export_closure_kpi = _full_post_export_closure_kpi(full_post_export_closure)
    post_export_extended_export_bundle_kpi = _post_export_extended_export_bundle_kpi(post_export_extended_bundle)
    post_export_stack_closure_kpi = _post_export_stack_closure_kpi(post_export_stack_closure)
    grand_post_export_closure_kpi = _grand_post_export_closure_kpi(grand_post_export_closure)
    grand_export_bundle_vault_sync_kpi = _grand_export_bundle_vault_sync_kpi(grand_export_bundle_vault_sync)
    post_grand_passive_observation_kpi = _post_grand_passive_observation_kpi(post_grand_passive_obs)
    full_grand_stack_final_closure_kpi = _full_grand_stack_final_closure_kpi(full_grand_stack_final_closure)
    grand_stack_extension_export_bundle_kpi = _grand_stack_extension_export_bundle_kpi(grand_stack_extension_export_bundle)
    grand_stack_stack_closure_kpi = _grand_stack_stack_closure_kpi(grand_stack_stack_closure)
    ultra_grand_post_export_closure_kpi = _ultra_grand_post_export_closure_kpi(ultra_grand_post_export_closure)
    ultra_grand_export_bundle_vault_sync_kpi = _ultra_grand_export_bundle_vault_sync_kpi(ultra_grand_export_bundle_vault_sync)
    post_ultra_grand_passive_observation_kpi = _post_ultra_grand_passive_observation_kpi(post_ultra_grand_passive_obs)
    full_ultra_grand_stack_final_closure_kpi = _full_ultra_grand_stack_final_closure_kpi(
        full_ultra_grand_stack_final_closure
    )
    ultra_grand_extension_export_bundle_kpi = _ultra_grand_extension_export_bundle_kpi(
        ultra_grand_extension_export_bundle
    )
    ultra_grand_stack_stack_closure_kpi = _ultra_grand_stack_stack_closure_kpi(ultra_grand_stack_stack_closure)
    post_breakpoint_passive_drift_observation_kpi = _post_breakpoint_passive_drift_observation_kpi(
        post_breakpoint_passive_drift
    )
    curated_bulk_human_review_kpi = _curated_bulk_human_review_kpi(curated_bulk_human_review)
    ops_closure_kpi = _ops_closure_kpi(ops_closure)
    l0_safety = _l0_safety_kpi(l0)
    weekly_ok = summary.get("summary_ok") is True and drafts.get("draft_ok") is True
    return {
        "schema": "encounter_sequence_weekly_report_v1",
        "version": "5.6.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "domain_lane": "tkm_korean_han_medicine",
        "sasang_primary": True,
        "send_gate": "HOLD",
        "weekly_ok": weekly_ok,
        "headline_kpi": headline,
        "physician_agreement_rate": headline.get("clinic_match_rate"),
        "encounter_match_rate": headline.get("encounter_match_rate"),
        "sequence_count": headline.get("encounter_sequence_count"),
        "l0_red_flag_trigger_events": summary.get("l0_red_flag_trigger_events"),
        "disagreement_draft_count": drafts.get("disagreement_draft_count"),
        "multiturn_churn_kpi": churn,
        "match_rate_delta_kpi": {
            "clinic_match_rate": delta.get("clinic_match_rate"),
            "encounter_match_rate": delta.get("encounter_match_rate"),
            "match_rate_delta_encounter_minus_clinic": delta.get("match_rate_delta_encounter_minus_clinic"),
            "encounter_breakdown": delta.get("encounter_breakdown"),
            "delta_kpi_ok": delta.get("delta_kpi_ok"),
        },
        "l5_myeongni_kpi": l5_myeongni,
        "l6_logos_kpi": l6_logos,
        "l7_cross_lens_kpi": l7_cross_lens,
        "passive_observation_kpi": passive_obs,
        "conflict_resolver_kpi": conflict_resolver,
        "disagreement_resolver_cross_kpi": disagreement_resolver_cross,
        "export_ingest_kpi": export_ingest_kpi,
        "lens_stack_rollup_kpi": lens_stack_rollup_kpi,
        "passive_integrated_rollup_kpi": passive_integrated_rollup_kpi,
        "clinical_validation_stub_kpi": clinical_validation_stub_kpi,
        "full_stack_export_bundle_kpi": full_stack_export_bundle_kpi,
        "extended_stack_export_bundle_kpi": extended_stack_export_bundle_kpi,
        "p43_observability_kpi": p43_observability_kpi,
        "stack_final_closure_kpi": stack_final_closure_kpi,
        "curated_review_milestone_kpi": curated_review_milestone_kpi,
        "gpu_interpret_observation_kpi": gpu_interpret_observation_kpi,
        "stack_extension_closure_kpi": stack_extension_closure_kpi,
        "full_extension_closure_kpi": full_extension_closure_kpi,
        "post_extension_observation_kpi": post_extension_observation_kpi,
        "integrated_stack_closure_kpi": integrated_stack_closure_kpi,
        "notebooklm_export_sync_kpi": notebooklm_export_sync_kpi,
        "post_export_passive_observation_kpi": post_export_passive_observation_kpi,
        "full_post_export_closure_kpi": full_post_export_closure_kpi,
        "post_export_extended_export_bundle_kpi": post_export_extended_export_bundle_kpi,
        "post_export_stack_closure_kpi": post_export_stack_closure_kpi,
        "grand_post_export_closure_kpi": grand_post_export_closure_kpi,
        "grand_export_bundle_vault_sync_kpi": grand_export_bundle_vault_sync_kpi,
        "post_grand_passive_observation_kpi": post_grand_passive_observation_kpi,
        "full_grand_stack_final_closure_kpi": full_grand_stack_final_closure_kpi,
        "grand_stack_extension_export_bundle_kpi": grand_stack_extension_export_bundle_kpi,
        "grand_stack_stack_closure_kpi": grand_stack_stack_closure_kpi,
        "ultra_grand_post_export_closure_kpi": ultra_grand_post_export_closure_kpi,
        "ultra_grand_export_bundle_vault_sync_kpi": ultra_grand_export_bundle_vault_sync_kpi,
        "post_ultra_grand_passive_observation_kpi": post_ultra_grand_passive_observation_kpi,
        "full_ultra_grand_stack_final_closure_kpi": full_ultra_grand_stack_final_closure_kpi,
        "ultra_grand_extension_export_bundle_kpi": ultra_grand_extension_export_bundle_kpi,
        "ultra_grand_stack_stack_closure_kpi": ultra_grand_stack_stack_closure_kpi,
        "post_breakpoint_passive_drift_observation_kpi": post_breakpoint_passive_drift_observation_kpi,
        "curated_bulk_human_review_kpi": curated_bulk_human_review_kpi,
        "ops_closure_kpi": ops_closure_kpi,
        "l0_safety_kpi": l0_safety,
        "blended_all_ledger": {
            "sequence_count": summary.get("sequence_count"),
            "physician_agreement_rate": summary.get("physician_agreement_rate"),
            "avg_turn_count": summary.get("avg_turn_count"),
        },
        "summary_ref": str(SUMMARY).replace("\\", "/"),
        "drafts_ref": str(DRAFTS).replace("\\", "/"),
        "multiturn_smoke_ref": str(MULTI).replace("\\", "/"),
        "dual_lane_ref": str(DUAL).replace("\\", "/"),
        "match_rate_delta_ref": str(DELTA).replace("\\", "/"),
        "myeongni_kpi_ref": str(MYEONGNI_KPI).replace("\\", "/"),
        "logos_kpi_ref": str(LOGOS_KPI).replace("\\", "/"),
        "cross_lens_kpi_ref": str(CROSS_LENS_KPI).replace("\\", "/"),
        "passive_observation_ref": str(PASSIVE_OBS).replace("\\", "/"),
        "conflict_resolver_kpi_ref": str(CONFLICT_RESOLVER).replace("\\", "/"),
        "disagreement_resolver_cross_kpi_ref": str(DISAGREEMENT_CROSS).replace("\\", "/"),
        "export_ingest_kpi_ref": str(EXPORT_INGEST_KPI).replace("\\", "/"),
        "lens_stack_rollup_ref": str(LENS_STACK_ROLLUP).replace("\\", "/"),
        "passive_integrated_rollup_ref": str(PASSIVE_INTEGRATED).replace("\\", "/"),
        "clinical_validation_stub_ref": str(CLINICAL_STUB).replace("\\", "/"),
        "full_stack_export_bundle_ref": str(FULL_STACK_BUNDLE).replace("\\", "/"),
        "extended_stack_export_bundle_ref": str(EXTENDED_STACK_BUNDLE).replace("\\", "/"),
        "p43_observability_ref": str(P43_OBSERVABILITY).replace("\\", "/"),
        "stack_final_closure_ref": str(STACK_FINAL_CLOSURE).replace("\\", "/"),
        "curated_review_milestone_ref": str(CURATED_MILESTONE).replace("\\", "/"),
        "gpu_interpret_observation_ref": str(GPU_INTERPRET_OBS).replace("\\", "/"),
        "stack_extension_closure_ref": str(STACK_EXTENSION_CLOSURE).replace("\\", "/"),
        "full_extension_closure_ref": str(FULL_EXTENSION_CLOSURE).replace("\\", "/"),
        "post_extension_observation_ref": str(POST_EXTENSION_OBS).replace("\\", "/"),
        "integrated_stack_closure_ref": str(INTEGRATED_STACK_CLOSURE).replace("\\", "/"),
        "notebooklm_export_sync_ref": str(NOTEBOOKLM_EXPORT_SYNC).replace("\\", "/"),
        "post_export_passive_observation_ref": str(POST_EXPORT_PASSIVE_OBS).replace("\\", "/"),
        "full_post_export_closure_ref": str(FULL_POST_EXPORT_CLOSURE).replace("\\", "/"),
        "post_export_extended_export_bundle_ref": str(POST_EXPORT_EXTENDED_BUNDLE).replace("\\", "/"),
        "post_export_stack_closure_ref": str(POST_EXPORT_STACK_CLOSURE).replace("\\", "/"),
        "grand_post_export_closure_ref": str(GRAND_POST_EXPORT_CLOSURE).replace("\\", "/"),
        "grand_export_bundle_vault_sync_ref": str(GRAND_EXPORT_BUNDLE_VAULT_SYNC).replace("\\", "/"),
        "post_grand_passive_observation_ref": str(POST_GRAND_PASSIVE_OBS).replace("\\", "/"),
        "full_grand_stack_final_closure_ref": str(FULL_GRAND_STACK_FINAL_CLOSURE).replace("\\", "/"),
        "grand_stack_extension_export_bundle_ref": str(GRAND_STACK_EXTENSION_EXPORT_BUNDLE).replace("\\", "/"),
        "grand_stack_stack_closure_ref": str(GRAND_STACK_STACK_CLOSURE).replace("\\", "/"),
        "ultra_grand_post_export_closure_ref": str(ULTRA_GRAND_POST_EXPORT_CLOSURE).replace("\\", "/"),
        "ultra_grand_export_bundle_vault_sync_ref": str(ULTRA_GRAND_EXPORT_BUNDLE_VAULT_SYNC).replace("\\", "/"),
        "post_ultra_grand_passive_observation_ref": str(POST_ULTRA_GRAND_PASSIVE_OBS).replace("\\", "/"),
        "full_ultra_grand_stack_final_closure_ref": str(FULL_ULTRA_GRAND_STACK_FINAL_CLOSURE).replace("\\", "/"),
        "ultra_grand_extension_export_bundle_ref": str(ULTRA_GRAND_EXTENSION_EXPORT_BUNDLE).replace("\\", "/"),
        "ultra_grand_stack_stack_closure_ref": str(ULTRA_GRAND_STACK_STACK_CLOSURE).replace("\\", "/"),
        "post_breakpoint_passive_drift_observation_ref": str(POST_BREAKPOINT_PASSIVE_DRIFT).replace("\\", "/"),
        "curated_bulk_human_review_ref": str(CURATED_BULK_HUMAN_REVIEW).replace("\\", "/"),
        "ops_closure_ref": str(OPS_CLOSURE).replace("\\", "/"),
        "l0_kpi_ref": str(L0_KPI).replace("\\", "/"),
        "reproduce": "py scripts/build_encounter_sequence_weekly_report_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    churn = doc.get("multiturn_churn_kpi") if isinstance(doc.get("multiturn_churn_kpi"), dict) else {}
    headline = doc.get("headline_kpi") if isinstance(doc.get("headline_kpi"), dict) else {}
    delta_kpi = doc.get("match_rate_delta_kpi") if isinstance(doc.get("match_rate_delta_kpi"), dict) else {}
    l5 = doc.get("l5_myeongni_kpi") if isinstance(doc.get("l5_myeongni_kpi"), dict) else {}
    l6 = doc.get("l6_logos_kpi") if isinstance(doc.get("l6_logos_kpi"), dict) else {}
    l7 = doc.get("l7_cross_lens_kpi") if isinstance(doc.get("l7_cross_lens_kpi"), dict) else {}
    l0k = doc.get("l0_safety_kpi") if isinstance(doc.get("l0_safety_kpi"), dict) else {}
    print(
        json.dumps(
            {
                "ok": doc["weekly_ok"],
                "sequence_count": doc.get("sequence_count"),
                "multiturn_churn_ok": churn.get("multiturn_churn_ok"),
                "dual_lane_headline_ok": headline.get("dual_lane_headline_ok"),
                "match_rate_delta": delta_kpi.get("match_rate_delta_encounter_minus_clinic"),
                "l5_myeongni_headline_ok": l5.get("l5_myeongni_headline_ok"),
                "l6_logos_headline_ok": l6.get("l6_logos_headline_ok"),
                "l7_cross_lens_headline_ok": l7.get("cross_lens_headline_ok"),
                "l0_safety_headline_ok": l0k.get("l0_safety_headline_ok"),
            }
        )
    )
    return 0 if doc["weekly_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
