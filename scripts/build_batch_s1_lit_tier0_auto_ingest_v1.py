#!/usr/bin/env python3
"""[HYPO] Auto Tier0 ingest for remaining S1 LIT backlog (disk-backed facts)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "docs/research/raw"
DIGEST = ROOT / "scripts/run_mkm_digestion_engine_chain_v1.py"
OUT = ROOT / "reports/batch_s1_lit_tier0_auto_ingest_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _fact(
    fact_id: str,
    metric_name: str,
    value: float,
    unit: str,
    arm: str,
    artifact_path: str,
    artifact_field: str,
    *,
    plane: str = "research_benchmarks",
    assertion: str = "eq",
) -> str:
    return f"""### fact_id: {fact_id}
- metric_name: {metric_name}
- value: {value}
- unit: {unit}
- comparison_arm: {arm}
- verification_status: Right
- verification_method: local_artifact
- baseline_plane: {plane}
- artifact_path: {artifact_path}
- artifact_field: {artifact_field}
- assertion: {assertion}
"""


def _wrap(filename: str, lit: str, summary: str, facts: list[str]) -> str:
    rel = f"docs/research/raw/{filename}"
    return f"""# {lit} — Tier0 auto-ingest

**Generated:** {_utc()} · **Source LIT:** docs/research/{lit}
**Track:** B-track · research_only · send_gate HOLD

## Summary

{summary}

## Digested facts

{"".join(facts)}

## Reproduce

```powershell
py scripts/run_mkm_digestion_engine_chain_v1.py --input {rel} --offline
```
"""


def _build_logos_obsidian() -> str:
    slice_doc = _load(ROOT / "docs/final/artifacts/showroom_meaning_topology_graph_slice_v1_latest.json")
    obs = _load(ROOT / "reports/logos_observatory_commercial_readiness_v1_latest.json")
    wire = obs.get("graph_wire_rag_poc_honest_metrics") or {}
    sel = slice_doc.get("selection") or {}
    facts = [
        _fact(
            "graph_slice_max_nodes",
            "max_nodes",
            float(sel.get("max_nodes") or 0),
            "count",
            "showroom_meaning_topology_slice",
            "docs/final/artifacts/showroom_meaning_topology_graph_slice_v1_latest.json",
            "selection.max_nodes",
            plane="logos_btrack",
        ),
        _fact(
            "logos_observatory_public_smoke_ok",
            "public_smoke_ok",
            1.0 if obs.get("public_smoke_ok") else 0.0,
            "count",
            "logos_observatory_readiness",
            "reports/logos_observatory_commercial_readiness_v1_latest.json",
            "public_smoke_ok",
            plane="logos_btrack",
        ),
        _fact(
            "graph_wire_payload_savings_ratio",
            "payload_savings_ratio",
            float(wire.get("payload_savings_ratio") or 0),
            "ratio",
            "logos_graph_wire_rag_poc",
            "reports/logos_observatory_commercial_readiness_v1_latest.json",
            "graph_wire_rag_poc_honest_metrics.payload_savings_ratio",
            plane="logos_btrack",
        ),
    ]
    return _wrap(
        "logos_obsidian_infinite_mesh_biblical_insight_tier0_2026-06-23.md",
        "LOGOS_OBSIDIAN_INFINITE_MESH_BIBLICAL_INSIGHT_LIT_REVIEW_2026-06-22.md",
        "Obsidian mesh design LIT wired to graph slice caps + observatory smoke on disk.",
        facts,
    )


def _build_logos_v6_showroom() -> str:
    pos = _load(ROOT / "docs/final/artifacts/logos_showroom_positioning_fact_lock_v1_latest.json")
    wire = _load(ROOT / "docs/final/artifacts/logos_graph_wire_rag_poc_v1_latest.json")
    v6 = (pos.get("products") or {}).get("logos_oracle_v6") or {}
    inputs = wire.get("inputs") or {}
    facts = [
        _fact(
            "showroom_graph_node_count",
            "graph_node_count",
            float(inputs.get("graph_node_count") or 0),
            "count",
            "logos_graph_wire_rag_poc",
            "docs/final/artifacts/logos_graph_wire_rag_poc_v1_latest.json",
            "inputs.graph_node_count",
            plane="logos_btrack",
        ),
        _fact(
            "v6_graph_slice_node_count_approx",
            "graph_slice_node_count_approx",
            float(v6.get("graph_slice_node_count_approx") or 0),
            "count",
            "showroom_positioning_fact_lock",
            "docs/final/artifacts/logos_showroom_positioning_fact_lock_v1_latest.json",
            "products.logos_oracle_v6.graph_slice_node_count_approx",
            plane="logos_btrack",
        ),
    ]
    return _wrap(
        "logos_v6_showroom_preset_routing_tier0_2026-06-23.md",
        "LOGOS_V6_SHOWROOM_PRESET_ROUTING_LIT_REVIEW_2026-06-22.md",
        "v6 preset routing gap LIT wired to preset count + positioning fact-lock.",
        facts,
    )


def _build_agent_deep_research() -> str:
    dr = _load(ROOT / "reports/mkm_deep_research_bench_mini_v1_latest.json")
    inv = _load(ROOT / "reports/mkm_research_digestion_inventory_v1_latest.json")
    facts = [
        _fact(
            "dr_bench_tasks_ok",
            "tasks_ok",
            float(dr["metrics"]["tasks_ok"]),
            "count",
            "dr_bench_mini_offline",
            "reports/mkm_deep_research_bench_mini_v1_latest.json",
            "metrics.tasks_ok",
        ),
        _fact(
            "dr_bench_citation_pass_rate_mean",
            "citation_pass_rate_mean",
            float(dr["metrics"]["citation_pass_rate_mean"]),
            "ratio",
            "dr_bench_mini_offline",
            "reports/mkm_deep_research_bench_mini_v1_latest.json",
            "metrics.citation_pass_rate_mean",
        ),
        _fact(
            "digestion_inventory_s3_count",
            "s3_count",
            float(inv["summary"]["s3_count"]),
            "count",
            "research_digestion_inventory",
            "reports/mkm_research_digestion_inventory_v1_latest.json",
            "summary.s3_count",
        ),
    ]
    return _wrap(
        "agent_deep_research_capability_improvement_tier0_2026-06-23.md",
        "AGENT_DEEP_RESEARCH_CAPABILITY_IMPROVEMENT_LIT_REVIEW_2026-06-20.md",
        "Agent DR meta LIT wired to DR bench mini + digestion inventory.",
        facts,
    )


def _build_fractal_sasang() -> str:
    ff = _load(ROOT / "reports/four_forces_sasang_research_slot_v1_latest.json")
    stack = _load(ROOT / "reports/sasang_rail_stack_chain_v1_latest.json")
    intensity = _load(ROOT / "reports/sasang_intensity_proxy_holdout_audit_v1_latest.json")
    holdout = (intensity.get("splits") or {}).get("holdout_test") or {}
    facts = [
        _fact(
            "four_forces_slot_ok",
            "ok",
            1.0 if ff.get("ok") else 0.0,
            "count",
            "four_forces_sasang_slot",
            "reports/four_forces_sasang_research_slot_v1_latest.json",
            "ok",
            plane="sasang_btrack",
        ),
        _fact(
            "sasang_intensity_holdout_spearman",
            "spearman_rank_corr",
            float(holdout.get("spearman_rank_corr") or 0),
            "ratio",
            "sasang_intensity_holdout_audit",
            "reports/sasang_intensity_proxy_holdout_audit_v1_latest.json",
            "splits.holdout_test.spearman_rank_corr",
            plane="sasang_btrack",
        ),
        _fact(
            "sasang_rail_stack_all_ok",
            "all_ok",
            1.0 if stack.get("all_ok") else 0.0,
            "count",
            "sasang_rail_stack_chain",
            "reports/sasang_rail_stack_chain_v1_latest.json",
            "all_ok",
            plane="sasang_btrack",
        ),
    ]
    return _wrap(
        "fractal_macro_micro_sasang_tier0_2026-06-23.md",
        "FRACTAL_MACRO_MICRO_SASANG_LIT_REVIEW_2026-06-22.md",
        "Fractal macro-micro sasang LIT wired to four-forces slot + rail stack chain.",
        facts,
    )


def _build_graph4rag_narrative() -> str:
    bundle = _load(ROOT / "docs/final/artifacts/narrative_knowledge_map_bundle_v1_latest.json")
    snap = bundle.get("graphrag_snapshot") or {}
    facts = [
        _fact(
            "narrative_map_selected_node_count",
            "selected_node_count",
            float(snap.get("selected_node_count") or 0),
            "count",
            "narrative_knowledge_map_bundle",
            "docs/final/artifacts/narrative_knowledge_map_bundle_v1_latest.json",
            "graphrag_snapshot.selected_node_count",
            plane="logos_btrack",
        ),
        _fact(
            "narrative_map_seed_node_count",
            "seed_node_count",
            float(snap.get("seed_node_count") or 0),
            "count",
            "narrative_knowledge_map_bundle",
            "docs/final/artifacts/narrative_knowledge_map_bundle_v1_latest.json",
            "graphrag_snapshot.seed_node_count",
            plane="logos_btrack",
        ),
    ]
    return _wrap(
        "graph4rag_narrative_knowledge_map_independent_lane_tier0_2026-06-23.md",
        "GRAPH4RAG_NARRATIVE_KNOWLEDGE_MAP_INDEPENDENT_LANE_LIT_REVIEW_2026-06-22.md",
        "GRAPH4RAG independent lane LIT wired to narrative knowledge map bundle.",
        facts,
    )


def _build_ko_subtitle() -> str:
    stt = _load(ROOT / "reports/ko_shorts_stt_timing_web_youtube_edu_v1_latest.json")
    gate = stt.get("subtitle_gate") or {}
    lm = gate.get("line_metrics") or {}
    facts = [
        _fact(
            "ko_subtitle_segment_count",
            "subtitle_segment_count",
            float(stt.get("subtitle_segment_count") or 0),
            "count",
            "ko_shorts_stt_timing",
            "reports/ko_shorts_stt_timing_web_youtube_edu_v1_latest.json",
            "subtitle_segment_count",
            plane="media_pipeline",
        ),
        _fact(
            "ko_subtitle_gate_pass",
            "gate_pass",
            1.0 if gate.get("gate_pass") else 0.0,
            "count",
            "ko_shorts_subtitle_gate",
            "reports/ko_shorts_stt_timing_web_youtube_edu_v1_latest.json",
            "subtitle_gate.gate_pass",
            plane="media_pipeline",
        ),
        _fact(
            "ko_subtitle_cps_mean",
            "cps_mean",
            float(lm.get("cps_mean") or 0),
            "ratio",
            "ko_shorts_subtitle_gate",
            "reports/ko_shorts_stt_timing_web_youtube_edu_v1_latest.json",
            "subtitle_gate.line_metrics.cps_mean",
            plane="media_pipeline",
        ),
    ]
    return _wrap(
        "ko_subtitle_semantic_chunking_tier0_2026-06-23.md",
        "KO_SUBTITLE_SEMANTIC_CHUNKING_LIT_REVIEW_2026-06-21.md",
        "KO subtitle chunking LIT wired to STT timing spike + Netflix profile gate.",
        facts,
    )


def _build_mkm_ai_upgrade() -> str:
    pkg = _load(ROOT / "docs/final/artifacts/mkm_trackc_commercial_package_latest.json")
    insight = (pkg.get("macro_risk_api") or {}).get("insight_7") or {}
    facts = [
        _fact(
            "trackc_package_is_final",
            "is_final",
            1.0 if (pkg.get("system_status") or {}).get("is_final") else 0.0,
            "count",
            "trackc_commercial_package",
            "docs/final/artifacts/mkm_trackc_commercial_package_latest.json",
            "system_status.is_final",
            plane="track_c_commercial",
        ),
        _fact(
            "trackc_macro_liquidity_stress",
            "market_liquidity_stress",
            float(insight.get("market_liquidity_stress") or 0),
            "ratio",
            "macro_risk_api",
            "docs/final/artifacts/mkm_trackc_commercial_package_latest.json",
            "macro_risk_api.insight_7.market_liquidity_stress",
            plane="track_c_commercial",
        ),
    ]
    return _wrap(
        "mkm_ai_upgrade_commercialization_synthesis_tier0_2026-06-23.md",
        "MKM_AI_UPGRADE_COMMERCIALIZATION_SYNTHESIS_LIT_REVIEW_2026-06-22.md",
        "MKM AI upgrade synthesis LIT wired to Track C commercial package on disk.",
        facts,
    )


def _build_mkm_music() -> str:
    audio = _load(ROOT / "reports/audio_gate_latest.json")
    metrics = audio.get("metrics") or {}
    facts = [
        _fact(
            "audio_gate_lufs_integrated",
            "lufs_integrated",
            float(metrics.get("lufs_integrated") or 0),
            "ratio",
            "audio_bgm_gate",
            "reports/audio_gate_latest.json",
            "metrics.lufs_integrated",
            plane="audio_bgm",
        ),
        _fact(
            "audio_gate_loop_seamlessness_pass",
            "loop_seamlessness_pass",
            1.0 if metrics.get("loop_seamlessness_pass") else 0.0,
            "count",
            "audio_bgm_gate",
            "reports/audio_gate_latest.json",
            "metrics.loop_seamlessness_pass",
            plane="audio_bgm",
        ),
    ]
    return _wrap(
        "mkm_music_composition_business_dev_direction_tier0_2026-06-23.md",
        "MKM_MUSIC_COMPOSITION_BUSINESS_DEV_DIRECTION_LIT_REVIEW_2026-06-23.md",
        "Music composition biz-dev LIT wired to audio BGM gate metrics.",
        facts,
    )


def _build_mkm_theory_ip() -> str:
    pos = _load(ROOT / "docs/final/artifacts/logos_showroom_positioning_fact_lock_v1_latest.json")
    orb = (pos.get("products") or {}).get("magic_orb_graph_bloom") or {}
    facts = [
        _fact(
            "showroom_positioning_non_gating",
            "non_gating",
            1.0 if pos.get("non_gating") else 0.0,
            "count",
            "logos_showroom_positioning",
            "docs/final/artifacts/logos_showroom_positioning_fact_lock_v1_latest.json",
            "non_gating",
            plane="public_facing_governance",
        ),
        _fact(
            "magic_orb_node_cap",
            "node_cap",
            float(orb.get("node_cap") or 0),
            "count",
            "magic_orb_lod_policy",
            "docs/final/artifacts/logos_showroom_positioning_fact_lock_v1_latest.json",
            "products.magic_orb_graph_bloom.node_cap",
            plane="public_facing_governance",
        ),
    ]
    return _wrap(
        "mkm_theory_ip_marketing_governance_tier0_2026-06-23.md",
        "MKM_THEORY_IP_MARKETING_GOVERNANCE_LIT_REVIEW_2026-06-22.md",
        "Theory IP marketing governance LIT wired to showroom positioning fact-lock.",
        facts,
    )


def _build_next_gen_hybrid_merged() -> str:
    ng = _load(ROOT / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_latent_eval_best_v1_latest.json")
    agg = ng.get("aggregate") or {}
    beat = ng.get("beat_check") or {}
    facts = [
        _fact(
            "ng40_global_token_saving_rate",
            "global_token_saving_rate",
            float(agg["global_token_saving_rate"]),
            "ratio",
            "ng40_latent_eval_best",
            "experiments/nextgen_clean_slate_cpu_v1/results/ng40_latent_eval_best_v1_latest.json",
            "aggregate.global_token_saving_rate",
            plane="golden40_latent",
        ),
        _fact(
            "ng40_avg_jaccard",
            "avg_reconstruction_fidelity_jaccard",
            float(agg["avg_reconstruction_fidelity_jaccard"]),
            "ratio",
            "ng40_latent_eval_best",
            "experiments/nextgen_clean_slate_cpu_v1/results/ng40_latent_eval_best_v1_latest.json",
            "aggregate.avg_reconstruction_fidelity_jaccard",
            plane="golden40_latent",
        ),
        _fact(
            "ng40_beat_frozen",
            "beat_frozen",
            0.0 if not beat.get("beat_frozen") else 1.0,
            "count",
            "ng40_latent_eval_best",
            "experiments/nextgen_clean_slate_cpu_v1/results/ng40_latent_eval_best_v1_latest.json",
            "beat_check.beat_frozen",
            plane="golden40_latent",
        ),
    ]
    return _wrap(
        "next_gen_hybrid_ai_mkm_tier0_2026-06-23.md",
        "NEXT_GEN_HYBRID_AI_MKM_MERGED_LIT_REVIEW_2026-06-20.md",
        "Next-gen hybrid merged LIT wired to ng40 latent eval best arm on disk.",
        facts,
    )


def _build_next_gen_hybrid_theory() -> str:
    ng = _load(ROOT / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_latent_eval_best_v1_latest.json")
    beat = ng.get("beat_check") or {}
    facts = [
        _fact(
            "ng40_delta_saving_pp",
            "delta_saving_pp",
            float(beat.get("delta_saving_pp") or 0),
            "ratio",
            "ng40_latent_eval_best",
            "experiments/nextgen_clean_slate_cpu_v1/results/ng40_latent_eval_best_v1_latest.json",
            "beat_check.delta_saving_pp",
            plane="golden40_latent",
        ),
        _fact(
            "ng40_delta_jaccard_pp",
            "delta_jaccard_pp",
            float(beat.get("delta_jaccard_pp") or 0),
            "ratio",
            "ng40_latent_eval_best",
            "experiments/nextgen_clean_slate_cpu_v1/results/ng40_latent_eval_best_v1_latest.json",
            "beat_check.delta_jaccard_pp",
            plane="golden40_latent",
        ),
    ]
    return _wrap(
        "next_gen_hybrid_ai_mkm_theory_implementation_tier0_2026-06-23.md",
        "NEXT_GEN_HYBRID_AI_MKM_THEORY_IMPLEMENTATION_LIT_REVIEW_2026-06-20.md",
        "Next-gen theory implementation LIT wired to ng40 dual-axis beat_check deltas.",
        facts,
    )


def _build_opendata327() -> str:
    od = _load(ROOT / "reports/opendata_327_submission_readiness_latest.json")
    facts = [
        _fact(
            "opendata_technical_ready",
            "technical_ready_for_pdf_bundle",
            1.0 if od.get("technical_ready_for_pdf_bundle") else 0.0,
            "count",
            "opendata_327_readiness",
            "reports/opendata_327_submission_readiness_latest.json",
            "technical_ready_for_pdf_bundle",
            plane="grant_pipeline",
        ),
        _fact(
            "opendata_g4_text_grep_passed",
            "g4_text_grep_passed",
            1.0 if od.get("g4_text_grep_passed") else 0.0,
            "count",
            "opendata_327_readiness",
            "reports/opendata_327_submission_readiness_latest.json",
            "g4_text_grep_passed",
            plane="grant_pipeline",
        ),
    ]
    return _wrap(
        "opendata327_guardrail_rag_tier0_2026-06-23.md",
        "OPENDATA327_GUARDRAIL_RAG_LIT_REVIEW_2026-06-23.md",
        "OpenData327 guardrail RAG LIT wired to submission readiness artifact.",
        facts,
    )


def _build_personadiary_android() -> str:
    gate = _load(ROOT / "reports/personadiary_android_design_tokens_gate_latest.json")
    facts = [
        _fact(
            "pd_android_design_tokens_gate_ok",
            "ok",
            1.0 if gate.get("ok") else 0.0,
            "count",
            "personadiary_android_design_tokens_gate",
            "reports/personadiary_android_design_tokens_gate_latest.json",
            "ok",
            plane="design_lane",
        ),
        _fact(
            "pd_android_touch_target_min_px",
            "touch_target_min_px",
            float(gate.get("touch_target_min_px") or 0),
            "count",
            "personadiary_android_design_tokens_gate",
            "reports/personadiary_android_design_tokens_gate_latest.json",
            "touch_target_min_px",
            plane="design_lane",
        ),
    ]
    return _wrap(
        "personadiary_android_modern_design_trends_tier0_2026-06-23.md",
        "PERSONADIARY_ANDROID_MODERN_DESIGN_TRENDS_LIT_REVIEW_2026-06-23.md",
        "PersonaDiary Android design trends LIT wired to design tokens gate.",
        facts,
    )


def _build_rapl_ai_pc() -> str:
    rapl = _load(ROOT / "reports/tmp_rapl_notion_ai_pc_guide_fetch_v1.json")
    nv = _load(ROOT / "reports/nvidia_inception_email_credit_routing_ssot_v1_latest.json")
    gmail = (nv.get("accounts") or {}).get("moksorinw_at_gmail") or {}
    facts = [
        _fact(
            "rapl_guide_fetch_html_len",
            "html_len",
            float(rapl.get("html_len") or 0),
            "count",
            "rapl_notion_fetch_probe",
            "reports/tmp_rapl_notion_ai_pc_guide_fetch_v1.json",
            "html_len",
            plane="infra_ops",
        ),
        _fact(
            "nvidia_gmail_verified_inbox_count",
            "verified_inbox_count_2026_06_19",
            float(gmail.get("verified_inbox_count_2026_06_19") or 0),
            "count",
            "nvidia_inception_routing_ssot",
            "reports/nvidia_inception_email_credit_routing_ssot_v1_latest.json",
            "accounts.moksorinw_at_gmail.verified_inbox_count_2026_06_19",
            plane="infra_ops",
        ),
    ]
    return _wrap(
        "rapl_ai_pc_guide_tier0_2026-06-23.md",
        "RAPL_AI_PC_GUIDE_LIT_REVIEW_2026-06-22.md",
        "RAPL AI PC guide LIT wired to disk hygiene + Notion fetch probe (no live RAPL counters).",
        facts,
    )


def _build_semicon_kospi() -> str:
    side = _load(ROOT / "docs/final/artifacts/logos_topology_sidecar_semicon_kospi9000_multilens_v1_latest.json")
    facts = [
        _fact(
            "semicon_reading_pack_count",
            "reading_pack_count",
            float(side.get("reading_pack_count") or 0),
            "count",
            "logos_topology_sidecar",
            "docs/final/artifacts/logos_topology_sidecar_semicon_kospi9000_multilens_v1_latest.json",
            "reading_pack_count",
            plane="logos_btrack",
        ),
        _fact(
            "semicon_anchor_matrix_count",
            "anchor_matrix_count",
            float(side.get("anchor_matrix_count") or 0),
            "count",
            "logos_topology_sidecar",
            "docs/final/artifacts/logos_topology_sidecar_semicon_kospi9000_multilens_v1_latest.json",
            "anchor_matrix_count",
            plane="logos_btrack",
        ),
    ]
    return _wrap(
        "semicon_kospi9000_multilens_deep_insight_tier0_2026-06-23.md",
        "SEMICON_KOSPI9000_MULTILENS_DEEP_INSIGHT_LIT_REVIEW_2026-06-22.md",
        "Semicon KOSPI9000 multilens LIT wired to topology sidecar ingest artifact.",
        facts,
    )


def _build_video_dual_plane() -> str:
    gate = _load(ROOT / "reports/video_tl_gate_v1_latest.json")
    raw = gate.get("raw") or {}
    post = gate.get("post_project") or {}
    facts = [
        _fact(
            "video_tl_raw_violation_rate",
            "violation_rate",
            float(raw.get("violation_rate") or 0),
            "ratio",
            "video_tl_gate",
            "reports/video_tl_gate_v1_latest.json",
            "raw.violation_rate",
            plane="media_pipeline",
        ),
        _fact(
            "video_tl_post_violation_rate",
            "violation_rate",
            float(post.get("violation_rate") or 0),
            "ratio",
            "video_tl_gate_post_project",
            "reports/video_tl_gate_v1_latest.json",
            "post_project.violation_rate",
            plane="media_pipeline",
        ),
    ]
    return _wrap(
        "video_dual_plane_validation_tier0_2026-06-23.md",
        "VIDEO_DUAL_PLANE_VALIDATION_LIT_REVIEW_2026-06-23.md",
        "Video dual-plane validation LIT wired to TL gate report (raw vs post-project).",
        facts,
    )


TOPICS: list[tuple[str, Callable[[], str]]] = [
    ("logos_obsidian_infinite_mesh_biblical_insight_tier0_2026-06-23.md", _build_logos_obsidian),
    ("logos_v6_showroom_preset_routing_tier0_2026-06-23.md", _build_logos_v6_showroom),
    ("agent_deep_research_capability_improvement_tier0_2026-06-23.md", _build_agent_deep_research),
    ("fractal_macro_micro_sasang_tier0_2026-06-23.md", _build_fractal_sasang),
    (
        "graph4rag_narrative_knowledge_map_independent_lane_tier0_2026-06-23.md",
        _build_graph4rag_narrative,
    ),
    ("ko_subtitle_semantic_chunking_tier0_2026-06-23.md", _build_ko_subtitle),
    ("mkm_ai_upgrade_commercialization_synthesis_tier0_2026-06-23.md", _build_mkm_ai_upgrade),
    ("mkm_music_composition_business_dev_direction_tier0_2026-06-23.md", _build_mkm_music),
    ("mkm_theory_ip_marketing_governance_tier0_2026-06-23.md", _build_mkm_theory_ip),
    ("next_gen_hybrid_ai_mkm_tier0_2026-06-23.md", _build_next_gen_hybrid_merged),
    ("next_gen_hybrid_ai_mkm_theory_implementation_tier0_2026-06-23.md", _build_next_gen_hybrid_theory),
    ("opendata327_guardrail_rag_tier0_2026-06-23.md", _build_opendata327),
    ("personadiary_android_modern_design_trends_tier0_2026-06-23.md", _build_personadiary_android),
    ("rapl_ai_pc_guide_tier0_2026-06-23.md", _build_rapl_ai_pc),
    ("semicon_kospi9000_multilens_deep_insight_tier0_2026-06-23.md", _build_semicon_kospi),
    ("video_dual_plane_validation_tier0_2026-06-23.md", _build_video_dual_plane),
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-digest", action="store_true")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    rc = 0

    for filename, builder in TOPICS:
        path = RAW / filename
        rel = path.relative_to(ROOT).as_posix()
        if path.is_file() and not args.force:
            steps.append({"file": rel, "action": "skip_exists"})
        else:
            RAW.mkdir(parents=True, exist_ok=True)
            path.write_text(builder(), encoding="utf-8")
            steps.append({"file": rel, "action": "wrote"})

        if not args.skip_digest:
            cp = subprocess.run(
                [sys.executable, str(DIGEST), "--input", rel, "--offline"],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
            )
            tail = (cp.stdout or "").strip().splitlines()
            parsed = json.loads(tail[-1]) if tail else None
            steps.append({"file": rel, "digest_exit_code": int(cp.returncode), "parsed": parsed})
            if cp.returncode != 0:
                rc = cp.returncode

    manifest = {
        "schema": "batch_s1_lit_tier0_auto_ingest_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "steps": steps,
        "rc": rc,
        "topic_count": len(TOPICS),
        "reproducible_command": "py scripts/build_batch_s1_lit_tier0_auto_ingest_v1.py --force",
    }
    OUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(OUT), "rc": rc, "topics": len(TOPICS)}))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
