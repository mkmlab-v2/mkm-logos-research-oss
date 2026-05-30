"""Smoke: build_magic_orb_question_insight_payload_v1 embeds graph_bloom."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/build_magic_orb_question_insight_payload_v1.py"
ROUTER = ROOT / "reports/question_logos_subgraph_router_sidecar_v1_latest.json"
BUNDLE = ROOT / "docs/final/artifacts/semantic_rag_bridge_insight_bundle_v1_latest.json"


def _load_builder():
    spec = importlib.util.spec_from_file_location("build_magic_orb_question_insight_payload_v1", BUILDER)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_payload_embeds_graph_bloom():
    if not ROUTER.is_file():
        return
    mod = _load_builder()
    router = json.loads(ROUTER.read_text(encoding="utf-8"))
    bundle = json.loads(BUNDLE.read_text(encoding="utf-8")) if BUNDLE.is_file() else {"schema": "semantic_rag_bridge_insight_bundle_v1", "rag_evidence": []}
    bloom_mod_path = ROOT / "scripts/build_magic_orb_graph_bloom_v1.py"
    bspec = importlib.util.spec_from_file_location("build_magic_orb_graph_bloom_v1", bloom_mod_path)
    bmod = importlib.util.module_from_spec(bspec)
    bspec.loader.exec_module(bmod)
    bloom = bmod.build_bloom(query=router["query"], router=router)
    payload = mod.build_payload(
        query=router["query"],
        query_id="q01",
        bundle=bundle,
        chain=None,
        router=router,
        graph_bloom=bloom,
    )
    assert payload["schema"] == "magic_orb_question_insight_v1"
    assert payload["graph_bloom"]["schema"] == "magic_orb_graph_bloom_v1"
    assert len(payload["graph_bloom"]["nodes"]) >= 2


def test_insight_builder_help():
    r = subprocess.run(
        [sys.executable, str(BUILDER), "--help"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0


def test_rag_fusion_prefers_ranked_router_over_stale_bundle():
    mod = _load_builder()
    stale_bundle = {
        "schema": "semantic_rag_bridge_insight_bundle_v1",
        "rag_evidence": [
            {
                "source_id": "logos_subgraph:path_stale:docs/final/artifacts/stale.json",
                "snippet": "stale",
                "confidence_band": "B",
            }
        ],
    }
    router = {
        "bridges_matched": 2,
        "paths": [
            {"path_id": "low", "bridge_artifact": "a.json", "steps": [], "note_ko": "low", "match_score": 1},
            {"path_id": "high", "bridge_artifact": "b.json", "steps": [], "note_ko": "high", "match_score": 9},
            {"path_id": "mid", "bridge_artifact": "c.json", "steps": [], "note_ko": "mid", "match_score": 5},
        ],
        "verse_ids": ["v1", "v2"],
    }
    payload = mod.build_payload(
        query="stress query",
        query_id="q_test",
        bundle=stale_bundle,
        chain=None,
        router=router,
        graph_bloom=None,
        caps={"subgraph_paths": 2, "subgraph_verses": 1, "rag_evidence": 24},
    )
    rag = payload["rag_evidence"]
    assert len(rag) == 3
    assert rag[0]["source_id"].startswith("logos_subgraph:high:")
    assert rag[1]["source_id"].startswith("logos_subgraph:mid:")
    assert payload["rag_fusion"]["router_paths_included"] == 2
    assert "logos_subgraph:path_stale" not in {r["source_id"] for r in rag}
