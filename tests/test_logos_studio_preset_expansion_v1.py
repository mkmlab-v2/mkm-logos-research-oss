"""Tests for Logos Studio preset expansion (BigSet + graph chapter roadmap)."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.merge_logos_studio_bigset_topic_presets_v1 import (
    BIGSET_TOPIC_SPECS,
    merge_bigset_presets,
)
from scripts.merge_logos_studio_graph_chapter_presets_v1 import merge_chapter_presets

ROOT = Path(__file__).resolve().parents[1]


def _load(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8-sig"))


def test_bigset_merge_adds_five_topics() -> None:
    presets = {"presets": [{"id": "p1", "prompt_ko": "x", "answer_ko": "y", "highlight_node_ids": []}]}
    conflict = _load("docs/final/artifacts/bigset_multi_topic_conflict_surface_v1_latest.json")
    graph = _load("docs/final/artifacts/showroom_meaning_topology_graph_slice_v1_latest.json")
    merged, added = merge_bigset_presets(presets, conflict, graph)
    ids = {p["id"] for p in merged["presets"]}
    assert added == len(BIGSET_TOPIC_SPECS)
    assert "bigset_topic_nephilim" in ids
    assert "bigset_topic_benei_haelohim" in ids
    neph = next(p for p in merged["presets"] if p["id"] == "bigset_topic_nephilim")
    assert neph.get("preset_kind") == "bigset_conflict_topic"
    assert "네피림" in neph["prompt_ko"] or "Nephilim" in neph["prompt_ko"]
    assert neph.get("highlight_node_ids")


def test_chapter_merge_reaches_fifty_from_seventeen_base() -> None:
    base = _load("docs/final/artifacts/showroom_meaning_topology_qa_presets_v1_latest.json")
    graph = _load("docs/final/artifacts/showroom_meaning_topology_graph_slice_v1_latest.json")
    conflict = _load("docs/final/artifacts/bigset_multi_topic_conflict_surface_v1_latest.json")
    doc, _ = merge_bigset_presets(dict(base), conflict, graph)
    doc, _ = merge_chapter_presets(doc, graph, target_count=50)
    assert len(doc["presets"]) >= 50


def test_nephilim_keywords_present() -> None:
    conflict = _load("docs/final/artifacts/bigset_multi_topic_conflict_surface_v1_latest.json")
    graph = _load("docs/final/artifacts/showroom_meaning_topology_graph_slice_v1_latest.json")
    merged, _ = merge_bigset_presets({"presets": []}, conflict, graph)
    neph = next(p for p in merged["presets"] if p["id"] == "bigset_topic_nephilim")
    kw = " ".join(neph.get("keywords") or []).lower()
    assert "nephilim" in kw
    assert "네피림" in kw


def test_keyword_router_matches_nephilim_free_query() -> None:
    from scripts.match_logos_studio_preset_query_v1 import load_default_lexical_index, resolve_preset_id

    presets_doc = _load("docs/final/artifacts/showroom_meaning_topology_qa_presets_v1_latest.json")
    lexical = load_default_lexical_index()
    resolved = resolve_preset_id(
        presets_doc["presets"],
        query="네피림이 뭐야?",
        lexical_index=lexical,
    )
    assert resolved["preset_id"] == "bigset_topic_nephilim"
    assert resolved["match"] in ("text", "lexical")


def test_lexical_router_matches_watchers_paraphrase() -> None:
    from scripts.match_logos_studio_preset_query_v1 import load_default_lexical_index, resolve_preset_id

    presets_doc = _load("docs/final/artifacts/showroom_meaning_topology_qa_presets_v1_latest.json")
    lexical = load_default_lexical_index()
    resolved = resolve_preset_id(
        presets_doc["presets"],
        query="감시자 watchers 타락 천사",
        lexical_index=lexical,
    )
    assert resolved["preset_id"] == "bigset_topic_watchers"
    assert resolved["match"] in ("text", "lexical")
