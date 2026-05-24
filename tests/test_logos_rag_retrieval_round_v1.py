"""Smoke tests for 2안 RAG round-1 helpers (no full index build)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def test_preprocess_query_normalizes_whitespace() -> None:
    from scripts.run_logos_rag_retrieval_round_v1 import preprocess_query

    assert preprocess_query("  Covenant   Stability  ") == "covenant stability"


def test_verse_text_for_embedding_reads_text_span() -> None:
    from scripts.logos_ann_lite_embedding_v1 import verse_text_for_embedding

    row = {
        "verse_id": "Gen.1.1",
        "text_span": {"original_script_text": "In the beginning"},
    }
    assert verse_text_for_embedding(row, 8192) == "In the beginning"


def test_comp_schema_constants() -> None:
    from scripts.run_logos_rag_retrieval_round_v1 import SCHEMA, VERSION

    assert SCHEMA == "comp_logos_rag_retrieval_v1"
    assert VERSION == "1.0.0"


def test_latest_comp_artifact_if_present() -> None:
    path = ROOT / "reports/constitution/btrack_pilot/comp_logos_rag_retrieval_v1_latest.json"
    if not path.is_file():
        pytest.skip("round not run yet")
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert doc.get("schema") == "comp_logos_rag_retrieval_v1"
    assert doc.get("track_wall", {}).get("prophecy_promotion_gates_touch") is False
    assert doc.get("track_wall", {}).get("use_gematria_4d_bridge") is False
