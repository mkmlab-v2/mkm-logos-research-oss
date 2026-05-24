"""Bridge lines for cross-lens RAG + 4RAG sphere pointers."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.commander_telegram_rag_viz_bridge_v1 import (
    build_cross_lens_telegram_lines,
    build_sphere_rag_viz_telegram_lines,
)


def test_cross_lens_lines_from_fixture(tmp_path: Path) -> None:
    doc = {
        "schema": "cross_lens_rag_fusion_v1",
        "cross_lens_conflict_matrix": {
            "agreement_rate": 0.8,
            "majority_sign": "bull",
            "minority_lenses": ["logos"],
        },
        "signal_light": {"status": "GREEN"},
        "final_gate_panel": {"veto_force_hold": False},
        "lens_snapshots": [
            {"lens_id": "logos", "available": True, "direction_sign": "bear", "confidence": 0.2},
        ],
    }
    path = tmp_path / "docs/final/artifacts/cross_lens_rag_fusion_latest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc), encoding="utf-8")
    lines = build_cross_lens_telegram_lines(tmp_path)
    assert any("합의" in ln for ln in lines)
    assert any("logos" in ln for ln in lines)


def test_sphere_lines_from_fixture(tmp_path: Path) -> None:
    doc = {
        "schema": "three_lens_sphere_envelope_v1",
        "rag_layers_resolved": {
            "lexical": [{"present": True}, {"present": False}],
            "semantic": [{"present": True}],
            "temporal": [],
            "constitutional": [{"present": True}],
        },
        "graph_viz": {"node_count_display": 42, "graph_slice_path": "docs/x.json"},
        "hub_links": {"jemaai_meaning_topology_graph": "https://example.com/topo"},
        "final_action": "REDUCE",
    }
    path = tmp_path / "docs/final/artifacts/three_lens_sphere_envelope_v1_latest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc), encoding="utf-8")
    lines = build_sphere_rag_viz_telegram_lines(tmp_path)
    assert any("4RAG" in ln for ln in lines)
    assert any("example.com" in ln for ln in lines)
