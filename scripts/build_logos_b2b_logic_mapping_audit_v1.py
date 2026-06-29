#!/usr/bin/env python3
"""B2B logic mapping audit — structure transplant only, separate from goal verifier [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_DEFAULT = ROOT / "reports/logos_b2b_logic_mapping_audit_v1_latest.json"

STRUCTURE_DIMENSIONS = (
    ("citation_lock", "every_claim_requires_verse_or_clause_ref"),
    ("goal_verifier_backtrack", "barrier_audit_and_forbidden_terms"),
    ("graph_path_evidence", "query_specific_evidence_graph"),
    ("dialectical_layers", "thesis_antithesis_synthesis_with_citation"),
    ("cross_theme_invariant", "shared_hub_or_semantic_tag_bridge"),
    ("psi_logic_morphism", "content_to_logic_layer_transplant"),
    ("simplicial_dependency_ledger", "2_simplex_coherence_and_dependency_path"),
)


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
    verifier = _load(ROOT / "reports/logos_b2b_proposal_goal_verifier_v1_latest.json")
    dialectical = _load(ROOT / "reports/logos_dialectical_insight_layers_v1_latest.json")
    bridge = _load(ROOT / "reports/logos_cross_theme_invariant_bridge_v1_latest.json")
    gaps = _load(ROOT / "reports/logos_insight_gap_audit_v1_latest.json")
    closure = _load(ROOT / "reports/logos_track_b_integration_closure_v1_latest.json")
    psi = _load(ROOT / "reports/logos_psi_logic_extraction_v1_latest.json")
    phase_o = _load(ROOT / "reports/logos_track_b_phase_o_v1_latest.json")
    simplicial = _load(ROOT / "reports/logos_causal_simplicial_snapshot_v1_latest.json")

    mappings: list[dict[str, Any]] = []
    for dim_id, rule in STRUCTURE_DIMENSIONS:
        ok = False
        note = ""
        if dim_id == "citation_lock":
            ok = (closure or {}).get("gates", {}).get("llm_citation_valid_dan") and (closure or {}).get("gates", {}).get("llm_citation_valid_john")
            note = "citation_lock on both themes"
        elif dim_id == "goal_verifier_backtrack":
            ok = (verifier or {}).get("ok") is True
            note = str((verifier or {}).get("verdict"))
        elif dim_id == "graph_path_evidence":
            ok = (closure or {}).get("gates", {}).get("graphrag_organic_42_42") is True
            note = str((closure or {}).get("metrics", {}).get("graphrag_seed_organic"))
        elif dim_id == "dialectical_layers":
            ok = int(((dialectical or {}).get("summary") or {}).get("insight_units") or 0) >= 6
            note = "6 dialectical units (2 themes x 3 layers)"
        elif dim_id == "cross_theme_invariant":
            sm = (bridge or {}).get("summary") or {}
            ok = (
                int(sm.get("shared_hub_count") or 0) > 0
                or int(sm.get("two_hop_bridges") or 0) > 0
                or int(sm.get("semantic_invariant_tags") or 0) > 0
                or int(sm.get("direct_cross_edges") or 0) > 0
            )
            note = (
                f"hubs={sm.get('shared_hub_count')} two_hop={sm.get('two_hop_bridges')} "
                f"invariants={sm.get('semantic_invariant_tags')}"
            )
        elif dim_id == "psi_logic_morphism":
            ok = (psi or {}).get("structure_transplant_only") is True and len(
                ((psi or {}).get("logic_graph") or {}).get("nodes") or []
            ) >= 4
            note = f"logic_nodes={len(((psi or {}).get('logic_graph') or {}).get('nodes') or [])}"
        elif dim_id == "simplicial_dependency_ledger":
            ok = int((phase_o or {}).get("ledger_records") or 0) >= 2 or int(
                (simplicial or {}).get("hub_triangles_seeded") or 0
            ) > 0
            note = (
                f"ledger_records={(phase_o or {}).get('ledger_records')} "
                f"triangles={(simplicial or {}).get('hub_triangles_seeded')}"
            )

        mappings.append(
            {
                "dimension_id": dim_id,
                "b2b_structure_rule": rule,
                "mapping_possible": bool(ok),
                "note": note,
                "theology_to_sales_forbidden": True,
            }
        )

    pass_count = sum(1 for m in mappings if m["mapping_possible"])
    gap_count = sum(len((t or {}).get("graph_hop_gaps") or []) for t in ((gaps or {}).get("themes") or []))

    return {
        "schema": "logos_b2b_logic_mapping_audit_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "structure_transplant_only": True,
        "master_summary_auto_promote": False,
        "question": "Can insight ENGINE STRUCTURE map to B2B verifier patterns (not theology content)?",
        "mappings": mappings,
        "summary": {
            "mapping_pass": f"{pass_count}/{len(STRUCTURE_DIMENSIONS)}",
            "hop_gaps_observed": gap_count,
            "verdict": "STRUCTURE_MAP_OK" if pass_count >= 5 else "STRUCTURE_MAP_PARTIAL",
        },
        "reproduce": "py scripts/build_logos_b2b_logic_mapping_audit_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ok = doc["summary"]["verdict"] == "STRUCTURE_MAP_OK"
    print(json.dumps({"ok": ok, "verdict": doc["summary"]["verdict"], "out": str(args.out)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
