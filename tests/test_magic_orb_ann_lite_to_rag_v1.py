"""Tests for magic_orb ANN-lite → rag bridge."""
from __future__ import annotations

from scripts.magic_orb_ann_lite_to_rag_v1 import ann_query_doc_to_rag_rows


def test_ann_query_doc_to_rag_rows_top_k():
    doc = {
        "schema": "logos_vector_ann_lite_query_result_v1",
        "top_k": [{"verse_id": "john.19.34", "score": 0.88}],
    }
    rows = ann_query_doc_to_rag_rows(doc)
    assert len(rows) == 1
    assert rows[0]["source_id"] == "logos_ann_lite:verse:john.19.34"
    assert "ANN-lite" in rows[0]["snippet"]
