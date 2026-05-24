#!/usr/bin/env python3
"""Cross-chat achievement index — single JSON for other sessions (no chat merge)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
OUT = PILOT / "comp_cross_chat_achievement_index_v1.json"
HANDOFF = PILOT / "comp_compression_lane_handoff_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _exists(rel: str) -> bool:
    return (ROOT / rel).is_file()


def main() -> int:
    achievements = {
        "track_a_frozen": {
            "global_token_saving_rate": 0.47538677918424754,
            "avg_reconstruction_fidelity_jaccard": 0.8904921794966301,
            "apply_gematria_4d_bridge_policy": False,
            "signoff": "multilens_ultra_compression_track_a_promotion_signoff_v1_latest.json",
            "active": "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json",
        },
        "comp_atom": [
            "comp_atom01_ab_summary_v1.json",
            "comp_atom02_pointer_feasibility_summary_v1.json",
            "comp_atom02_pointer_research_brief_v1.json",
            "comp_atom05_profile_matrix_sweep_v1.json",
            "comp_atom05_profile_matrix_brief_v1.json",
            "comp_atom05_full_v2_sweep_v1.json",
            "comp_atom05_bridge_boost_detail_v1.json",
            "comp_atom05_bridge_boost_per_case_delta_v1.json",
            "comp_atom05_compare_prior_v1.json",
            "comp_atom_track_b_closure_v1.json",
            "comp_atom05_parallel_fuse_v2.json",
            "comp_anchor07_wire_source_ab_v1.json",
            "comp_v2_wire_staging_promotion_scope_v1.json",
            "comp_v2_wire_shadow_metering_summary_v1.json",
        ],
        "comp_anchor": [
            "comp_anchor05_verse_pool_full_scan_v1.json",
            "comp_anchor06_top_verse_pools_v1.json",
            "comp_anchor06_registry_codebook_bridge_v1.json",
            "comp_anchor07_registry_seed_mapping_poc_v1.json",
            "comp_anchor08_seed_curation_queue_v1.json",
            "comp_anchor08_seed_curation_applied_v1.json",
            "comp_anchor07_wire_atom_candidates_v1.json",
            "comp_nl_manual_upload_manifest_v1.json",
            "comp_universal_bench_matrix_build_v1.json",
            "comp_universal_bench_matrix_sweep_v1.json",
            "comp_universal_bench_matrix_summary_v1.json",
            "comp_universal_bench_matrix_wire_ab_finance_v1.json",
            "comp_universal_bench_matrix_wire_ab_enterprise_v1.json",
            "comp_universal_bench_matrix_wire_ab_ijeoma_v1.json",
            "comp_universal_bench_matrix_wire_ab_summary_v1.json",
            "comp_universal_bench_matrix_wire_ab_summary_290_subset_v1.json",
            "comp_hanja_codebook_coverage_hypo_scan_v1.json",
            "comp_hanja_phrase_lexicon_hypo_slice_v1.json",
            "comp_hanja_chunk_compression_hypo_eval_v1.json",
            "comp_hanja_chunk_lane_status_hypo_v1.json",
            "comp_ijeoma_hanja_codebook_export_hypo_v1.json",
            "comp_universal_bench_matrix_wire_ab_ijeoma_chunk_v1.json",
            "comp_universal_bench_matrix_sweep_290_subset_v1.json",
            "comp_universal_bench_chunk_eval_debug_v1.json",
            "comp_v2_universal_wire_lane_refresh_v1.json",
            "comp_corpus01_readiness_v1.json",
        ],
        "ijeoma_b7": "comp_ijeoma_b7_manifest_closure_v1.json",
        "integration_team_ssot": {
            "brief_json": "reports/constitution/btrack_pilot/comp_atom05_profile_matrix_brief_v1.json",
            "openapi_draft": "docs/final/openapi_token_compression_v2_draft.yaml",
            "regenerate": "py scripts/comp_atom05_profile_matrix_brief_v1.py",
        },
        "notebooklm_manual": {
            "compression_pack": "reports/notebooklm_lens_packs_v1/COMPRESSION_BTRACK/",
            "ijeoma_pack": "reports/notebooklm_lens_packs_v1/IJEOMA_BTRACK/",
            "auto_script": "scripts/push_btrack_nl_nlm_text_v1.py",
            "upload_result": "reports/constitution/btrack_pilot/comp_nl_auto_upload_result_v1.json",
            "commander_auto_upload_approved": True,
            "ijeoma_fallback_notebook": "71f55a03-09d0-411f-b365-0ce2a2064c24",
        },
        "regression": {
            "script": "scripts/comp_parallel_round_v1.ps1",
            "comp_parallel_pytest": 37,
            "final_parallel_pytest": 15,
            "last_pytest_passed": 52,
            "wire_shadow_pytest_optional": 2,
        },
        "comp_v2_wire_closure": {
            "status": "DONE",
            "scope_json": "reports/constitution/btrack_pilot/comp_v2_wire_staging_promotion_scope_v1.json",
            "shadow_summary": "reports/constitution/btrack_pilot/comp_v2_wire_shadow_metering_summary_v1.json",
            "shadow_pairs": 9,
            "bridge_boost_flag_ok": 9,
            "scheduled_task": "MKM-V2-Wire-Shadow-Metering-Weekly",
            "first_auto_run_local": "2026-05-24T10:15:00",
            "hold": [
                "wire default true",
                "active KPI overwrite",
                "live meter",
            ],
        },
        "universal_bench_matrix": {
            "registry": "docs/final/artifacts/universal_compression_bench_matrix_registry_v1.json",
            "matrix_input": "docs/final/artifacts/UNIVERSAL_COMPRESSION_BENCH_MATRIX_INPUT_V1.json",
            "build_script": "scripts/build_universal_compression_bench_matrix_v1.py",
            "sweep_script": "scripts/run_universal_compression_bench_matrix_sweep_v1.py",
            "sweep_exclude_lane_ids": ["ijeoma_chunk_table_v1"],
            "sweep_290_operational_out": "reports/constitution/btrack_pilot/comp_universal_bench_matrix_sweep_290_operational_v1.json",
            "wire_ab_lane_script": "scripts/run_universal_compression_bench_wire_ab_lane_v1.py",
            "wire_ab_artifacts": [
                "reports/constitution/btrack_pilot/comp_universal_bench_matrix_wire_ab_finance_v1.json",
                "reports/constitution/btrack_pilot/comp_universal_bench_matrix_wire_ab_enterprise_v1.json",
                "reports/constitution/btrack_pilot/comp_universal_bench_matrix_wire_ab_ijeoma_v1.json",
            ],
            "golden_frozen": "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json",
            "sweep_290_subset": "reports/constitution/btrack_pilot/comp_universal_bench_matrix_sweep_290_subset_v1.json",
            "matrix_case_count": 470,
            "operational_kpi_case_count": 290,
            "excluded_chunk_lanes": ["ijeoma_chunk_table_v1", "ijeoma_chunk_cjk_hypo_v1"],
            "subset_script": "scripts/summarize_universal_bench_matrix_sweep_subset_v1.py",
            "chunk_lane_eval_note": "full_chunk_join OK; economy 0% when master_codebook hit_count=0 (hanja/CJK); exclude lane from B-track mean KPI",
            "chunk_eval_debug": "reports/constitution/btrack_pilot/comp_universal_bench_chunk_eval_debug_v1.json",
            "wire_ab_290_subset": "reports/constitution/btrack_pilot/comp_universal_bench_matrix_wire_ab_summary_290_subset_v1.json",
            "hanja_codebook_hypo_scan": "scripts/scan_hanja_codebook_coverage_hypo_v1.py",
            "hanja_chunk_lane_status": "reports/constitution/btrack_pilot/comp_hanja_chunk_lane_status_hypo_v1.json",
            "hanja_chunk_verdict": "lexicon_hits_ok_saving_still_flat — hypo lexicon 12k phrases",
            "ijeoma_hanja_hypo_lexicon": "reports/constitution/btrack_pilot/ijeoma_hanja_codebook_lexicon_v1_hypo_latest.json",
            "export_script": "scripts/export_ijeoma_hanja_codebook_lexicon_hypo_v1.py",
            "hypo_chain_ps1": "scripts/run_ijeoma_hanja_hypo_chain_v1.ps1",
            "cjk_substitution_eval": "reports/constitution/btrack_pilot/comp_ijeoma_cjk_substitution_hypo_eval_v1.json",
            "cjk_substitution_lane": "docs/final/artifacts/universal_compression_bench_lane_ijeoma_chunk_cjk_hypo_v1.json",
            "cjk_lane_registry_id": "ijeoma_chunk_cjk_hypo_v1",
            "cjk_sweep_90_baseline": "reports/constitution/btrack_pilot/comp_universal_bench_matrix_sweep_ijeoma_chunk_cjk_hypo_v1.json",
            "cjk_char_jaccard": "reports/constitution/btrack_pilot/comp_ijeoma_cjk_fidelity_char_jaccard_v1.json",
            "evaluate_report_cjk_hook": "report_multilens_performance_eval.evaluate_report(ijeoma_cjk_substitution_hypo_v1=True)",
            "cjk_bridge_vs_eval_hook_parity": "reports/constitution/btrack_pilot/comp_ijeoma_cjk_bridge_vs_eval_hook_v1.json",
            "cjk_o200k_bench": "reports/constitution/btrack_pilot/comp_ijeoma_cjk_o200k_bench_v1.json",
            "hanja_lexicon_cap_sweep": "reports/constitution/btrack_pilot/comp_ijeoma_hanja_lexicon_cap_sweep_v1.json",
            "cjk_hypo_20k_sweep": "reports/constitution/btrack_pilot/comp_universal_bench_matrix_sweep_ijeoma_chunk_cjk_hypo_20k_v1.json",
            "ms_hwpx_cjk_crosslink": "reports/hwpx_poc/ms_cjk_btrack_crosslink_v1.txt",
            "sweep_290_operational": "reports/constitution/btrack_pilot/comp_universal_bench_matrix_sweep_290_operational_v1.json",
            "ijeoma_cjk_compression_hypo": "scripts/ijeoma_cjk_compression_hypo_v1.py",
            "ijeoma_cjk_bench_bridge": "scripts/ijeoma_cjk_substitution_bench_bridge_v1.py",
            "ijeoma_cjk_hypo_bundle": "reports/constitution/btrack_pilot/comp_ijeoma_cjk_hypo_bundle_summary_v1.json",
            "research_only": True,
        },
    }
    boost_path = PILOT / "comp_atom05_bridge_boost_per_case_delta_v1.json"
    mean_delta_pp = None
    if boost_path.is_file():
        mean_delta_pp = json.loads(boost_path.read_text(encoding="utf-8")).get("mean_delta_pp")

    seed_applied_path = PILOT / "comp_anchor08_seed_curation_applied_v1.json"
    seed_approved = None
    if seed_applied_path.is_file():
        seed_applied = json.loads(seed_applied_path.read_text(encoding="utf-8"))
        seed_approved = seed_applied.get("approved_count")

    brief_path = PILOT / "comp_atom05_profile_matrix_brief_v1.json"
    brief_presets = None
    if brief_path.is_file():
        brief_presets = json.loads(brief_path.read_text(encoding="utf-8")).get("profile_presets")
    for group in ("comp_atom", "comp_anchor"):
        achievements[group] = [p for p in achievements[group] if _exists(f"reports/constitution/btrack_pilot/{p}")]

    doc = {
        "schema": "comp_cross_chat_achievement_index_v1",
        "generated_at_utc": _utc(),
        "mission_log_ssot": "MISSION_LOG.md",
        "research_only": True,
        "fusion_policy": {
            "merge_chats": False,
            "merge_method": "read MISSION_LOG + this JSON + btrack_pilot artifacts",
            "forbidden": [
                "overwrite active report without human",
                "MS/HWPX in compression agent loop",
                "NotebookLM MCP add_source batch",
            ],
        },
        "ms_paste_hwpx": {
            "status": "commander_done",
            "target": "reports/hwpx_poc/ms_microsoft_ma_jung_filled_v1.hwpx",
            "kpi_lock": "47.5% saving / Jaccard 0.890 only (Golden 40)",
        },
        "current_situation_one_liner": (
            "COMP/v2-shadow lane DONE: Track A 47.5% frozen; parallel pytest 52/52 exit 0; "
            "shadow 9/9 bridge_boost flag [HYPO]; task Ready first run 2026-05-24 10:15; "
            f"outer manual: O-P5/personadiary/ijeoma80+; seed {seed_approved or 0}/11."
            if seed_approved is not None
            else (
                "COMP/v2-shadow lane DONE: Track A 47.5% frozen; pytest 52; shadow 9/9 flag; "
                "weekly task Ready 2026-05-24 10:15."
            )
        ),
        "work_objectives_next": [
            "OUTER-O-P5: DONE (verify op5_pass) — demo https://jema12.com/studio; optional www rule only — op5_cf_manual_runbook_v1.json",
            "OUTER-personadiary: MKM_CLOUDFLARE_PERSONADIARY_DNS_TOKEN then Invoke-PersonadiaryCloudflareRoutingReadiness_v1.ps1 -Apply",
            "COMP-OPTIONAL: ijeoma 80+ cases / Vault mirror / NL ai-b-mkm-abstract UI",
            "COMP-WEEKLY: first MKM-V2-Wire-Shadow-Metering-Weekly 2026-05-24 10:15 — verify Last Result=0",
        ],
        "profile_presets": brief_presets,
        "achievements": achievements,
        "key_verdicts": {
            "pointer_strict_40": 0,
            "pointer_partial_40": 10,
            "bridge_boost_cases": 9,
            "verse_scan": 31102,
            "b7_closure_ok": _exists("reports/constitution/btrack_pilot/comp_ijeoma_b7_manifest_closure_v1.json"),
            "boost_mean_jaccard_delta_pp": mean_delta_pp,
            "seed_approved_count": seed_approved,
        },
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Also refresh handoff pointer list
    if HANDOFF.is_file():
        handoff = json.loads(HANDOFF.read_text(encoding="utf-8"))
    else:
        handoff = {"schema": "comp_compression_lane_handoff_v1"}
    handoff["generated_at_utc"] = _utc()
    handoff["cross_chat_index"] = str(OUT.relative_to(ROOT)).replace("\\", "/")
    handoff["achievement_index"] = achievements
    handoff["work_objectives"] = doc["work_objectives_next"]
    handoff["current_situation"] = doc["current_situation_one_liner"]
    if brief_presets:
        handoff["profile_presets"] = brief_presets
        handoff["integration_team_ssot"] = achievements.get("integration_team_ssot")
    HANDOFF.write_text(json.dumps(handoff, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"wrote": OUT.name, "handoff": HANDOFF.name}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
