"""Unit tests for bilingual hybrid query helpers."""
from __future__ import annotations

from scripts.logos_rag_hybrid_query_v1 import build_hybrid_text_query


def test_build_hybrid_ko_primary():
    text, style = build_hybrid_text_query("covenant crisis", "위기 언약", style="ko_primary")
    assert style == "hybrid_ko_primary"
    assert "위기" in text


def test_build_hybrid_dual_mean_empty_text():
    text, style = build_hybrid_text_query("a", "가", style="dual_embed_mean")
    assert style == "hybrid_dual_embed_mean"
    assert text == ""
