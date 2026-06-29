#!/usr/bin/env python3
"""Refresh UNIVERSAL_ROOT_GATE_SPEC baseline_observed from latest artifacts [HYPO]."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPEC = ROOT / "docs/final/artifacts/UNIVERSAL_ROOT_GATE_SPEC_V1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def refresh_baseline(spec: dict[str, Any]) -> dict[str, Any]:
    nsm = _read(ROOT / "reports/nsm_41k_lexicon_crosswalk_audit_v1_latest.json")
    nsm_raw = _read(ROOT / "reports/nsm_41k_lexicon_crosswalk_audit_raw_v1_latest.json")
    deepnsm = _read(ROOT / "reports/deepnsm_shadow_distortion_chain_v1_latest.json")
    gold = _read(ROOT / "reports/logos_subgraph_gold_eval_v1_latest.json")
    mdl = _read(ROOT / "reports/universal_root_mdl_prune_poc_v1_latest.json")
    mdl_gate = _read(ROOT / "reports/universal_root_mdl_prune_gate_v1_latest.json")
    comp_atom02 = _read(
        ROOT / "reports/constitution/btrack_pilot/comp_atom02_lexicon_must_keep_analysis_v1.json"
    )
    route = _read(ROOT / "reports/ollama_shallow_routing_oracle_gap_v1_latest.json")
    route_stress = _read(ROOT / "reports/ollama_shallow_oracle_gap_stress_v1_latest.json")
    hf_ab = _read(ROOT / "reports/deepnsm_hf_ab_research_stub_v1_latest.json")
    hf_chain = _read(ROOT / "reports/deepnsm_hf_explication_chain_v1_latest.json")
    hf_ollama_chain = _read(ROOT / "reports/deepnsm_hf_explication_ollama_chain_v1_latest.json")
    hf_ollama_500_chain = _read(ROOT / "reports/deepnsm_hf_explication_ollama_500_chain_v1_latest.json")
    hf_checkpoint_chain = _read(ROOT / "reports/deepnsm_hf_explication_checkpoint_chain_v1_latest.json")
    cost_deep = _read(ROOT / "reports/ollama_shallow_cost_deep_bench_v1_latest.json")
    closure = _read(ROOT / "docs/final/artifacts/universal_root_layer_stack_closure_v1_latest.json")
    phase12_live = _read(ROOT / "reports/logos_phase12_live_bundle_v1_latest.json")
    showroom_smoke = _read(ROOT / "reports/showroom_trust_viz_public_chain_smoke_latest.json")
    topology = _read(ROOT / "reports/universal_root_topology_crosswalk_v1_latest.json")
    topology_gate = _read(ROOT / "reports/universal_root_topology_crosswalk_gate_v1_latest.json")
    phase16_chain = _read(ROOT / "reports/logos_graphrag_phase16_topology_crosswalk_chain_v1_latest.json")

    nsm_base = nsm.get("baseline") or {}
    nsm_raw_base = nsm_raw.get("baseline") or {}
    gold_sum = gold.get("summary") or {}
    gold_rates = gold_sum.get("hit_at_k_rates") or {}
    route_raw = route.get("raw") or {}
    route_stress_raw = route_stress.get("raw") or {}

    layer_c: dict[str, Any] = {"status": "not_run"}
    if mdl:
        best = mdl.get("best_sweep") or {}
        layer_c = {
            "status": "poc_complete" if mdl.get("any_sweep_pass") else "poc_fail",
            "report": "reports/universal_root_mdl_prune_poc_v1_latest.json",
            "baseline_jaccard": mdl.get("baseline_jaccard"),
            "any_sweep_pass": mdl.get("any_sweep_pass"),
            "best_actual_reduction_pct": (best.get("prune_meta") or {}).get("actual_reduction_pct"),
            "best_jaccard_delta_pp": best.get("jaccard_delta_pp_vs_baseline"),
        }

    out = dict(spec)
    out["version"] = "1.1.0"
    out["generated_at_utc"] = _utc()
    distortion_gate_ok = (nsm.get("gates") or {}).get("gate_ok")
    compress_observed: dict[str, Any] = {"status": "not_run"}
    if comp_atom02:
        ablation = comp_atom02.get("compression_ablation") or comp_atom02.get("ablation") or {}
        lex_on = ablation.get("lexicon_on") or {}
        lex_off = ablation.get("lexicon_off") or {}
        parity = comp_atom02.get("active_report_parity") or {}
        gate_profile = parity if parity.get("global_token_saving_rate") is not None else lex_on
        saving = gate_profile.get("global_token_saving_rate")
        jaccard = gate_profile.get("avg_reconstruction_fidelity_jaccard")
        would_pass = (
            saving is not None
            and jaccard is not None
            and float(saving) >= 0.465
            and float(jaccard) >= 0.885
        )
        compress_observed = {
            "status": "observed",
            "report": "reports/constitution/btrack_pilot/comp_atom02_lexicon_must_keep_analysis_v1.json",
            "gate_profile": comp_atom02.get("gate_compress_profile") or "active_report_parity",
            "strict_lexicon_on": lex_on,
            "lexicon_off": lex_off,
            "active_report_parity": parity,
            "gate_metrics": gate_profile,
            "delta_on_minus_off": ablation.get("delta_on_minus_off"),
            "gate_threshold_saving_pct": 46.5,
            "gate_threshold_jaccard": 0.885,
            "compress_plane_would_pass": would_pass,
        }

    cost_ready = (
        compress_observed.get("compress_plane_would_pass")
        and route_stress_raw.get("cloud_skip_ratio") is not None
        and float(route_stress_raw.get("cloud_skip_ratio") or 0) >= 0.95
    )
    hf_paired = bool(hf_ab.get("comparison_ready"))
    cost_deep_ok = bool(cost_deep.get("deep_bench_ok"))
    closure_ok = bool(closure.get("closure_ok"))
    live_public_ok = (
        bool(phase12_live.get("ok"))
        and bool(phase12_live.get("jemaai_core_ok"))
        and bool(showroom_smoke.get("ok"))
    )
    hf_ollama_ok = (
        hf_ollama_chain.get("implementation_status") == "ollama_local_weights_v1"
        and bool(hf_ollama_chain.get("ok"))
        and int(hf_ollama_chain.get("pair_count") or 0) >= 100
    )
    hf_ollama_full_ok = (
        hf_ollama_500_chain.get("implementation_status") == "ollama_local_weights_v1"
        and bool(hf_ollama_500_chain.get("ok"))
        and int(hf_ollama_500_chain.get("pair_count") or 0) >= 500
        and bool((hf_ollama_500_chain.get("hf_ollama_audit") or {}).get("gate_ok"))
    )
    hf_checkpoint_ok = (
        hf_checkpoint_chain.get("implementation_status") == "deepnsm_hf_checkpoint_v1"
        and bool(hf_checkpoint_chain.get("ok"))
        and int(hf_checkpoint_chain.get("pair_count") or 0) >= 100
        and bool((hf_checkpoint_chain.get("hf_checkpoint_audit") or {}).get("gate_ok"))
    )
    topology_ok = bool(topology_gate.get("gate_ok")) and bool((topology.get("summary") or {}).get("verse_reachable_rate") is not None)
    phase17_chain = _read(ROOT / "reports/logos_graphrag_phase17_closure_observability_chain_v1_latest.json")
    phase17_ok = bool(phase17_chain.get("ok"))
    if phase17_ok and topology_ok and hf_checkpoint_ok and hf_ollama_full_ok and hf_ollama_ok and closure_ok and live_public_ok:
        phase = "17"
    elif topology_ok and hf_checkpoint_ok and hf_ollama_full_ok and hf_ollama_ok and closure_ok and live_public_ok:
        phase = "16"
    elif hf_checkpoint_ok and hf_ollama_full_ok and hf_ollama_ok and closure_ok and live_public_ok:
        phase = "15"
    elif hf_ollama_full_ok and hf_ollama_ok and closure_ok and live_public_ok:
        phase = "14"
    elif hf_ollama_ok and closure_ok and live_public_ok:
        phase = "13"
    elif closure_ok and live_public_ok:
        phase = "12"
    elif hf_ollama_ok:
        phase = "11-U"
    elif closure_ok or cost_deep_ok:
        phase = "11-T"
    elif hf_paired:
        phase = "11-S"
    elif cost_ready:
        phase = "11-R"
    elif compress_observed.get("compress_plane_would_pass"):
        phase = "11-Q"
    else:
        phase = "11-P"

    out["baseline_observed"] = {
        "phase": phase,
        "observed_at_utc": _utc(),
        "distortion_raw_latin": {
            "fixture": "tests/fixtures/nsm_41k_lexicon_crosswalk_500_v1.json",
            "audit_mode": nsm_raw.get("audit_mode") or "raw_latin",
            "pair_count": nsm_raw_base.get("pair_count"),
            "prime_hit_rate": nsm_raw_base.get("prime_hit_rate"),
            "english_only_distortion_rate": nsm_raw_base.get("english_only_distortion_rate"),
            "negative_control_leak_count": nsm_raw_base.get("negative_control_leak_count"),
            "gate_ok": (nsm_raw.get("gates") or {}).get("gate_ok"),
            "report": "reports/nsm_41k_lexicon_crosswalk_audit_raw_v1_latest.json",
        },
        "distortion_shadow_remapped": {
            "fixture": "tests/fixtures/nsm_41k_lexicon_crosswalk_500_v1.json",
            "audit_mode": nsm.get("audit_mode") or "deepnsm_shadow",
            "explication_sidecar": nsm.get("explication_sidecar"),
            "pair_count": nsm_base.get("pair_count"),
            "prime_hit_rate": nsm_base.get("prime_hit_rate"),
            "english_only_distortion_rate": nsm_base.get("english_only_distortion_rate"),
            "negative_control_leak_count": nsm_base.get("negative_control_leak_count"),
            "gate_ok": (nsm.get("gates") or {}).get("gate_ok"),
            "report": "reports/nsm_41k_lexicon_crosswalk_audit_v1_latest.json",
        },
        "distortion_delta_shadow_minus_raw": deepnsm.get("delta_shadow_minus_raw") or {},
        "retrieve": {
            "fixture": "docs/final/fixtures/logos_gold_query_eval_v1.json",
            "items_evaluated": gold_sum.get("items_evaluated"),
            "hit_at_k_rates": gold_rates,
            "gold_required_all_pass": gold_sum.get("gold_required_all_pass"),
            "router_version": gold.get("router_version"),
            "known_miss_resolved": ["q31"],
        },
        "route": {
            "report": "reports/ollama_shallow_routing_oracle_gap_v1_latest.json",
            "routing_oracle_gap": route_raw.get("routing_oracle_gap"),
            "router_hit_rate": route_raw.get("router_hit_rate"),
        },
        "route_stress_live_32": {
            "report": "reports/ollama_shallow_oracle_gap_stress_v1_latest.json",
            "fixture": "tests/fixtures/ollama_shallow_router_golden_combined_stress_v1.json",
            "bench_report": "reports/ollama_shallow_router_bench_stress_v1_latest.json",
            "modelfile": "docs/final/artifacts/ollama_mkm_shallow_router_modelfile_v1.txt",
            "modelfile_version": "v1.3",
            "router_hit_rate": route_stress_raw.get("router_hit_rate"),
            "routing_oracle_gap": route_stress_raw.get("routing_oracle_gap"),
            "cloud_skip_ratio": route_stress_raw.get("cloud_skip_ratio"),
            "deep_routing_recall": route_stress_raw.get("deep_routing_recall"),
        },
        "layer_c_mdl": layer_c,
        "compress_golden40": compress_observed,
        "deepnsm_hf_ab": {
            "ab_status": hf_ab.get("ab_status"),
            "comparison_ready": hf_paired,
            "implementation_status": hf_ollama_chain.get("implementation_status")
            or hf_chain.get("implementation_status"),
            "ollama_pilot_ok": hf_ollama_ok,
            "delta_hf_minus_gematria": hf_ab.get("delta_hf_minus_gematria")
            or hf_ollama_chain.get("delta_hf_ollama_minus_gematria")
            or hf_chain.get("delta_hf_stub_minus_gematria"),
            "report": "reports/deepnsm_hf_ab_research_stub_v1_latest.json",
            "chain_report": (
                "reports/deepnsm_hf_explication_ollama_chain_v1_latest.json"
                if hf_ollama_ok
                else "reports/deepnsm_hf_explication_chain_v1_latest.json"
            ),
        },
        "cost_deep_bench": {
            "deep_bench_ok": cost_deep_ok,
            "golden16": ((cost_deep.get("profiles") or {}).get("golden16") or {}).get("raw"),
            "combined32": ((cost_deep.get("profiles") or {}).get("combined32") or {}).get("raw"),
            "delta_combined32_minus_golden16": cost_deep.get("delta_combined32_minus_golden16"),
            "report": "reports/ollama_shallow_cost_deep_bench_v1_latest.json",
        },
        "layer_stack_closure": {
            "closure_ok": closure_ok,
            "report": "docs/final/artifacts/universal_root_layer_stack_closure_v1_latest.json",
            "enabled_plane_count": closure.get("enabled_plane_count"),
        },
        "phase12_live_public": {
            "live_bundle_ok": phase12_live.get("ok"),
            "jemaai_core_ok": phase12_live.get("jemaai_core_ok"),
            "showroom_smoke_ok": showroom_smoke.get("ok"),
            "live_bundle_report": "reports/logos_phase12_live_bundle_v1_latest.json",
            "showroom_smoke_report": "reports/showroom_trust_viz_public_chain_smoke_latest.json",
        },
        "phase13_deepnsm_hf_ollama": {
            "implementation_status": hf_ollama_chain.get("implementation_status"),
            "pilot_ok": hf_ollama_ok,
            "pair_count": hf_ollama_chain.get("pair_count"),
            "ollama_model": (hf_ollama_chain.get("ollama_meta") or {}).get("ollama_model"),
            "hf_audit": hf_ollama_chain.get("hf_ollama_audit"),
            "delta_hf_minus_gematria": hf_ollama_chain.get("delta_hf_ollama_minus_gematria"),
            "chain_report": "reports/deepnsm_hf_explication_ollama_chain_v1_latest.json",
            "sidecar": "docs/final/artifacts/deepnsm_hf_explication_ollama_v1.jsonl",
        },
        "phase14_deepnsm_hf_ollama_500": {
            "implementation_status": hf_ollama_500_chain.get("implementation_status"),
            "full_audit_ok": hf_ollama_full_ok,
            "pair_count": hf_ollama_500_chain.get("pair_count"),
            "ollama_model": (hf_ollama_500_chain.get("ollama_meta") or {}).get("ollama_model"),
            "hf_audit": hf_ollama_500_chain.get("hf_ollama_audit"),
            "delta_hf_minus_gematria": hf_ollama_500_chain.get("delta_hf_ollama_minus_gematria"),
            "chain_report": "reports/deepnsm_hf_explication_ollama_500_chain_v1_latest.json",
            "sidecar": "docs/final/artifacts/deepnsm_hf_explication_ollama_500_v1.jsonl",
            "stub_vs_ollama_ab": "reports/deepnsm_hf_stub_vs_ollama_500_ab_v1_latest.json",
        },
        "phase15_deepnsm_hf_checkpoint": {
            "implementation_status": hf_checkpoint_chain.get("implementation_status"),
            "pilot_ok": hf_checkpoint_ok,
            "pair_count": hf_checkpoint_chain.get("pair_count"),
            "checkpoint_model": (hf_checkpoint_chain.get("checkpoint_meta") or {}).get("checkpoint_model"),
            "base_model": (hf_checkpoint_chain.get("checkpoint_meta") or {}).get("base_model"),
            "hf_audit": hf_checkpoint_chain.get("hf_checkpoint_audit"),
            "delta_hf_minus_gematria": hf_checkpoint_chain.get("delta_hf_checkpoint_minus_gematria"),
            "chain_report": "reports/deepnsm_hf_explication_checkpoint_chain_v1_latest.json",
            "sidecar": "docs/final/artifacts/deepnsm_hf_explication_checkpoint_v1.jsonl",
            "ollama_vs_checkpoint_ab": "reports/deepnsm_hf_ollama_vs_checkpoint_ab_v1_latest.json",
        },
        "phase16_topology_crosswalk": {
            "implementation_status": phase16_chain.get("implementation_status") or "topology_crosswalk_v1",
            "topology_ok": topology_ok,
            "pair_count": (topology.get("summary") or {}).get("pair_count"),
            "lexicon_plane": topology.get("lexicon_plane") or {},
            "topology_plane": topology.get("topology_plane") or {},
            "wall_divergence": topology.get("wall_divergence") or {},
            "delta_topology_minus_lexicon": topology.get("delta_topology_minus_lexicon") or {},
            "spec": "docs/final/artifacts/UNIVERSAL_ROOT_TOPOLOGY_CROSSWALK_SPEC_V1.json",
            "crosswalk_report": "reports/universal_root_topology_crosswalk_v1_latest.json",
            "gate_report": "reports/universal_root_topology_crosswalk_gate_v1_latest.json",
            "chain_report": "reports/logos_graphrag_phase16_topology_crosswalk_chain_v1_latest.json",
        },
        "phase17_closure_observability": {
            "implementation_status": phase17_chain.get("implementation_status") or "closure_observability_v1",
            "closure_ok": phase17_ok,
            "wall_exception_count": phase17_chain.get("wall_exception_count"),
            "wall_cards": "docs/final/artifacts/UNIVERSAL_ROOT_WALL_DIVERGENCE_EXCEPTION_CARDS_V1.json",
            "bridge_query_id": phase17_chain.get("bridge_query_id"),
            "observability_chain_pass": phase17_chain.get("observability_chain_pass"),
            "chain_report": "reports/logos_graphrag_phase17_closure_observability_chain_v1_latest.json",
        },
        "distortion": {
            "fixture": "tests/fixtures/nsm_41k_lexicon_crosswalk_500_v1.json",
            "audit_mode": nsm.get("audit_mode") or "deepnsm_shadow",
            "pair_count": nsm_base.get("pair_count"),
            "prime_hit_rate": nsm_base.get("prime_hit_rate"),
            "english_only_distortion_rate": nsm_base.get("english_only_distortion_rate"),
            "negative_control_leak_count": nsm_base.get("negative_control_leak_count"),
            "gate_ok": distortion_gate_ok,
            "report": "reports/nsm_41k_lexicon_crosswalk_audit_v1_latest.json",
        },
    }
    layers = dict(out.get("layers") or {})
    layer_a_cfg = dict(layers.get("layer_a") or {})
    layer_a_cfg["implementation_status"] = "partial"
    layer_a_cfg["scripts"] = [
        "scripts/run_nsm_41k_lexicon_crosswalk_audit_v1.py",
        "scripts/build_nsm_41k_crosswalk_500_fixture_v1.py",
        "scripts/run_deepnsm_shadow_explication_chain_v1.py",
        "scripts/run_deepnsm_shadow_distortion_chain_v1.py",
        "scripts/run_deepnsm_hf_explication_chain_v1.py",
        "scripts/build_ollama_shallow_routing_oracle_gap_v1.py",
    ]
    layers["layer_a"] = layer_a_cfg
    layer_c_cfg = dict(layers.get("layer_c") or {})
    layer_c_cfg["implementation_status"] = "poc" if mdl else "not_run"
    layer_c_cfg["scripts"] = [
        "scripts/run_universal_root_mdl_prune_poc_v1.py",
        "scripts/check_universal_root_mdl_prune_gate_v1.py",
    ]
    layers["layer_c"] = layer_c_cfg
    out["layers"] = layers
    repro = dict(out.get("reproduce") or {})
    repro["deepnsm_shadow_chain"] = "py scripts/run_deepnsm_shadow_distortion_chain_v1.py"
    repro["mdl_prune_poc"] = "py scripts/run_universal_root_mdl_prune_poc_v1.py"
    repro["phase11d_chain"] = "py scripts/run_logos_graphrag_phase11d_mdl_prune_chain_v1.py"
    repro["phase11e_chain"] = "py scripts/run_logos_graphrag_phase11e_nsm_crosswalk_repair_chain_v1.py"
    repro["phase11f_chain"] = "py scripts/run_logos_graphrag_phase11f_chain_v1.py"
    repro["phase11g_chain"] = "py scripts/run_logos_graphrag_phase11g_shallow_stress_chain_v1.py"
    repro["phase11i_chain"] = "py scripts/run_logos_graphrag_phase11i_shallow_modelfile_tune_chain_v1.py"
    repro["phase11k_chain"] = "py scripts/run_logos_graphrag_phase11k_sidecar_ablation_v3_chain_v1.py"
    repro["phase11l_chain"] = "py scripts/run_logos_graphrag_phase11l_closure_refresh_chain_v1.py"
    repro["phase11m_chain"] = "py scripts/run_logos_graphrag_phase11m_research_impl_bridge_chain_v1.py"
    repro["phase11p_chain"] = "py scripts/run_logos_graphrag_phase11p_compress_layerc_gate_chain_v1.py"
    repro["phase11q_chain"] = "py scripts/run_logos_graphrag_phase11q_compress_parity_chain_v1.py"
    repro["phase11r_chain"] = "py scripts/run_logos_graphrag_phase11r_cost_deepnsm_stub_chain_v1.py"
    repro["phase11s_chain"] = "py scripts/run_logos_graphrag_phase11s_evidence_nl_sync_chain_v1.py"
    repro["phase11t_chain"] = "py scripts/run_logos_graphrag_phase11t_cost_deep_bench_chain_v1.py"
    repro["phase11u_chain"] = "py scripts/run_logos_graphrag_phase11u_deepnsm_hf_ollama_chain_v1.py"
    repro["phase12_chain"] = "py scripts/run_logos_graphrag_phase12_live_public_chain_v1.py"
    repro["phase13_chain"] = "py scripts/run_logos_graphrag_phase13_deepnsm_hf_ollama_chain_v1.py"
    repro["phase14_chain"] = "py scripts/run_logos_graphrag_phase14_deepnsm_hf_ollama_500_chain_v1.py"
    repro["phase15_chain"] = "py scripts/run_logos_graphrag_phase15_deepnsm_hf_checkpoint_chain_v1.py"
    repro["phase16_chain"] = "py scripts/run_logos_graphrag_phase16_topology_crosswalk_chain_v1.py"
    repro["phase17_chain"] = "py scripts/run_logos_graphrag_phase17_closure_observability_chain_v1.py"
    repro["wall_divergence_exception_cards"] = "py scripts/build_universal_root_wall_divergence_exception_cards_v1.py"
    repro["topology_crosswalk_build"] = "py scripts/build_universal_root_topology_crosswalk_v1.py"
    repro["topology_crosswalk_gate"] = "py scripts/check_universal_root_topology_crosswalk_v1.py"
    repro["stub_vs_ollama_500_ab"] = "py scripts/build_deepnsm_hf_stub_vs_ollama_500_ab_v1.py"
    repro["ollama_vs_checkpoint_ab"] = "py scripts/build_deepnsm_hf_ollama_vs_checkpoint_ab_v1.py"
    repro["checkpoint_prereqs"] = "py scripts/check_deepnsm_hf_checkpoint_prereqs_v1.py"
    repro["phase12_live_bundle"] = "py scripts/build_logos_phase12_live_bundle_v1.py"
    repro["showroom_public_smoke"] = "py scripts/check_showroom_trust_viz_public_chain_v1.py"
    repro["cost_deep_bench"] = "py scripts/build_ollama_shallow_cost_deep_bench_v1.py"
    repro["deepnsm_hf_explication_chain"] = "py scripts/run_deepnsm_hf_explication_chain_v1.py"
    repro["deepnsm_hf_ab_stub"] = "py scripts/build_deepnsm_hf_ab_research_stub_v1.py"
    repro["comp_atom02"] = "py scripts/comp_atom02_lexicon_must_keep_analysis_v1.py"
    repro["sidecar_ablation_v3"] = "py scripts/run_universal_root_sidecar_ablation_v3_chain_v1.py"
    out["reproduce"] = repro
    gates = dict(out.get("promotion_gates") or {})
    planes = dict(gates.get("planes") or {})
    distortion_plane = dict(planes.get("distortion") or {})
    shadow_dr = nsm_base.get("english_only_distortion_rate")
    raw_dr = nsm_raw_base.get("english_only_distortion_rate")
    distortion_plane["notes"] = (
        "Layer A audit uses DeepNSM shadow remapping (gematria lemma script → 41k Unicode forms). "
        f"Raw latin: distortion {raw_dr}; shadow remapped: distortion {shadow_dr}; gate_ok={distortion_gate_ok}."
    )
    planes["distortion"] = distortion_plane
    layer_c_plane = dict(planes.get("layer_c_mdl") or {})
    if mdl_gate.get("gate_ok"):
        layer_c_plane["enabled"] = True
        layer_c_plane["notes"] = (
            "Morfessor-class PoC gate_ok=true (Phase 11-D/11-P). "
            f"best_reduction={(layer_c.get('best_actual_reduction_pct'))}%; "
            f"jaccard_delta_pp={(layer_c.get('best_jaccard_delta_pp'))}."
        )
    planes["layer_c_mdl"] = layer_c_plane
    compress_plane = dict(planes.get("compress") or {})
    if compress_observed.get("status") == "observed":
        would_pass = compress_observed.get("compress_plane_would_pass")
        gate_metrics = compress_observed.get("gate_metrics") or {}
        strict = compress_observed.get("strict_lexicon_on") or {}
        compress_plane["notes"] = (
            "Golden-40 V2 — gate uses active_report_parity (frozen Track A run_config). "
            f"parity saving={gate_metrics.get('global_token_saving_rate')}; "
            f"jaccard={gate_metrics.get('avg_reconstruction_fidelity_jaccard')}; "
            f"strict_lexicon_on saving={strict.get('global_token_saving_rate')}; "
            f"would_pass={would_pass}."
        )
        if would_pass:
            compress_plane["enabled"] = True
    planes["compress"] = compress_plane
    cost_plane = dict(planes.get("cost") or {})
    stress_skip = route_stress_raw.get("cloud_skip_ratio")
    combined_raw = ((cost_deep.get("profiles") or {}).get("combined32") or {}).get("raw") or {}
    deep_recall = combined_raw.get("deep_routing_recall") or route_stress_raw.get("deep_routing_recall")
    if cost_deep_ok or (stress_skip is not None and float(stress_skip) >= 0.95):
        cost_plane["enabled"] = True
        cost_thr = dict(cost_plane.get("thresholds") or {})
        cost_thr.setdefault("min_cloud_skip_ratio", 0.95)
        if cost_deep_ok:
            cost_thr.setdefault("min_deep_routing_recall", 0.95)
        cost_plane["thresholds"] = cost_thr
        cost_plane["notes"] = (
            "Shallow cost deep bench (golden16 + combined32). "
            f"combined32 cloud_skip_ratio={combined_raw.get('cloud_skip_ratio') or stress_skip}; "
            f"deep_routing_recall={deep_recall}; "
            "not OS-wide API cost claim."
        )
    planes["cost"] = cost_plane
    topology_plane = dict(planes.get("topology") or {})
    topo_summary = topology.get("summary") or {}
    topo_wall = topology.get("wall_divergence") or {}
    topology_thr = dict(topology_plane.get("thresholds") or {})
    topology_thr.setdefault("fixture_pair_count_min", 500)
    topology_thr.setdefault("min_verse_reachable_rate", 0.5)
    topology_thr.setdefault("max_lexicon_only_without_topology_rate", 0.02)
    topology_plane["thresholds"] = topology_thr
    if topology_ok:
        topology_plane["enabled"] = True
        topology_plane["notes"] = (
            "Phase16 41k↔31k metric plane separation. "
            f"verse_reachable={topo_summary.get('verse_reachable_rate')}; "
            f"prime_hit={topo_summary.get('prime_hit_rate')}; "
            f"lexicon_only_without_topology_rate={topo_wall.get('lexicon_only_without_topology_rate')}; "
            f"gate_ok={topology_gate.get('gate_ok')}."
        )
    else:
        topology_plane["enabled"] = False
        topology_plane["notes"] = (
            "Phase16 topology crosswalk gate not yet satisfied — run "
            "scripts/run_logos_graphrag_phase16_topology_crosswalk_chain_v1.py"
        )
    planes["topology"] = topology_plane
    gates["planes"] = planes
    out["promotion_gates"] = gates
    metric_planes = dict(out.get("metric_planes") or {})
    metric_planes["topology"] = {
        "scope": "NSM prime probes → 31k verse atom graph reachability; separate from 41k lexicon distortion plane",
        "primary_metrics": [
            "verse_reachable_rate",
            "lexicon_only_without_topology_rate",
            "negative_topology_leak_count",
        ],
        "script": "scripts/build_universal_root_topology_crosswalk_v1.py",
        "never_collapse_with": [
            "prime_hit_rate",
            "hit_at_k",
            "compress_jaccard",
        ],
    }
    out["metric_planes"] = metric_planes
    forbidden = list(out.get("forbidden_claims") or [])
    for claim in (
        "verse_reachable_rate replaces 41k lexicon prime_hit for Track A promotion",
        "41k lexicon hit proves Logos subgraph hit_at_k readiness",
        "collapsed topology_lexicon_combined_score used as promotion KPI",
    ):
        if claim not in forbidden:
            forbidden.append(claim)
    out["forbidden_claims"] = forbidden
    ptr = dict(out.get("artifact_pointers") or {})
    ptr["deepnsm_shadow_sidecar"] = "docs/final/artifacts/deepnsm_shadow_explication_v1.jsonl"
    ptr["deepnsm_shadow_chain_latest"] = "reports/deepnsm_shadow_distortion_chain_v1_latest.json"
    ptr["nsm_audit_raw_latest"] = "reports/nsm_41k_lexicon_crosswalk_audit_raw_v1_latest.json"
    ptr["mdl_prune_poc_latest"] = "reports/universal_root_mdl_prune_poc_v1_latest.json"
    ptr["mdl_prune_gate_latest"] = "reports/universal_root_mdl_prune_gate_v1_latest.json"
    ptr["phase11d_chain_latest"] = "reports/logos_graphrag_phase11d_mdl_prune_chain_v1_latest.json"
    ptr["phase11e_chain_latest"] = "reports/logos_graphrag_phase11e_nsm_crosswalk_repair_chain_v1_latest.json"
    ptr["sidecar_ablation_v2_latest"] = "reports/logos_subgraph_sidecar_ablation_v2_latest.json"
    ptr["phase11f_chain_latest"] = "reports/logos_graphrag_phase11f_chain_v1_latest.json"
    ptr["shallow_stress_gap_latest"] = "reports/ollama_shallow_oracle_gap_stress_v1_latest.json"
    ptr["shallow_stress_bench_latest"] = "reports/ollama_shallow_router_bench_stress_v1_latest.json"
    ptr["phase11g_chain_latest"] = "reports/logos_graphrag_phase11g_shallow_stress_chain_v1_latest.json"
    ptr["phase11i_chain_latest"] = "reports/logos_graphrag_phase11i_shallow_modelfile_tune_chain_v1_latest.json"
    ptr["sidecar_ablation_v3_latest"] = "reports/universal_root_sidecar_ablation_v3_latest.json"
    ptr["phase11k_chain_latest"] = "reports/logos_graphrag_phase11k_sidecar_ablation_v3_chain_v1_latest.json"
    ptr["phase11l_chain_latest"] = "reports/logos_graphrag_phase11l_closure_refresh_chain_v1_latest.json"
    ptr["phase11m_chain_latest"] = "reports/logos_graphrag_phase11m_research_impl_bridge_chain_v1_latest.json"
    ptr["universal_root_research_impl_bridge"] = "docs/final/artifacts/universal_root_research_impl_bridge_v1_latest.json"
    ptr["shallow_router_modelfile"] = "docs/final/artifacts/ollama_mkm_shallow_router_modelfile_v1.txt"
    ptr["comp_atom02_latest"] = (
        "reports/constitution/btrack_pilot/comp_atom02_lexicon_must_keep_analysis_v1.json"
    )
    ptr["phase11p_chain_latest"] = "reports/logos_graphrag_phase11p_compress_layerc_gate_chain_v1_latest.json"
    ptr["phase11q_chain_latest"] = "reports/logos_graphrag_phase11q_compress_parity_chain_v1_latest.json"
    ptr["phase11r_chain_latest"] = "reports/logos_graphrag_phase11r_cost_deepnsm_stub_chain_v1_latest.json"
    ptr["phase11s_chain_latest"] = "reports/logos_graphrag_phase11s_evidence_nl_sync_chain_v1_latest.json"
    ptr["phase11t_chain_latest"] = "reports/logos_graphrag_phase11t_cost_deep_bench_chain_v1_latest.json"
    ptr["phase11u_chain_latest"] = "reports/logos_graphrag_phase11u_deepnsm_hf_ollama_chain_v1_latest.json"
    ptr["deepnsm_hf_ollama_chain_latest"] = "reports/deepnsm_hf_explication_ollama_chain_v1_latest.json"
    ptr["phase12_chain_latest"] = "reports/logos_graphrag_phase12_live_public_chain_v1_latest.json"
    ptr["phase13_chain_latest"] = "reports/logos_graphrag_phase13_deepnsm_hf_ollama_chain_v1_latest.json"
    ptr["phase14_chain_latest"] = "reports/logos_graphrag_phase14_deepnsm_hf_ollama_500_chain_v1_latest.json"
    ptr["deepnsm_hf_ollama_500_chain_latest"] = "reports/deepnsm_hf_explication_ollama_500_chain_v1_latest.json"
    ptr["deepnsm_hf_ollama_500_sidecar"] = "docs/final/artifacts/deepnsm_hf_explication_ollama_500_v1.jsonl"
    ptr["stub_vs_ollama_500_ab_latest"] = "reports/deepnsm_hf_stub_vs_ollama_500_ab_v1_latest.json"
    ptr["deepnsm_hf_ollama_chain_latest"] = "reports/deepnsm_hf_explication_ollama_chain_v1_latest.json"
    ptr["deepnsm_hf_ollama_sidecar"] = "docs/final/artifacts/deepnsm_hf_explication_ollama_v1.jsonl"
    ptr["phase12_live_bundle_latest"] = "reports/logos_phase12_live_bundle_v1_latest.json"
    ptr["showroom_trust_viz_smoke_latest"] = "reports/showroom_trust_viz_public_chain_smoke_latest.json"
    ptr["layer_stack_closure"] = "docs/final/artifacts/universal_root_layer_stack_closure_v1_latest.json"
    ptr["cost_deep_bench_latest"] = "reports/ollama_shallow_cost_deep_bench_v1_latest.json"
    ptr["shallow_gap_golden16_latest"] = "reports/ollama_shallow_routing_oracle_gap_golden16_v1_latest.json"
    ptr["deepnsm_hf_explication_chain_latest"] = "reports/deepnsm_hf_explication_chain_v1_latest.json"
    ptr["deepnsm_hf_ab_stub_latest"] = "reports/deepnsm_hf_ab_research_stub_v1_latest.json"
    ptr["topology_crosswalk_latest"] = "reports/universal_root_topology_crosswalk_v1_latest.json"
    ptr["topology_crosswalk_gate_latest"] = "reports/universal_root_topology_crosswalk_gate_v1_latest.json"
    ptr["phase16_chain_latest"] = "reports/logos_graphrag_phase16_topology_crosswalk_chain_v1_latest.json"
    ptr["phase17_chain_latest"] = "reports/logos_graphrag_phase17_closure_observability_chain_v1_latest.json"
    ptr["wall_divergence_exception_cards"] = "docs/final/artifacts/UNIVERSAL_ROOT_WALL_DIVERGENCE_EXCEPTION_CARDS_V1.json"
    ptr["topology_crosswalk_spec"] = "docs/final/artifacts/UNIVERSAL_ROOT_TOPOLOGY_CROSSWALK_SPEC_V1.json"
    out["artifact_pointers"] = ptr
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if not args.spec.is_file():
        print(json.dumps({"ok": False, "error": "missing_spec"}))
        return 2
    spec = _read(args.spec)
    updated = refresh_baseline(spec)
    if args.dry_run:
        print(json.dumps({"ok": True, "dry_run": True, "phase": updated["baseline_observed"]["phase"]}))
        return 0
    args.spec.write_text(json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.spec)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
