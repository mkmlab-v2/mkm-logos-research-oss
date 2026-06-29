#!/usr/bin/env python3
"""Tests for logos ANN typology boost (CPU-only)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import apply_logos_ann_typology_boost_v1 as boost_mod


def test_match_q06_theme_by_query_id() -> None:
    lex = json.loads(
        (ROOT / "docs/final/fixtures/logos_ann_typology_lexicon_v1.json").read_text(encoding="utf-8")
    )
    entries = boost_mod.match_lexicon_entries(
        query="예수가 십자가에 못박혀 돌아가실 때 흘린 물과 피의 상징은 무엇을 의미하는가?",
        query_id="q06",
        lexicon=lex,
    )
    assert any(e.get("theme_id") == "passion_blood_water_symbolism" for e in entries)


def test_boost_injects_john_19_34() -> None:
    lex = json.loads(
        (ROOT / "docs/final/fixtures/logos_ann_typology_lexicon_v1.json").read_text(encoding="utf-8")
    )
    ann = {
        "schema": "logos_vector_ann_lite_query_result_v1",
        "top_k": [{"verse_id": "Isa.28.8", "score": 0.39}],
    }
    boosted, meta = boost_mod.apply_typology_boost(
        ann,
        query="예수가 십자가에 못박혀 돌아가실 때 흘린 물과 피의 상징은 무엇을 의미하는가?",
        query_id="q06",
        lexicon=lex,
    )
    top_ids = [r["verse_id"] for r in boosted["top_k"]]
    assert "John.19.34" in top_ids
    assert meta["applied"] is True
    assert boosted["top_k"][0]["verse_id"] in {"John.19.34", "1John.5.6", "Lev.17.11"}


def test_gold_fixture_includes_q08() -> None:
    doc = json.loads((ROOT / "docs/final/fixtures/logos_gold_query_eval_v1.json").read_text(encoding="utf-8"))
    ids = {it["id"] for it in doc["items"]}
    assert "q08" in ids
