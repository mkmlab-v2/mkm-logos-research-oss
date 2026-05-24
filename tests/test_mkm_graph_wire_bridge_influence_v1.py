# @MKM12-METADATA
# Type: Logic
# Purpose: COMP-ATOM-05 graph wire influence map contract.

from __future__ import annotations

from scripts.mkm_graph_wire_bridge_influence_v1 import (
    build_case_graph_wire_influence_map,
    merge_wire_into_semantic_pointer,
    wire_atom_ids_from_anchor07,
    wire_atom_ids_merged,
    wire_influence_score,
)


def test_wire_influence_score_graph_hit() -> None:
    hi = wire_influence_score(expanded_node_count=5, anchor_terms=["babel", "exodus"])
    lo = wire_influence_score(expanded_node_count=0, anchor_terms=[])
    assert hi > lo
    assert hi >= 0.35


def test_build_case_map_bridge_boost() -> None:
    routes = [
        {
            "case_id": "c1",
            "expanded_node_count": 10,
            "anchor_terms": ["babel", "tower"],
        },
        {"case_id": "c2", "expanded_node_count": 0, "anchor_terms": []},
    ]
    m = build_case_graph_wire_influence_map(routes, wire_atom_ids=["aramaic::Dan.2.10"])
    assert m["c1"]["bridge_boost"] is True
    assert m["c2"]["bridge_boost"] is False
    assert "graph::babel" in m["c1"]["atom_id_sequence"]


def test_wire_atom_ids_anchor07_loads_when_file_present() -> None:
    ids = wire_atom_ids_from_anchor07(max_n=3)
    if not ids:
        return
    assert ids[0].startswith("hebrew::") or ids[0].startswith("greek::")


def test_wire_atom_ids_merged_dedupes() -> None:
    merged = wire_atom_ids_merged(anchor_max=4)
    assert len(merged) == len(set(merged))


def test_merge_wire_into_semantic_pointer() -> None:
    sp = {"schema": "semantic_pointer_v1", "case_id": "x"}
    out = merge_wire_into_semantic_pointer(
        sp,
        {"atom_id_sequence": ["a"], "wire_influence_score": 0.5, "bridge_boost": True, "graph_anchor_terms": []},
    )
    assert out["graph_wire_influence_v1"]["bridge_boost"] is True
