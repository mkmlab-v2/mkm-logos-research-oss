"""Phase 3: magic_orb graph bloom edge integrity_tier annotation."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/build_magic_orb_graph_bloom_v1.py"
HERO = ROOT / "docs/final/artifacts/magic_orb_hero_slices_v1_latest.json"
INSIGHT = ROOT / "docs/final/artifacts/magic_orb_question_insight_v1_latest.json"


def _load_builder():
    spec = importlib.util.spec_from_file_location("build_magic_orb_graph_bloom_v1", BUILDER)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_annotate_integrity_tiers_on_edge_types():
    mod = _load_builder()
    doc = {
        "schema": "magic_orb_graph_bloom_v1",
        "nodes": [{"id": "a", "label": "a", "kind": "verse"}],
        "edges": [
            {"src": "a", "dst": "b", "edge_type": "cross_lens_confirm"},
            {"src": "b", "dst": "c", "edge_type": "parallel"},
            {"src": "c", "dst": "d", "edge_type": "timeline_anchor"},
            {"src": "d", "dst": "e", "edge_type": "unknown_kind"},
        ],
    }
    out = mod.annotate_bloom_edge_integrity(doc)
    tiers = {e["edge_type"]: e["integrity_tier"] for e in out["edges"]}
    assert tiers["cross_lens_confirm"] == "confirmed"
    assert tiers["parallel"] == "parallel_evidence"
    assert tiers["timeline_anchor"] == "chrono_anchor"
    assert tiers["unknown_kind"] == "observation"
    assert out["edge_integrity_policy"]["research_only"] is True


def test_hero_passion_slice_has_parallel_integrity():
    if not HERO.is_file():
        return
    bundle = json.loads(HERO.read_text(encoding="utf-8-sig"))
    passion = next(s for s in bundle["slices"] if s["slice_id"] == "SYNOPTIC_PASSION_WEEK_v1")
    edges = passion["graph_bloom"]["edges"]
    assert any(e.get("edge_type") == "parallel" for e in edges)
    mod = _load_builder()
    annotated = mod.annotate_bloom_edge_integrity(json.loads(json.dumps(passion["graph_bloom"])))
    parallel = next(e for e in annotated["edges"] if e.get("edge_type") == "parallel")
    assert parallel.get("integrity_tier") == "parallel_evidence"


def test_insight_bloom_has_edge_integrity_policy():
    if not INSIGHT.is_file():
        return
    doc = json.loads(INSIGHT.read_text(encoding="utf-8-sig"))
    bloom = doc.get("graph_bloom") or {}
    if not bloom.get("edges"):
        return
    mod = _load_builder()
    mod.annotate_bloom_edge_integrity(bloom)
    assert bloom.get("edge_integrity_policy", {}).get("schema") == "magic_orb_graph_bloom_edge_integrity_v1"
    assert all("integrity_tier" in e for e in bloom["edges"])
