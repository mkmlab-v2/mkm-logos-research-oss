"""B-track wire gloss lexicon alignment helpers."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_wire_atom_ids_lexicon_filtered_drops_verse_nodes() -> None:
    from scripts.mkm_graph_wire_bridge_influence_v1 import (
        wire_atom_ids_lexicon_filtered,
        wire_atom_ids_merged,
    )

    merged = wire_atom_ids_merged(anchor_max=12)
    filtered = wire_atom_ids_lexicon_filtered(anchor_max=12)
    assert len(filtered) <= len(merged)
    assert all("Dan.2." not in aid for aid in filtered)
    assert len(filtered) >= 12


def test_surface_wire_gloss_per_case_smoke() -> None:
    from scripts.logos_verse_surface_reconstruct_hypo_v1 import run_batch_wire_gloss
    from scripts.mkm_graph_wire_bridge_influence_v1 import wire_atom_ids_lexicon_filtered

    lane = ROOT / "reports/golden_40_logos_verse_compression_lane_stride120_v1.json"
    lex = ROOT / "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41658_rows_latest.json"
    cases = json.loads(lane.read_text(encoding="utf-8")).get("compression_cases") or []
    sample = cases[:6]
    wire_ids = wire_atom_ids_lexicon_filtered(anchor_max=12, lexicon_path=lex)
    doc = run_batch_wire_gloss(sample, lex, wire_atom_ids=wire_ids, influence_map={})
    assert doc["case_count"] == 6
    assert doc["wire_gloss_delta_pp_vs_lexicon"] == 0.0


def test_rebuild_lexicon_aligned_poc_strategy() -> None:
    from scripts.rebuild_logos_wire_poc_lexicon_aligned_v1 import rebuild

    poc = ROOT / "docs/final/artifacts/logos_graph_wire_rag_poc_v1_latest.json"
    lex = ROOT / "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41658_rows_latest.json"
    doc = rebuild(poc, lexicon_path=lex, strategy="anchor07_primary")
    ids = doc["graph_rag"]["reasoning_path_node_ids"]
    assert len(ids) >= 12
    assert "aramaic::Dan.2.10" not in ids
    assert doc["alignment"]["dropped_unknown_to_lexicon"]
