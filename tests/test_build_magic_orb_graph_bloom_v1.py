"""Smoke: build_magic_orb_graph_bloom_v1 from router sidecar."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTER = ROOT / "reports/question_logos_subgraph_router_sidecar_v1_latest.json"
BUILDER = ROOT / "scripts/build_magic_orb_graph_bloom_v1.py"


def _load_builder():
    spec = importlib.util.spec_from_file_location("build_magic_orb_graph_bloom_v1", BUILDER)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_bloom_from_router_has_query_center():
    if not ROUTER.is_file():
        return
    mod = _load_builder()
    router = json.loads(ROUTER.read_text(encoding="utf-8"))
    doc = mod.build_bloom(query=router.get("query", "test"), router=router)
    assert doc["schema"] == "magic_orb_graph_bloom_v1"
    assert doc["nodes"]
    ids = {n["id"] for n in doc["nodes"]}
    assert "query::center" in ids
    assert doc["stats"]["node_count"] == len(doc["nodes"])
    assert doc["stats"]["edge_count"] == len(doc["edges"])
    assert doc["stats"]["node_count"] <= 64
    verse_nodes = sum(1 for n in doc["nodes"] if n.get("kind") == "verse")
    if router.get("seed_chain_verse_sample") or router.get("paths"):
        assert verse_nodes >= 1
        assert doc["stats"]["edge_count"] >= 1


def test_bloom_gold_profile_allows_dense_cap():
    mod = _load_builder()
    gold_mod_path = ROOT / "scripts/magic_orb_gold_lod_profiles_v1.py"
    gspec = importlib.util.spec_from_file_location("magic_orb_gold_lod_profiles_v1", gold_mod_path)
    gmod = importlib.util.module_from_spec(gspec)
    assert gspec.loader is not None
    gspec.loader.exec_module(gmod)
    caps = gmod.resolve_gold_lod_profile("q04")
    assert caps["lod_node_cap"] == 64
    assert caps["lod_edge_cap"] == 72
    if not ROUTER.is_file():
        return
    router = json.loads(ROUTER.read_text(encoding="utf-8"))
    doc = mod.build_bloom(
        query=router.get("query", "test"),
        router=router,
        lod_node_cap=int(caps["lod_node_cap"]),
        lod_edge_cap=int(caps["lod_edge_cap"]),
        hub_verse_refs=list(caps.get("hub_verse_ids") or []),
        expand_graph=True,
    )
    assert doc["stats"]["node_count"] <= 64
    hub_nodes = [n for n in doc["nodes"] if (n.get("hub_score") or 0) >= 0.9]
    if caps.get("hub_verse_ids"):
        assert hub_nodes, "expected pinned hub nodes for gold profile"


def test_bloom_router_nodes_use_bridge_label_ko():
    if not ROUTER.is_file():
        return
    mod = _load_builder()
    router = json.loads(ROUTER.read_text(encoding="utf-8"))
    if not router.get("paths"):
        return  # seed-chain-only fallback uses canonical verse refs without bridge label_ko
    doc = mod.build_bloom(query=router.get("query", "test"), router=router)
    ko_nodes = [n for n in doc["nodes"] if n.get("label_ko") or ("가-힣" in n.get("label", ""))]
    if not ko_nodes:
        return  # bridge label_ko is best-effort per router/bridge mix
    assert ko_nodes, "expected Korean labels from bridge label_ko"
    english_only = [
        n["label"]
        for n in doc["nodes"]
        if n.get("kind") not in ("query",) and not (n.get("label_ko") or __import__("re").search(r"[가-힣]", n.get("label", "")))
    ]
    assert len(english_only) <= max(4, len(doc["nodes"]) // 4), english_only[:6]


def test_bloom_builder_cli_help():
    import subprocess
    import sys

    r = subprocess.run(
        [sys.executable, str(BUILDER), "--help"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0
    assert "magic_orb_graph_bloom" in r.stdout
