"""LTM graph topology — software layer · security · blast radius ([HYPO] routing map)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

SOFTWARE_LAYERS = frozenset(
    {
        "seed",
        "machine",
        "fuel",
        "packaging",
        "lens_regime",
        "meta_routing",
        "research",
    }
)
SECURITY_LEVELS = frozenset({"low", "medium", "high"})
BLAST_RADIUS = frozenset({"local", "lane", "repo", "production"})


@dataclass(frozen=True)
class TopologySpec:
    software_layer: str
    security_level: str
    blast_radius: str
    dependency_concepts: tuple[str, ...] = ()
    contract_note: str | None = None


def topology_to_dict(spec: TopologySpec) -> dict[str, Any]:
    d: dict[str, Any] = {
        "software_layer": spec.software_layer,
        "security_level": spec.security_level,
        "blast_radius": spec.blast_radius,
    }
    if spec.dependency_concepts:
        d["dependency_concepts"] = list(spec.dependency_concepts)
    if spec.contract_note:
        d["contract_note"] = spec.contract_note
    return d


TOPOLOGY_BY_ID: dict[str, TopologySpec] = {
    # --- seed (lib root) ---
    "sasang_taeyang_containment": TopologySpec(
        "lens_regime", "low", "lane", ("sasang_forbidden_synthesis",), "[HYPO] only"
    ),
    "sasang_forbidden_synthesis": TopologySpec(
        "lens_regime", "low", "lane", ("sasang_taeyang_containment",), "[HYPO] only"
    ),
    "lens_sasang_notebooklm_pack": TopologySpec(
        "lens_regime", "low", "lane", ("sasang_taeyang_containment",)
    ),
    "sasang_routing_sidecar_gematria_path": TopologySpec(
        "lens_regime",
        "low",
        "lane",
        ("sasang_forbidden_synthesis",),
        "[HYPO] sidecar only — no score fusion",
    ),
    "btrack_oper_score_freeze": TopologySpec(
        "packaging",
        "high",
        "repo",
        ("prophecy_research_only_boundary",),
        "oper SSOT read-only",
    ),
    "btrack_envelope_benchmark_closed": TopologySpec(
        "research", "medium", "lane", ("btrack_oper_score_freeze",)
    ),
    "send_gate_hold_doctrine": TopologySpec(
        "packaging",
        "high",
        "production",
        ("compression_send_prep_scaffold", "track_a_active_report_human_gate"),
    ),
    "fact_lock_implementation": TopologySpec(
        "packaging",
        "high",
        "repo",
        ("verify_p0_constitution_paths",),
    ),
    "central_resume_protocol": TopologySpec(
        "seed", "medium", "repo", ("ltm_graph_self_meta", "fact_lock_implementation")
    ),
    "prophecy_research_only_boundary": TopologySpec(
        "packaging", "high", "repo", ("btrack_oper_score_freeze",)
    ),
    # --- extended ---
    "compression_track_a_active_kpi": TopologySpec(
        "fuel", "high", "repo", ("track_a_active_report_human_gate", "raw_repair_dual_reporting")
    ),
    "compression_fail_comp004_boundary": TopologySpec(
        "packaging", "high", "repo", ("compression_track_a_active_kpi",)
    ),
    "ms_lane_submission_hold": TopologySpec(
        "packaging", "high", "lane", ("compression_fail_comp004_boundary",)
    ),
    "infra_solo_scheduler_stack": TopologySpec("machine", "medium", "repo"),
    "infra_parallel_passive_loop": TopologySpec(
        "machine", "medium", "lane", ("infra_solo_scheduler_stack",)
    ),
    "infra_en_tech_gpu_poc_venv": TopologySpec(
        "machine",
        "medium",
        "repo",
        ("infra_solo_scheduler_stack",),
        "venv-only GPU/ML · global py forbidden",
    ),
    "infra_ollama_qwen_local_default": TopologySpec(
        "machine",
        "low",
        "local",
        ("infra_en_tech_gpu_poc_venv",),
        "qwen2.5-coder default · 24h keep_alive",
    ),
    "infra_lambda_credits_hold_gate": TopologySpec(
        "packaging",
        "high",
        "production",
        ("send_gate_hold_doctrine", "web_ops_regime_gate_nebius"),
        "no Lambda burn until credits confirmed",
    ),
    "infra_integrity_guard_probe_regen": TopologySpec(
        "fuel",
        "high",
        "repo",
        ("verify_p0_constitution_paths", "fact_lock_implementation"),
        "myeongni_summary_gen → 16_STATE_MASTER_PROBE",
    ),
    "design_showroom_domain_portfolio": TopologySpec("packaging", "medium", "lane"),
    "domain_adapters_shallow_routing": TopologySpec(
        "meta_routing",
        "medium",
        "repo",
        ("design_showroom_domain_portfolio", "ltm_graph_self_meta"),
        "sync_bridge + ops_memory overlay",
    ),
    "pixel_battalion_adapter": TopologySpec(
        "packaging",
        "low",
        "lane",
        ("domain_adapters_shallow_routing", "design_showroom_domain_portfolio"),
        "[HYPO] mkmlife UI sprites",
    ),
    "lens_audio_adapter": TopologySpec(
        "research",
        "low",
        "lane",
        ("domain_adapters_shallow_routing",),
        "[HYPO] BGM PoC only",
    ),
    "lens_myeongni_notebooklm_pack": TopologySpec(
        "lens_regime", "low", "lane", ("regime_field_primary_map",)
    ),
    "lens_logos_non_gating_pack": TopologySpec(
        "lens_regime", "low", "lane", ("regime_field_primary_map",), "[NON_GATING]"
    ),
    "logos_theory_implementation_wiring": TopologySpec(
        "research",
        "low",
        "lane",
        ("lens_logos_non_gating_pack",),
        "re-invention guard",
    ),
    "logos_spread_sandbox_dynamic_tuning": TopologySpec(
        "research",
        "medium",
        "lane",
        ("logos_theory_implementation_wiring", "lens_logos_non_gating_pack"),
        "[HYPO] sandbox only",
    ),
    "logos_cosmic_anchor_graph_math": TopologySpec(
        "research",
        "medium",
        "lane",
        ("logos_theory_implementation_wiring", "lens_logos_non_gating_pack"),
        "339 anchors · gematria_bridge_v1",
    ),
    "logos_router_regression_bundle": TopologySpec(
        "research",
        "medium",
        "repo",
        ("logos_cosmic_anchor_graph_math", "a2a_ltm_track_wall"),
        "P21 structural gates · HOLD",
    ),
    "logos_4d_state_non_gating": TopologySpec(
        "lens_regime",
        "low",
        "lane",
        ("lens_logos_non_gating_pack", "logos_cosmic_anchor_graph_math"),
        "[NON_GATING] assist only",
    ),
    "logos_gematria_dual_gate": TopologySpec(
        "research",
        "medium",
        "lane",
        ("logos_cosmic_anchor_graph_math", "logos_spread_sandbox_dynamic_tuning"),
        "prod vs sandbox geometry",
    ),
    "regime_field_primary_map": TopologySpec(
        "lens_regime", "high", "repo", ("prophecy_research_only_boundary",)
    ),
    "local_vps_one_rule_workflow": TopologySpec(
        "packaging", "high", "production", ("athena_ecc_execution_governance",)
    ),
    "notebooklm_mcp_auth_bridge": TopologySpec("machine", "medium", "local"),
    "news_neutralizer_shadow_weekly": TopologySpec(
        "research", "medium", "lane", ("prophecy_research_only_boundary",)
    ),
    "web_ops_regime_gate_nebius": TopologySpec(
        "research", "high", "production", ("send_gate_hold_doctrine",), "GPU HOLD"
    ),
    "compression_moat_open_bench": TopologySpec(
        "research", "medium", "repo", ("compression_track_a_active_kpi",)
    ),
    "myeongni_pack0b_training_observation": TopologySpec(
        "research", "medium", "lane", ("lens_myeongni_notebooklm_pack",)
    ),
    "ltm_graph_self_meta": TopologySpec(
        "seed",
        "medium",
        "repo",
        ("central_resume_protocol",),
        "graph→overlay→resume",
    ),
    # --- dev_os packaging ---
    "git_hygiene_internal_first": TopologySpec(
        "packaging", "high", "repo", ("remote_publication_github_explicit",)
    ),
    "remote_publication_github_explicit": TopologySpec(
        "packaging", "high", "repo", ("git_hygiene_internal_first",)
    ),
    "athena_ecc_execution_governance": TopologySpec(
        "packaging", "high", "production", ("integrated_governance_ecc_input",)
    ),
    "raw_repair_dual_reporting": TopologySpec(
        "packaging", "high", "repo", ("compression_track_a_active_kpi",)
    ),
    "public_facing_ip_copy_v17": TopologySpec("packaging", "high", "repo"),
    "mkm_orchestrator_todo_queue": TopologySpec(
        "packaging", "medium", "repo", ("verify_p0_constitution_paths",)
    ),
    "verify_p0_constitution_paths": TopologySpec(
        "packaging", "high", "repo", ("fact_lock_implementation",)
    ),
    "track_a_active_report_human_gate": TopologySpec(
        "packaging", "high", "production", ("compression_fail_comp004_boundary",)
    ),
    "integrated_governance_ecc_input": TopologySpec(
        "packaging", "high", "production", ("athena_ecc_execution_governance",)
    ),
    "cursor_cloud_sandbox_boundary": TopologySpec(
        "packaging", "high", "repo", ("local_vps_one_rule_workflow",)
    ),
    "compression_send_prep_scaffold": TopologySpec(
        "packaging", "high", "production", ("send_gate_hold_doctrine",)
    ),
    # --- dev_os fuel ---
    "compression_openapi_v1_stub_contract": TopologySpec("fuel", "medium", "repo"),
    "compression_token_api_v1_stub": TopologySpec("fuel", "medium", "repo"),
    "compression_openapi_v2_draft": TopologySpec("fuel", "low", "repo"),
    "stt_routing_audit_log_schema": TopologySpec("fuel", "medium", "repo"),
    "track_a_metering_log_endpoint": TopologySpec("fuel", "high", "repo"),
    "run_fact_lock_bundle_entry": TopologySpec(
        "fuel", "high", "repo", ("verify_p0_constitution_paths",)
    ),
    "run_workspace_automation_health": TopologySpec(
        "fuel", "medium", "repo", ("run_fact_lock_bundle_entry",)
    ),
    "prism_grand_index_registry": TopologySpec("fuel", "low", "repo"),
    "p0_commercialization_tracker": TopologySpec("fuel", "medium", "repo"),
    "independent_lens_shadow_gate": TopologySpec(
        "fuel", "medium", "lane", ("lens_myeongni_notebooklm_pack",)
    ),
    # --- meta_routing (P2) ---
    "twelve_ai_routing_contract": TopologySpec(
        "meta_routing",
        "medium",
        "lane",
        ("ltm_graph_self_meta", "mkm_orchestrator_todo_queue"),
        "S/K/L/M cap 4 · not 12 models",
    ),
    "four_ai_lens_output_contract": TopologySpec(
        "meta_routing",
        "medium",
        "lane",
        ("regime_field_primary_map", "lens_logos_non_gating_pack"),
        "Field→Lens→Conflict→Final",
    ),
    "absolute_balance_coordinator_mode": TopologySpec(
        "meta_routing",
        "low",
        "lane",
        ("four_ai_lens_output_contract",),
        "state not 5th AI",
    ),
    "lane_resume_pack_contract": TopologySpec(
        "meta_routing",
        "medium",
        "lane",
        ("central_resume_protocol", "twelve_ai_routing_contract"),
        "build_mkm_chat_resume_pack_v1 --lane",
    ),
    "nl_research_sandbox_tier_b_gate": TopologySpec(
        "research",
        "medium",
        "lane",
        ("ltm_graph_self_meta", "prophecy_research_only_boundary"),
        "external_source_review · no Tier A ingest",
    ),
    "trading_go_nogo_status_ssot": TopologySpec(
        "packaging",
        "high",
        "production",
        (
            "trading_human_execution_approval_gate",
            "fact_safe_risk_sync_chain",
            "local_vps_one_rule_workflow",
            "athena_ecc_execution_governance",
        ),
        "single verdict JSON · no network",
    ),
    "trading_human_execution_approval_gate": TopologySpec(
        "packaging",
        "high",
        "production",
        ("trading_go_nogo_status_ssot", "athena_ecc_execution_governance"),
        "human receipt before live hooks",
    ),
    "vps_pm2_live_entry_boundary": TopologySpec(
        "packaging",
        "high",
        "production",
        ("local_vps_one_rule_workflow", "trading_go_nogo_status_ssot"),
        "code sync ≠ order ON",
    ),
    "fact_safe_risk_sync_chain": TopologySpec(
        "fuel",
        "high",
        "repo",
        ("trading_go_nogo_status_ssot", "local_vps_one_rule_workflow"),
        "observation chain · no auto live",
    ),
    "a2a_two_layer_architecture_ssot": TopologySpec(
        "meta_routing",
        "medium",
        "lane",
        ("ltm_ops_inject_to_a2a_wire", "inter_agent_encoding_smoke_chain"),
        "ops_memory vs inter_agent wire layers",
    ),
    "ltm_ops_inject_to_a2a_wire": TopologySpec(
        "meta_routing",
        "medium",
        "lane",
        ("a2a_two_layer_architecture_ssot", "lane_resume_pack_contract"),
        "ltm_* → tp01 pilot",
    ),
    "inter_agent_encoding_smoke_chain": TopologySpec(
        "fuel",
        "medium",
        "repo",
        ("a2a_two_layer_architecture_ssot", "a2a_ltm_track_wall"),
        "RQ-019 smoke + wire profile",
    ),
    "a2a_ltm_track_wall": TopologySpec(
        "packaging",
        "high",
        "repo",
        ("send_gate_hold_doctrine", "a2a_two_layer_architecture_ssot"),
        "forbidden_auto_merge explicit",
    ),
}


def verify_topology_coverage(concept_ids: tuple[str, ...] | list[str]) -> list[str]:
    errors: list[str] = []
    ids = set(concept_ids)
    mapped = set(TOPOLOGY_BY_ID.keys())
    missing = sorted(ids - mapped)
    extra = sorted(mapped - ids)
    if missing:
        errors.append(f"topology missing for concepts: {missing}")
    if extra:
        errors.append(f"topology entries without concepts: {extra}")
    for cid, topo in TOPOLOGY_BY_ID.items():
        if cid not in ids:
            continue
        if topo.software_layer not in SOFTWARE_LAYERS:
            errors.append(f"{cid}: invalid software_layer {topo.software_layer!r}")
        if topo.security_level not in SECURITY_LEVELS:
            errors.append(f"{cid}: invalid security_level {topo.security_level!r}")
        if topo.blast_radius not in BLAST_RADIUS:
            errors.append(f"{cid}: invalid blast_radius {topo.blast_radius!r}")
        for dep in topo.dependency_concepts:
            if dep not in ids:
                errors.append(f"{cid}: dependency {dep!r} not in concept set")
    return errors


def verify_topology_blast_radius(graph: dict[str, Any]) -> list[str]:
    """High blast_radius edits should not appear without high-security packaging nodes in route."""
    errors: list[str] = []
    concepts = graph.get("concepts") or {}
    for cid, concept in concepts.items():
        topo = concept.get("topology") or {}
        br = topo.get("blast_radius")
        sec = topo.get("security_level")
        if br == "production" and sec not in ("high",):
            errors.append(f"{cid}: production blast_radius requires security_level high")
    return errors
