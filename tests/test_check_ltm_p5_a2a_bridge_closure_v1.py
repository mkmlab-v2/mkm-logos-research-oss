"""Tests for LTM P5 A2A bridge closure ([HYPO] / B-track · RQ-019)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from check_ltm_p5_a2a_bridge_closure_v1 import A2A_BRIDGE_IDS, WALL  # noqa: E402
from mkm_long_term_memory_graph_lib_v1 import CONCEPT_BY_ID  # noqa: E402
from build_ltm_a2a_bridge_map_v1 import build_map  # noqa: E402


def test_a2a_bridge_concepts_present() -> None:
    for cid in A2A_BRIDGE_IDS:
        assert cid in CONCEPT_BY_ID
    assert len(CONCEPT_BY_ID) >= 59


def test_wall_doc_contract() -> None:
    wall = json.loads(WALL.read_text(encoding="utf-8-sig"))
    assert wall["schema"] == "ltm_a2a_bridge_wall_v1"
    assert "live_trading_enable" in wall["forbidden_auto_merge"]
    assert wall.get("research_only") is True


def test_route_a2a_bridge_subgraph(tmp_path: Path) -> None:
    from mkm_long_term_memory_graph_lib_v1 import build_graph_document, route_concepts_by_query

    from tests.test_mkm_long_term_memory_graph_v1 import _write_min_ssot

    _write_min_ssot(tmp_path)
    doc = build_graph_document(tmp_path)
    routed = route_concepts_by_query(doc, "a2a inter agent ltm wire encoding rq019 track wall")
    ids = {cid for cid, _ in routed}
    assert ids.intersection(A2A_BRIDGE_IDS)


def test_bridge_map_schema_when_artifacts_present() -> None:
    graph_path = ROOT / "storage/meta/mkm_long_term_memory_graph_v1.json"
    index_path = ROOT / "storage/meta/mkm_ops_memory_index_v1.json"
    if not graph_path.is_file() or not index_path.is_file():
        return
    doc = build_map(ROOT)
    assert doc["schema"] == "ltm_a2a_bridge_map_v1"
    assert doc["ltm_overlay_count"] >= 1
    assert len(doc["a2a_bridge_concept_ids"]) >= 3
