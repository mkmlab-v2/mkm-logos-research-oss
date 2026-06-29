"""Phase 2: router empty paths → seed_chain / hero slice bloom must not be sparse."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/build_magic_orb_graph_bloom_v1.py"
ROUTER = ROOT / "reports/question_logos_subgraph_router_sidecar_v1_latest.json"
INSIGHT = ROOT / "docs/final/artifacts/magic_orb_question_insight_v1_latest.json"
HERO = ROOT / "docs/final/artifacts/magic_orb_hero_slices_v1_latest.json"


def _load_builder():
    spec = importlib.util.spec_from_file_location("build_magic_orb_graph_bloom_v1", BUILDER)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_seed_chain_fallback_on_empty_paths():
    mod = _load_builder()
    router = {
        "schema": "logos_subgraph_graphrag_router_v1",
        "query": "Dan.2 cluster observational",
        "paths": [],
        "verse_ids": [],
        "seed_chain_verse_sample": ["Dan.2.10", "Dan.2.11", "Dan.2.12", "Dan.2.13"],
    }
    doc = mod.build_bloom(query=router["query"], router=router)
    assert doc["stats"]["node_count"] >= 5
    assert doc["stats"]["edge_count"] >= 4
    kinds = {n["kind"] for n in doc["nodes"]}
    assert "query" in kinds and "verse" in kinds


def test_live_router_sidecar_not_sparse_when_seed_chain_present():
    if not ROUTER.is_file() or not HERO.is_file():
        return
    mod = _load_builder()
    router = json.loads(ROUTER.read_text(encoding="utf-8-sig"))
    if not router.get("seed_chain_verse_sample"):
        return
    doc = mod.build_bloom(query="위기 가운데 언약의 안정과 신실", router=router)
    verse_nodes = sum(1 for n in doc["nodes"] if n.get("kind") == "verse")
    assert verse_nodes >= 4, f"expected seed_chain or hero fallback, got {verse_nodes} verses"
    assert doc["stats"]["edge_count"] >= 3


def test_insight_graph_bloom_not_query_only():
    if not INSIGHT.is_file():
        return
    doc = json.loads(INSIGHT.read_text(encoding="utf-8-sig"))
    bloom = doc.get("graph_bloom") or {}
    nodes = bloom.get("nodes") or []
    edges = bloom.get("edges") or []
    verse_nodes = sum(1 for n in nodes if n.get("kind") == "verse")
    assert verse_nodes >= 4, f"insight graph_bloom too sparse: {len(nodes)} nodes, {len(edges)} edges"
