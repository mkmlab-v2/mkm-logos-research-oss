#!/usr/bin/env python3
"""Distill successful Logos+B2B verifier patterns into retrieval_rules SSOT (logic only)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_reasoning_pattern_registry_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return None


def build() -> dict[str, Any]:
    b2b_verifier = _load(ROOT / "reports/logos_b2b_proposal_goal_verifier_v1_latest.json")
    master = _load(ROOT / "docs/final/artifacts/logos_b2b_proposal_master_summary_v1_latest.json")
    john_lock = _load(
        ROOT / "docs/final/artifacts/logos_deep_research_distill_john_1_logos_citation_lock_latest.json"
    )
    macula_ingest = _load(ROOT / "reports/logos_macula_themed_ingest_v1_latest.json")
    graphrag_audit = _load(ROOT / "reports/logos_themed_graphrag_seed_retrieval_v1_latest.json")
    phase_h = _load(ROOT / "reports/logos_track_b_phase_h_v1_latest.json")
    xref_manifest = _load(ROOT / "reports/logos_themed_xref_subgraph_v1_latest.json")
    bridge = _load(ROOT / "reports/logos_cross_theme_invariant_bridge_v1_latest.json")
    dialectical = _load(ROOT / "reports/logos_dialectical_insight_layers_v1_latest.json")
    multi_insight = _load(ROOT / "reports/logos_multi_insight_synthesis_v1_latest.json")
    phase_o = _load(ROOT / "reports/logos_track_b_phase_o_v1_latest.json")
    psi = _load(ROOT / "reports/logos_psi_logic_extraction_v1_latest.json")
    path_gate = _load(ROOT / "reports/logos_path_verification_gate_v1_latest.json")

    patterns: list[dict[str, Any]] = [
        {
            "pattern_id": "layered_context_v1",
            "source": "john_1_logos_citation_lock",
            "layers": ["field", "evidence_anchors", "narrative", "operator_posture", "conflict_resolver"],
            "rules": [
                "every_claim_requires_clause_ref_or_verse_id",
                "orphan_citation_veto",
                "hypo_tag_required",
            ],
            "pedagogical_only": True,
        },
        {
            "pattern_id": "goal_verifier_backtrack_v1",
            "source": "logos_b2b_proposal_goal_verifier",
            "rules": [
                "barrier_audit_must_pass",
                "forbidden_terms_negation_aware",
                "track_a_bridge_forbidden",
            ],
            "verdict": (b2b_verifier or {}).get("verdict"),
        },
        {
            "pattern_id": "macula_themed_ingest_v1",
            "source": "ingest_logos_macula_themed_lemma_edges_v1",
            "rules": [
                "theme_scoped_verse_ids_only",
                "macula_tsv_when_available_else_distill_proxy",
                "merge_dedupe_by_src_dst_type",
            ],
            "edges_built": (macula_ingest or {}).get("edges_built"),
        },
        {
            "pattern_id": "themed_anchor_graphrag_wiring_v1",
            "source": "build_logos_themed_anchor_concept_bridge_v1",
            "rules": [
                "distill_citation_lock_anchors_to_concept_bridge_paths",
                "themed_registry_overlay_for_graphrag_router",
                "organic_seed_recall_audited_before_xref",
            ],
            "seed_hits_organic": ((graphrag_audit or {}).get("summary") or {}).get("seed_hits_organic"),
            "phase_h_ok": (phase_h or {}).get("ok"),
        },
        {
            "pattern_id": "openbible_xref_1hop_v1",
            "source": "build_logos_themed_xref_subgraph_v1",
            "rules": [
                "theme_anchor_scoped_openbible_scan",
                "bidirectional_xref_enrichment_on_router",
            ],
            "xref_edges": (xref_manifest or {}).get("total_edges"),
        },
    ]

    if bridge:
        patterns.append(
            {
                "pattern_id": "cross_theme_invariant_bridge_v1",
                "source": "build_logos_cross_theme_invariant_bridge_v1",
                "rules": ["xref_hub_bridge", "semantic_invariant_tags", "dan_john_parallel_only"],
                "shared_hubs": (bridge.get("summary") or {}).get("shared_hub_count"),
            }
        )
    if dialectical:
        patterns.append(
            {
                "pattern_id": "dialectical_insight_layers_v1",
                "source": "build_logos_dialectical_insight_layers_v1",
                "rules": ["thesis_antithesis_synthesis", "verse_id_per_segment", "orphan_citation_veto"],
                "insight_units": (dialectical.get("summary") or {}).get("insight_units"),
            }
        )
    if multi_insight:
        patterns.append(
            {
                "pattern_id": "multi_insight_synthesis_v1",
                "source": "run_logos_llm_multi_insight_synthesis_v1",
                "rules": ["paper_guided_insight_units", "bible_ai_refs_applied"],
                "unit_count": (multi_insight.get("summary") or {}).get("unit_count"),
            }
        )
    if psi:
        patterns.append(
            {
                "pattern_id": "psi_logic_extraction_v1",
                "source": "build_logos_psi_logic_extraction_v1",
                "rules": ["theological_token_filter", "logic_layer_only", "content_layer_isolated"],
                "logic_nodes": len((psi.get("logic_graph") or {}).get("nodes") or []),
            }
        )
    if phase_o:
        patterns.append(
            {
                "pattern_id": "phase_o_simplicial_b2b_chain_v1",
                "source": "run_logos_track_b_phase_o_v1",
                "rules": [
                    "simplicial_dependency_ledger",
                    "b2b_alpha_beta_chain",
                    "path_verification_v_score",
                    "hitl_required",
                ],
                "ledger_records": phase_o.get("ledger_records"),
                "path_gate_pass": phase_o.get("path_verification_gate_pass"),
            }
        )
    if path_gate:
        patterns.append(
            {
                "pattern_id": "path_verification_gate_v1",
                "source": "build_logos_path_verification_gate_v1",
                "rules": ["verse_adjacency_max_hops", "v_score_per_unit"],
                "pass_rate": (path_gate.get("summary") or {}).get("pass_rate"),
            }
        )

    retrieval_rules = {
        "bm25_first": True,
        "semantic_gate_on_low_confidence": True,
        "graph_hop_max": 2,
        "citation_lock_before_narrative": True,
        "master_summary_promotion_requires_verifier_ok": True,
        "themed_graphrag_registry": "docs/final/artifacts/logos_concept_bridge_registry_themed_v1_latest.json",
    }

    return {
        "schema": "logos_reasoning_pattern_registry_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "content_domain_separation": True,
        "patterns": patterns,
        "retrieval_rules": retrieval_rules,
        "evidence": {
            "b2b_verifier_ok": (b2b_verifier or {}).get("ok"),
            "master_summary_promoted": (master or {}).get("promoted"),
            "john_citation_locked": ((john_lock or {}).get("citation_lock") or {}).get("locked_count"),
            "macula_edges_built": (macula_ingest or {}).get("edges_built"),
            "graphrag_seed_hits_organic": ((graphrag_audit or {}).get("summary") or {}).get("seed_hits_organic"),
            "xref_edges": (xref_manifest or {}).get("total_edges"),
        },
        "reproduce": "py scripts/build_logos_reasoning_pattern_registry_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "patterns": len(doc["patterns"]), "out": str(args.out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
