#!/usr/bin/env python3
"""Assemble Logos GraphRAG bridge L4/L5 evidence pack (internal · research_only · NON_GATING)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/final/artifacts"
REPORTS = ROOT / "reports"
DEFAULT_OUT_JSON = ART / "logos_graphrag_bridge_evidence_pack_v1_latest.json"
DEFAULT_OUT_MD = ART / "logos_graphrag_bridge_evidence_pack_v1_latest.md"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path.resolve().as_posix())


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _snapshot(path: Path) -> dict[str, Any]:
    return {"path": _rel(path), "exists": path.is_file()}


def _count_jsonl_rows(path: Path) -> int:
    if not path.is_file():
        return 0
    n = 0
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                n += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description="Build Logos GraphRAG bridge evidence pack v1")
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT_JSON)
    ap.add_argument("--output-md", type=Path, default=DEFAULT_OUT_MD)
    args = ap.parse_args()

    bridge_ssot = ROOT / "docs/final/LOGOS_ORIGINAL_LANGUAGE_GRAPH_RAG_BRIDGE_V1.md"
    graph_bundle = ART / "logos_corpus_graph_bundle_v1_latest.json"
    concept_registry = ART / "logos_concept_bridge_registry_v1_latest.json"
    router_out = ART / "logos_subgraph_graphrag_router_v1_latest.json"
    lemma_jsonl = ART / "logos_lemma_verse_edges_v1.jsonl"
    lemma_manifest = ART / "logos_lemma_verse_edges_v1_latest.json"
    replay_summary = REPORTS / "subgraph_router_replay_summary_latest.json"
    l3 = ART / "logos_track_l_l3_readiness_v1_latest.json"
    s1_packet = ART / "logos_s1_shadow_promotion_review_packet_latest.json"
    gold_eval = REPORTS / "logos_gold_query_eval_v1_latest.json"
    subgraph_gold_eval = REPORTS / "logos_subgraph_gold_eval_v1_latest.json"
    subgraph_gold_chain = REPORTS / "logos_subgraph_gold_eval_chain_v1_latest.json"
    phase9_chain = REPORTS / "logos_graphrag_phase9_eval_chain_v1_latest.json"
    phase10_chain = REPORTS / "logos_graphrag_phase10_miss_tune_chain_v1_latest.json"
    phase10c_chain = REPORTS / "logos_graphrag_phase10c_chain_v1_latest.json"
    sidecar_ablation = REPORTS / "logos_subgraph_sidecar_ablation_v1_latest.json"
    sidecar_ablation_v2 = REPORTS / "logos_subgraph_sidecar_ablation_v2_latest.json"
    sidecar_ablation_v3 = REPORTS / "universal_root_sidecar_ablation_v3_latest.json"
    shallow_stress_gap = REPORTS / "ollama_shallow_oracle_gap_stress_v1_latest.json"
    shallow_stress_bench = REPORTS / "ollama_shallow_router_bench_stress_v1_latest.json"
    gate_spec = ART / "UNIVERSAL_ROOT_GATE_SPEC_V1.json"
    gate_eval = REPORTS / "universal_root_gate_eval_v1_latest.json"
    nsm_audit = REPORTS / "nsm_41k_lexicon_crosswalk_audit_v1_latest.json"
    nsm_audit_raw = REPORTS / "nsm_41k_lexicon_crosswalk_audit_raw_v1_latest.json"
    deepnsm_chain = REPORTS / "deepnsm_shadow_distortion_chain_v1_latest.json"
    mdl_prune_poc = REPORTS / "universal_root_mdl_prune_poc_v1_latest.json"
    phase11a_chain = REPORTS / "logos_graphrag_phase11a_chain_v1_latest.json"
    phase11b_chain = REPORTS / "logos_graphrag_phase11b_chain_v1_latest.json"
    phase11d_chain = REPORTS / "logos_graphrag_phase11d_mdl_prune_chain_v1_latest.json"
    phase11e_chain = REPORTS / "logos_graphrag_phase11e_nsm_crosswalk_repair_chain_v1_latest.json"
    phase11f_chain = REPORTS / "logos_graphrag_phase11f_chain_v1_latest.json"
    phase11g_chain = REPORTS / "logos_graphrag_phase11g_shallow_stress_chain_v1_latest.json"
    phase11q_chain = REPORTS / "logos_graphrag_phase11q_compress_parity_chain_v1_latest.json"
    phase11r_chain = REPORTS / "logos_graphrag_phase11r_cost_deepnsm_stub_chain_v1_latest.json"
    phase11s_chain = REPORTS / "logos_graphrag_phase11s_evidence_nl_sync_chain_v1_latest.json"
    phase11t_chain = REPORTS / "logos_graphrag_phase11t_layer_stack_closure_chain_v1_latest.json"
    layer_stack_closure = ART / "universal_root_layer_stack_closure_v1_latest.json"
    deepnsm_hf_chain = REPORTS / "deepnsm_hf_explication_chain_v1_latest.json"
    deepnsm_hf_ab = REPORTS / "deepnsm_hf_ab_research_stub_v1_latest.json"
    phase15_chain = REPORTS / "logos_graphrag_phase15_deepnsm_hf_checkpoint_chain_v1_latest.json"
    phase16_chain = REPORTS / "logos_graphrag_phase16_topology_crosswalk_chain_v1_latest.json"
    phase17_chain = REPORTS / "logos_graphrag_phase17_closure_observability_chain_v1_latest.json"
    topology_crosswalk = REPORTS / "universal_root_topology_crosswalk_v1_latest.json"
    wall_exception_cards = ART / "UNIVERSAL_ROOT_WALL_DIVERGENCE_EXCEPTION_CARDS_V1.json"
    topology_spec = ART / "UNIVERSAL_ROOT_TOPOLOGY_CROSSWALK_SPEC_V1.json"
    p3_nsm_wire = REPORTS / "p3_root_nsm_wire_chain_v1_latest.json"
    miss_forensics = REPORTS / "logos_subgraph_gold_miss_forensics_v1_latest.json"
    oracle_gap = REPORTS / "ollama_shallow_routing_oracle_gap_v1_latest.json"
    shallow_bench = REPORTS / "ollama_shallow_router_bench_v1_latest.json"
    external_kg_manifest = ART / "logos_external_kg_ingest_manifest_v1_latest.json"
    human_gate_queue = ART / "logos_concept_bridge_human_gate_queue_v1_latest.json"
    joint_eval = REPORTS / "logos_graphrag_ollama_joint_eval_v1_latest.json"
    phase0_semiconductor = ART / "logos_concept_bridge_semiconductor_poc_v1_latest.json"

    bundle_doc = _read_json(graph_bundle)
    gf = bundle_doc.get("graph_files") if isinstance(bundle_doc.get("graph_files"), dict) else {}
    registry_doc = _read_json(concept_registry)
    lemma_doc = _read_json(lemma_manifest)
    replay_doc = _read_json(replay_summary)
    l3_doc = _read_json(l3)
    gold_doc = _read_json(gold_eval)
    gold_summary = gold_doc.get("summary") if isinstance(gold_doc.get("summary"), dict) else {}
    subgraph_gold_doc = _read_json(subgraph_gold_eval)
    subgraph_gold_summary = (
        subgraph_gold_doc.get("summary") if isinstance(subgraph_gold_doc.get("summary"), dict) else {}
    )
    external_kg_doc = _read_json(external_kg_manifest)
    human_gate_doc = _read_json(human_gate_queue)
    joint_eval_doc = _read_json(joint_eval)
    oracle_gap_doc = _read_json(oracle_gap)
    oracle_gap_raw = oracle_gap_doc.get("raw") if isinstance(oracle_gap_doc.get("raw"), dict) else {}
    shallow_bench_doc = _read_json(shallow_bench)
    shallow_bench_raw = shallow_bench_doc.get("raw") if isinstance(shallow_bench_doc.get("raw"), dict) else {}
    phase9_doc = _read_json(phase9_chain)
    phase10_doc = _read_json(phase10_chain)
    phase10c_doc = _read_json(phase10c_chain)
    sidecar_ablation_doc = _read_json(sidecar_ablation)
    sidecar_ablation_v2_doc = _read_json(sidecar_ablation_v2)
    sidecar_ablation_v3_doc = _read_json(sidecar_ablation_v3)
    v3_planes = sidecar_ablation_v3_doc.get("planes") if isinstance(sidecar_ablation_v3_doc.get("planes"), dict) else {}
    shallow_stress_gap_doc = _read_json(shallow_stress_gap)
    shallow_stress_bench_doc = _read_json(shallow_stress_bench)
    shallow_stress_gap_raw = (
        shallow_stress_gap_doc.get("raw") if isinstance(shallow_stress_gap_doc.get("raw"), dict) else {}
    )
    gate_spec_doc = _read_json(gate_spec)
    gate_eval_doc = _read_json(gate_eval)
    gate_eval_summary = gate_eval_doc.get("evaluation") if isinstance(gate_eval_doc.get("evaluation"), dict) else {}
    nsm_audit_doc = _read_json(nsm_audit)
    nsm_audit_raw_doc = _read_json(nsm_audit_raw)
    nsm_shadow_base = nsm_audit_doc.get("baseline") if isinstance(nsm_audit_doc.get("baseline"), dict) else {}
    nsm_raw_base = nsm_audit_raw_doc.get("baseline") if isinstance(nsm_audit_raw_doc.get("baseline"), dict) else {}
    deepnsm_chain_doc = _read_json(deepnsm_chain)
    mdl_prune_doc = _read_json(mdl_prune_poc)
    phase11a_doc = _read_json(phase11a_chain)
    phase11b_doc = _read_json(phase11b_chain)
    phase11d_doc = _read_json(phase11d_chain)
    phase11e_doc = _read_json(phase11e_chain)
    phase11f_doc = _read_json(phase11f_chain)
    phase11g_doc = _read_json(phase11g_chain)
    phase11q_doc = _read_json(phase11q_chain)
    phase11r_doc = _read_json(phase11r_chain)
    phase11s_doc = _read_json(phase11s_chain)
    phase11t_doc = _read_json(phase11t_chain)
    layer_stack_closure_doc = _read_json(layer_stack_closure)
    deepnsm_hf_chain_doc = _read_json(deepnsm_hf_chain)
    deepnsm_hf_ab_doc = _read_json(deepnsm_hf_ab)
    phase15_doc = _read_json(phase15_chain)
    phase16_doc = _read_json(phase16_chain)
    phase17_doc = _read_json(phase17_chain)
    topology_crosswalk_doc = _read_json(topology_crosswalk)
    wall_exception_cards_doc = _read_json(wall_exception_cards)
    p3_nsm_wire_doc = _read_json(p3_nsm_wire)
    baseline_observed = (
        gate_spec_doc.get("baseline_observed") if isinstance(gate_spec_doc.get("baseline_observed"), dict) else {}
    )
    miss_forensics_doc = _read_json(miss_forensics)
    joint_router_summary = (
        joint_eval_doc.get("router_summary") if isinstance(joint_eval_doc.get("router_summary"), dict) else {}
    )
    joint_corpus_snapshot = (
        joint_eval_doc.get("steps", {}).get("corpus_snapshot")
        if isinstance(joint_eval_doc.get("steps"), dict)
        else {}
    )
    if not isinstance(joint_corpus_snapshot, dict):
        joint_corpus_snapshot = {}
    local_snapshot = (
        external_kg_doc.get("local_snapshot") if isinstance(external_kg_doc.get("local_snapshot"), dict) else {}
    )
    external_sources = external_kg_doc.get("external_sources") or []
    release_full_ok_sources = [
        str(s.get("source_id"))
        for s in external_sources
        if isinstance(s, dict) and s.get("ingest_status") == "release_full_ok"
    ]
    lemma_jsonl_line_count = _count_jsonl_rows(lemma_jsonl)
    lemma_manifest_edge_count = int(lemma_doc.get("edge_count") or 0)

    static_phase0 = [
        phase0_semiconductor,
        ART / "logos_concept_bridge_covenant_crisis_poc_v1_latest.json",
    ]

    pack: dict[str, Any] = {
        "schema": "logos_graphrag_bridge_evidence_pack_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "ready_for_external_send": False,
        "track_l_gate_level": "L5_evidence_pack",
        "purpose": (
            "Internal audit pointers for Logos GraphRAG / original-language bridge Phase 0–1. "
            "Not a theology Q&A product claim; not Track A or live-trading enablement."
        ),
        "policy_pointers": {
            "bridge_ssot": _rel(bridge_ssot),
            "promotion_checklist": "docs/final/MKM_PROMOTION_GATE_CHECKLIST_L0_L12_V1.md",
            "public_facing_checklist": "docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md",
            "track_c_plan": "docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md",
        },
        "graph_snapshot": {
            "nodes_line_count": gf.get("nodes_line_count"),
            "edges_line_count": gf.get("edges_line_count"),
            "theme_association_edges": gf.get("theme_association_edges"),
        },
        "phase_coverage": {
            "phase_0_static_bridges": {
                "required_present": all(p.is_file() for p in static_phase0),
                "artifacts": [_rel(p) for p in static_phase0],
            },
            "phase_1_lemma_verse": {
                "jsonl": _snapshot(lemma_jsonl),
                "manifest": _snapshot(lemma_manifest),
                "edge_count_manifest": lemma_manifest_edge_count,
                "jsonl_line_count": lemma_jsonl_line_count,
                "edge_count_mismatch": lemma_manifest_edge_count != lemma_jsonl_line_count,
                "manifest_schema_ok": lemma_doc.get("schema") == "logos_lemma_verse_edges_v1",
            },
            "phase_2_concept_registry": {
                "bridge_count": registry_doc.get("bridge_count"),
                "human_reviewed_ratio": registry_doc.get("human_reviewed_ratio"),
                "governance_warning_zero_human": registry_doc.get("governance_warning_zero_human"),
            },
            "phase_3_subgraph_router": {
                "router_artifact": _snapshot(router_out),
                "replay_summary": _snapshot(replay_summary),
                "replay_pass": bool(replay_doc.get("pass")),
                "replay_pass_count": replay_doc.get("pass_count"),
                "replay_query_count": replay_doc.get("query_count"),
            },
            "phase_8_tier4_external_kg_full_stack": {
                "external_kg_manifest": _snapshot(external_kg_manifest),
                "external_source_count": len(external_sources),
                "release_full_ok_count": len(release_full_ok_sources),
                "release_full_ok_source_ids": release_full_ok_sources,
                "all_five_sources_release_full_ok": len(release_full_ok_sources) >= 5,
                "lexicon_line_counts": {
                    "sinew_xref_jsonl_lines": local_snapshot.get("sinew_xref_edges_jsonl_lines")
                    or joint_corpus_snapshot.get("sinew_xref_jsonl_lines"),
                    "osi_xref_jsonl_lines": local_snapshot.get("osi_xref_edges_jsonl_lines")
                    or joint_corpus_snapshot.get("osi_xref_jsonl_lines"),
                    "theographic_entity_jsonl_lines": local_snapshot.get("theographic_entity_edges_jsonl_lines")
                    or joint_corpus_snapshot.get("theographic_entity_jsonl_lines"),
                    "scriptures_js_gematria_lexicon_jsonl_lines": local_snapshot.get(
                        "scriptures_js_gematria_lexicon_jsonl_lines"
                    )
                    or joint_corpus_snapshot.get("scriptures_js_gematria_lexicon_jsonl_lines"),
                },
                "human_gate_queue": {
                    "artifact": _snapshot(human_gate_queue),
                    "queue_count": human_gate_doc.get("queue_count"),
                    "signoff_complete": human_gate_doc.get("queue_count") == 0,
                    "registry_human_reviewed_count": human_gate_doc.get("registry_human_reviewed_count"),
                },
                "concept_bridge": {
                    "bridge_count": registry_doc.get("bridge_count"),
                    "human_reviewed_count": registry_doc.get("human_reviewed_count"),
                    "human_reviewed_ratio": registry_doc.get("human_reviewed_ratio"),
                    "governance_warning_zero_human": registry_doc.get("governance_warning_zero_human"),
                },
                "joint_eval": {
                    "artifact": _snapshot(joint_eval),
                    "joint_ok": joint_eval_doc.get("joint_ok"),
                    "lemma_edge_hits": joint_eval_doc.get("lemma_edge_hits")
                    or joint_router_summary.get("lemma_edge_hits"),
                    "sinew_xref_hits": joint_eval_doc.get("sinew_xref_hits")
                    or joint_router_summary.get("sinew_xref_hits"),
                    "osi_xref_hits": joint_eval_doc.get("osi_xref_hits")
                    or joint_router_summary.get("osi_xref_hits"),
                    "theographic_entity_hits": joint_eval_doc.get("theographic_entity_hits")
                    or joint_router_summary.get("theographic_entity_hits"),
                    "gematria_lexicon_hits": joint_eval_doc.get("gematria_lexicon_hits")
                    or joint_router_summary.get("gematria_lexicon_hits"),
                },
            },
            "phase_9_oracle_gap_dual_gold_eval": {
                "phase9_chain": _snapshot(phase9_chain),
                "phase9_all_ok": phase9_doc.get("all_ok"),
                "oracle_gap": {
                    "artifact": _snapshot(oracle_gap),
                    "routing_oracle_gap": oracle_gap_raw.get("routing_oracle_gap"),
                    "router_hit_rate": oracle_gap_raw.get("router_hit_rate"),
                    "cloud_skip_ratio": oracle_gap_raw.get("cloud_skip_ratio"),
                    "deep_routing_recall": oracle_gap_raw.get("deep_routing_recall"),
                },
                "shallow_router_bench": {
                    "artifact": _snapshot(shallow_bench),
                    "parse_ok_rate_raw": shallow_bench_raw.get("parse_ok_rate"),
                    "router_hit_rate_raw": shallow_bench_raw.get("router_hit_rate"),
                },
                "dual_gold_eval": {
                    "subgraph_gold_required_all_pass": subgraph_gold_summary.get("gold_required_all_pass"),
                    "subgraph_hit_at_k_rates": subgraph_gold_summary.get("hit_at_k_rates"),
                    "magic_orb_gold_required_all_pass": gold_summary.get("gold_required_all_pass"),
                },
            },
            "phase_10_subgraph_gold_miss_tune": {
                "phase10_chain": _snapshot(phase10_chain),
                "phase10b_chain": _snapshot(REPORTS / "logos_graphrag_phase10b_chain_v1_latest.json"),
                "phase10c_chain": _snapshot(phase10c_chain),
                "phase10_all_ok": phase10_doc.get("all_ok"),
                "phase10c_all_ok": phase10c_doc.get("all_ok"),
                "forensics": _snapshot(miss_forensics),
                "router_version": subgraph_gold_doc.get("router_version"),
                "subgraph_hit_at_k_rates": subgraph_gold_summary.get("hit_at_k_rates"),
                "subgraph_gold_required_all_pass": subgraph_gold_summary.get("gold_required_all_pass"),
                "gold_item_count": subgraph_gold_summary.get("items_evaluated"),
                "miss_query_ids": miss_forensics_doc.get("miss_query_ids"),
                "sidecar_ablation": {
                    "artifact": _snapshot(sidecar_ablation),
                    "all_ok": sidecar_ablation_doc.get("all_ok"),
                    "baseline_hit_at_k_rates": sidecar_ablation_doc.get("baseline_hit_at_k_rates"),
                },
                "shallow_oracle_gap_stress": {
                    "artifact": _snapshot(shallow_stress_gap),
                    "bench_artifact": _snapshot(shallow_stress_bench),
                    "bench_mode": shallow_stress_bench_doc.get("mode"),
                    "router_hit_rate": shallow_stress_gap_raw.get("router_hit_rate"),
                    "routing_oracle_gap": shallow_stress_gap_raw.get("routing_oracle_gap"),
                    "cloud_skip_ratio": shallow_stress_gap_raw.get("cloud_skip_ratio"),
                    "deep_routing_recall": shallow_stress_gap_raw.get("deep_routing_recall"),
                },
            },
            "phase_11_universal_root_layer_stack": {
                "gate_spec": {
                    "artifact": _snapshot(gate_spec),
                    "version": gate_spec_doc.get("version"),
                    "phase": baseline_observed.get("phase"),
                    "send_gate": gate_spec_doc.get("send_gate"),
                },
                "gate_eval": {
                    "artifact": _snapshot(gate_eval),
                    "schema_validation_ok": gate_eval_doc.get("schema_validation_ok"),
                    "all_enabled_planes_ok": gate_eval_summary.get("all_enabled_planes_ok"),
                    "research_ready_decision": gate_eval_summary.get("research_ready_decision"),
                },
                "layer_a_nsm_crosswalk": {
                    "shadow_audit": _snapshot(nsm_audit),
                    "raw_latin_audit": _snapshot(nsm_audit_raw),
                    "audit_mode": nsm_audit_doc.get("audit_mode"),
                    "shadow_prime_hit_rate": nsm_shadow_base.get("prime_hit_rate"),
                    "shadow_distortion_rate": nsm_shadow_base.get("english_only_distortion_rate"),
                    "raw_distortion_rate": nsm_raw_base.get("english_only_distortion_rate"),
                    "distortion_gate_ok": (nsm_audit_doc.get("gates") or {}).get("gate_ok"),
                    "deepnsm_chain": _snapshot(deepnsm_chain),
                    "delta_shadow_minus_raw": deepnsm_chain_doc.get("delta_shadow_minus_raw"),
                },
                "layer_a_shallow_nsm_wire": {
                    "p3_nsm_wire_chain": _snapshot(p3_nsm_wire),
                    "p3_ok": p3_nsm_wire_doc.get("ok"),
                    "routing_oracle_gap_golden16": (
                        (p3_nsm_wire_doc.get("oracle_gap_summary") or {}).get("routing_oracle_gap")
                    ),
                },
                "layer_b_subgraph_sidecar_ablation_v2": {
                    "artifact": _snapshot(sidecar_ablation_v2),
                    "all_ok": sidecar_ablation_v2_doc.get("all_ok"),
                    "no_hit_at_1_regression": sidecar_ablation_v2_doc.get("no_hit_at_1_regression"),
                    "config_count": sidecar_ablation_v2_doc.get("config_count"),
                    "baseline_hit_at_k_rates": sidecar_ablation_v2_doc.get("baseline_hit_at_k_rates"),
                },
                "layer_b_subgraph_sidecar_ablation_v3": {
                    "artifact": _snapshot(sidecar_ablation_v3),
                    "all_ok": sidecar_ablation_v3_doc.get("all_ok"),
                    "retrieve_plane_ok": (v3_planes.get("retrieve_sidecar_v2") or {}).get("ok"),
                    "distortion_ok": v3_planes.get("distortion_ok"),
                    "distortion_delta": v3_planes.get("distortion_delta_shadow_minus_raw"),
                },
                "layer_c_mdl_prune_poc": {
                    "artifact": _snapshot(mdl_prune_poc),
                    "any_sweep_pass": mdl_prune_doc.get("any_sweep_pass"),
                    "baseline_jaccard": mdl_prune_doc.get("baseline_jaccard"),
                    "best_reduction_pct": (
                        (mdl_prune_doc.get("best_sweep") or {}).get("prune_meta") or {}
                    ).get("actual_reduction_pct"),
                },
                "layer_a_deepnsm_hf_ab": {
                    "hf_explication_chain": _snapshot(deepnsm_hf_chain),
                    "hf_ab_stub": _snapshot(deepnsm_hf_ab),
                    "ab_status": deepnsm_hf_ab_doc.get("ab_status"),
                    "comparison_ready": deepnsm_hf_ab_doc.get("comparison_ready"),
                    "delta_hf_minus_gematria": deepnsm_hf_ab_doc.get("delta_hf_minus_gematria"),
                    "hf_stub_prime_hit": (deepnsm_hf_chain_doc.get("hf_stub_audit") or {}).get("prime_hit_rate"),
                    "gematria_prime_hit_ref": (
                        (deepnsm_hf_chain_doc.get("gematria_shadow_audit_reference") or {}).get("prime_hit_rate")
                    ),
                },
                "layer_stack_closure_signoff": {
                    "artifact": _snapshot(layer_stack_closure),
                    "closure_ok": layer_stack_closure_doc.get("closure_ok"),
                    "enabled_plane_count": layer_stack_closure_doc.get("enabled_plane_count"),
                    "phase11t_chain": _snapshot(phase11t_chain),
                    "phase11t_ok": phase11t_doc.get("all_ok"),
                    "phase11s_ok": phase11s_doc.get("all_ok"),
                },
                "compress_and_cost_planes": {
                    "phase11q": _snapshot(phase11q_chain),
                    "phase11q_ok": phase11q_doc.get("all_ok"),
                    "compress_parity_saving_pct": (phase11q_doc.get("compress_parity") or {}).get(
                        "active_report_saving_pct"
                    ),
                    "phase11r": _snapshot(phase11r_chain),
                    "phase11r_ok": phase11r_doc.get("all_ok"),
                    "cost_cloud_skip_ratio": (phase11r_doc.get("cost_plane") or {}).get("cloud_skip_ratio"),
                    "enabled_plane_count": (phase11r_doc.get("gate_eval_summary") or {}).get("enabled_plane_count"),
                },
                "shallow_stress_live_32": {
                    "phase11g_chain": _snapshot(phase11g_chain),
                    "all_ok": phase11g_doc.get("all_ok"),
                    "live_ollama": phase11g_doc.get("live_ollama"),
                    "router_hit_rate": phase11g_doc.get("router_hit_rate"),
                    "routing_oracle_gap": phase11g_doc.get("routing_oracle_gap"),
                    "stress_gap_ok": phase11g_doc.get("stress_gap_ok"),
                },
                "phase_chains": {
                    "phase11a": {"artifact": _snapshot(phase11a_chain), "all_ok": phase11a_doc.get("all_ok")},
                    "phase11b": {"artifact": _snapshot(phase11b_chain), "all_ok": phase11b_doc.get("all_ok")},
                    "phase11d": {"artifact": _snapshot(phase11d_chain), "all_ok": phase11d_doc.get("all_ok")},
                    "phase11e": {"artifact": _snapshot(phase11e_chain), "all_ok": phase11e_doc.get("all_ok")},
                    "phase11f": {"artifact": _snapshot(phase11f_chain), "all_ok": phase11f_doc.get("all_ok")},
                    "phase11g": {"artifact": _snapshot(phase11g_chain), "all_ok": phase11g_doc.get("all_ok")},
                    "phase11q": {"artifact": _snapshot(phase11q_chain), "all_ok": phase11q_doc.get("all_ok")},
                    "phase11r": {"artifact": _snapshot(phase11r_chain), "all_ok": phase11r_doc.get("all_ok")},
                    "phase11s": {"artifact": _snapshot(phase11s_chain), "all_ok": phase11s_doc.get("all_ok")},
                    "phase11t": {"artifact": _snapshot(phase11t_chain), "all_ok": phase11t_doc.get("all_ok")},
                },
                "phase_15_16_17_deepnsm_topology_closure": {
                    "phase15_chain": _snapshot(phase15_chain),
                    "phase15_ok": phase15_doc.get("ok"),
                    "phase16_chain": _snapshot(phase16_chain),
                    "phase16_ok": phase16_doc.get("ok"),
                    "topology_crosswalk": _snapshot(topology_crosswalk),
                    "verse_reachable_rate": (topology_crosswalk_doc.get("summary") or {}).get("verse_reachable_rate"),
                    "prime_hit_rate": (topology_crosswalk_doc.get("lexicon_plane") or {}).get("prime_hit_rate"),
                    "wall_exception_cards": _snapshot(wall_exception_cards),
                    "wall_exception_count": (wall_exception_cards_doc.get("summary") or {}).get("exception_count"),
                    "topology_spec": _snapshot(topology_spec),
                    "phase17_chain": _snapshot(phase17_chain),
                    "phase17_ok": phase17_doc.get("ok"),
                    "bridge_query_id": phase17_doc.get("bridge_query_id"),
                },
                "shallow_router_note": (
                    "Layer A preprocess uses Ollama Modelfile (mkm-shallow-router-v1 on gemma4:e2b), "
                    "not LoRA weight fine-tuning. LoRA remains on Control-Integrity / Pack 0-B lanes."
                ),
            },
        },
        "track_l_readiness": {
            "l3_ok": bool(l3_doc.get("l3_ok")),
            "l3_artifact": _rel(l3),
        },
        "gold_eval_pointer": {
            "path": _rel(gold_eval),
            "exists": gold_eval.is_file(),
            "gold_required_all_pass": gold_summary.get("gold_required_all_pass"),
            "subgraph_gold_eval_path": _rel(subgraph_gold_eval),
            "subgraph_gold_eval_exists": subgraph_gold_eval.is_file(),
            "subgraph_gold_required_all_pass": subgraph_gold_summary.get("gold_required_all_pass"),
            "subgraph_hit_at_k_rates": subgraph_gold_summary.get("hit_at_k_rates"),
            "subgraph_gold_eval_chain_path": _rel(subgraph_gold_chain),
            "subgraph_gold_eval_chain_exists": subgraph_gold_chain.is_file(),
        },
        "s1_shadow_packet_pointer": _snapshot(s1_packet),
        "artifacts": {
            "logos_corpus_graph_bundle_v1_latest": _rel(graph_bundle),
            "logos_concept_bridge_registry_v1_latest": _rel(concept_registry),
            "logos_subgraph_graphrag_router_v1_latest": _rel(router_out),
            "logos_lemma_verse_edges_v1_jsonl": _rel(lemma_jsonl),
            "logos_lemma_verse_edges_v1_latest": _rel(lemma_manifest),
            "subgraph_router_replay_summary_latest": _rel(replay_summary),
            "logos_track_l_l3_readiness_v1_latest": _rel(l3),
            "logos_external_kg_ingest_manifest_v1_latest": _rel(external_kg_manifest),
            "logos_concept_bridge_human_gate_queue_v1_latest": _rel(human_gate_queue),
            "logos_graphrag_ollama_joint_eval_v1_latest": _rel(joint_eval),
            "logos_subgraph_gold_eval_v1_latest": _rel(subgraph_gold_eval),
            "logos_subgraph_gold_eval_chain_v1_latest": _rel(subgraph_gold_chain),
            "logos_graphrag_phase10_miss_tune_chain_v1_latest": _rel(phase10_chain),
            "logos_subgraph_gold_miss_forensics_v1_latest": _rel(miss_forensics),
            "ollama_shallow_routing_oracle_gap_v1_latest": _rel(oracle_gap),
            "universal_root_gate_spec_v1": _rel(gate_spec),
            "logos_subgraph_sidecar_ablation_v2_latest": _rel(sidecar_ablation_v2),
            "logos_graphrag_phase11g_shallow_stress_chain_v1_latest": _rel(phase11g_chain),
        },
        "reproduction_commands": [
            "py scripts/build_logos_concept_bridge_registry_v1.py",
            "py scripts/build_logos_lemma_verse_edges_v1.py",
            "py scripts/run_logos_subgraph_graphrag_router_v1.py --query-id q01 --top-bridges 3",
            "powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-GraphSubgraphLaneRecommendedChain_v1.ps1 -SkipPetPoC -SkipDeviceGraphSync",
            "py scripts/run_logos_track_l_l3_readiness_v1.py",
            "py scripts/run_logos_external_kg_full_stack_chain_v1.py --skip-osi-download --skip-sinew-download --skip-theographic-download --skip-scriptures-js-download",
            "py scripts/run_logos_subgraph_gold_eval_chain_v1.py",
            "py scripts/run_logos_graphrag_phase9_eval_chain_v1.py --skip-ollama-bench",
            "py scripts/run_logos_graphrag_phase10_miss_tune_chain_v1.py",
            "py scripts/run_logos_graphrag_phase11g_shallow_stress_chain_v1.py",
            "py scripts/run_logos_graphrag_phase11h_evidence_pack_chain_v1.py",
            "py scripts/build_logos_graphrag_bridge_evidence_pack_v1.py",
            "py scripts/run_logos_track_l_l4_l5_readiness_v1.py",
        ],
        "disclaimer": (
            "Lemma labels are pedagogical anchors until morphology SSOT exists. "
            "No prophecy hit-rate, no A-track merge, no live trading trigger from this pack."
        ),
    }

    out_json = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out_md = args.output_md if args.output_md.is_absolute() else ROOT / args.output_md
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md_lines = [
        "# Logos GraphRAG Bridge — Evidence Pack v1",
        "",
        f"- generated_at_utc: `{pack['generated_at_utc']}`",
        f"- ready_for_external_send: `{pack['ready_for_external_send']}`",
        f"- graph edges: `{pack['graph_snapshot'].get('edges_line_count')}`",
        f"- concept bridges: `{pack['phase_coverage']['phase_2_concept_registry'].get('bridge_count')}`",
        f"- subgraph replay: `{pack['phase_coverage']['phase_3_subgraph_router'].get('replay_pass_count')}/{pack['phase_coverage']['phase_3_subgraph_router'].get('replay_query_count')}`",
        f"- Track L L3: `{pack['track_l_readiness'].get('l3_ok')}`",
        "",
        "## Tier 4 external KG full stack",
    ]
    tier4 = pack["phase_coverage"].get("phase_8_tier4_external_kg_full_stack") or {}
    md_lines.extend(
        [
            f"- release_full_ok sources: `{tier4.get('release_full_ok_count')}/5`",
            f"- human_gate queue_count: `{((tier4.get('human_gate_queue') or {}).get('queue_count'))}`",
            f"- concept_bridge human_reviewed_ratio: `{((tier4.get('concept_bridge') or {}).get('human_reviewed_ratio'))}`",
            f"- joint_eval gematria_lexicon_hits: `{((tier4.get('joint_eval') or {}).get('gematria_lexicon_hits'))}`",
            f"- subgraph gold eval exists: `{pack['gold_eval_pointer'].get('subgraph_gold_eval_exists')}`",
            "",
            "## Phase 11 — Universal Root layer stack (B-track)",
        ]
    )
    phase11 = pack["phase_coverage"].get("phase_11_universal_root_layer_stack") or {}
    layer_a = phase11.get("layer_a_nsm_crosswalk") or {}
    stress = phase11.get("shallow_stress_live_32") or {}
    md_lines.extend(
        [
            f"- GATE_SPEC phase: `{((phase11.get('gate_spec') or {}).get('phase'))}`",
            f"- distortion shadow/remapped: `{layer_a.get('shadow_distortion_rate')}` / raw `{layer_a.get('raw_distortion_rate')}`",
            f"- sidecar ablation v2 configs: `{((phase11.get('layer_b_subgraph_sidecar_ablation_v2') or {}).get('config_count'))}`",
            f"- live shallow stress 32 hit: `{stress.get('router_hit_rate')}` gap `{stress.get('routing_oracle_gap')}`",
            f"- Modelfile note: Layer A shallow = Modelfile lock-in, not LoRA",
            "",
            "## SSOT",
        ]
    )
    md_lines.extend(
        [
            f"- `{pack['policy_pointers']['bridge_ssot']}`",
            "",
            "## Reproduction",
        ]
    )
    for cmd in pack["reproduction_commands"]:
        md_lines.append(f"- `{cmd}`")
    out_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(json.dumps({"ok": True, "out_json": str(out_json), "out_md": str(out_md)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
