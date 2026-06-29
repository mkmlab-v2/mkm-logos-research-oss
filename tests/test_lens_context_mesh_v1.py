"""Lens context mesh hop index + hub schema tests."""
from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "docs/final/schemas"
ARTIFACTS = ROOT / "docs/final/artifacts"
SLICE = ARTIFACTS / "showroom_meaning_topology_graph_slice_v1_latest.json"

from scripts.lens_context_mesh_v1 import (  # noqa: E402
    bfs_node_ids,
    build_hop_index_from_slice,
    build_hub_logos,
    filter_slice_to_nodes,
    load_json,
)


def _schema(name: str) -> dict:
    return json.loads((SCHEMAS / name).read_text(encoding="utf-8-sig"))


@pytest.fixture(scope="module")
def slice_doc() -> dict:
    assert SLICE.is_file(), f"missing slice fixture: {SLICE}"
    return load_json(SLICE)


def test_build_hop_index_matches_schema(slice_doc: dict) -> None:
    doc = build_hop_index_from_slice(slice_doc, source_slice_path="docs/final/artifacts/showroom_meaning_topology_graph_slice_v1_latest.json")
    jsonschema.validate(doc, _schema("lens_context_mesh_hop_index_v1.schema.json"))
    slice_ids = {str(n.get("id")) for n in slice_doc.get("nodes") or [] if n.get("id")}
    hop_ids = set(doc["nodes"].keys())
    assert slice_ids.issubset(hop_ids)
    assert doc["stats"]["node_count"] == len(hop_ids)
    assert doc["stats"]["undirected_edge_pairs"] > 0


def test_bfs_depth_expansion(slice_doc: dict) -> None:
    hop = build_hop_index_from_slice(slice_doc)
    nodes = hop["nodes"]
    seed = next(iter(nodes))
    d1 = bfs_node_ids(hop, [seed], depth=1, max_nodes=100)
    d2 = bfs_node_ids(hop, [seed], depth=2, max_nodes=100)
    assert len(d1) >= 1
    assert len(d2) >= len(d1)


def test_bfs_respects_max_nodes(slice_doc: dict) -> None:
    hop = build_hop_index_from_slice(slice_doc)
    seed = next(iter(hop["nodes"]))
    capped = bfs_node_ids(hop, [seed], depth=4, max_nodes=5)
    assert len(capped) <= 5


def test_filter_slice_to_nodes(slice_doc: dict) -> None:
    hop = build_hop_index_from_slice(slice_doc)
    seed = next(iter(hop["nodes"]))
    visible = set(bfs_node_ids(hop, [seed], depth=2, max_nodes=20))
    filtered = filter_slice_to_nodes(slice_doc, visible)
    filtered_ids = {str(n.get("id")) for n in filtered["nodes"]}
    assert filtered_ids.issubset(visible)
    assert filtered_ids.issubset({str(n.get("id")) for n in slice_doc.get("nodes") or []})
    for e in filtered["edges"]:
        assert e["src"] in filtered_ids and e["dst"] in filtered_ids


def test_hub_manifest_schema(slice_doc: dict, tmp_path: Path) -> None:
    hop_path = tmp_path / "hop.json"
    hop = build_hop_index_from_slice(slice_doc)
    hop_path.write_text(json.dumps(hop), encoding="utf-8")
    hub = build_hub_logos(slice_path=SLICE, hop_index_path=hop_path)
    jsonschema.validate(hub, _schema("lens_context_mesh_hub_v1.schema.json"))
    assert hub["send_gate"] == "HOLD"
    assert hub["ui_contract"]["default_depth"] == 2
