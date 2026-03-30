from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.core.master_codebook_lexicon_v1_bridge import (
    clear_codebook_cache,
    lexicon_hits_for_text,
    resolve_latest_codebook_path,
    unicode_word_tokens,
)
from scripts.report_multilens_performance_eval import evaluate_report


def test_unicode_word_tokens_splits_latin() -> None:
    assert "hello" in unicode_word_tokens("Hello, world!")


def test_lexicon_hits_intersection(tmp_path: Path) -> None:
    clear_codebook_cache()
    p = tmp_path / "master_codebook_lexicon_v1_2_rows_latest.json"
    p.write_text(
        json.dumps(
            {
                "schema": "master_codebook_lexicon_v1",
                "row_count": 2,
                "entries": [
                    {
                        "atom_id": "a1",
                        "lang": "en",
                        "normalized_form": "keepterm",
                        "lexicon_match_method": "test",
                        "morphhb_match_method": "test",
                    },
                    {
                        "atom_id": "a2",
                        "lang": "en",
                        "normalized_form": "otherform",
                        "lexicon_match_method": "test",
                        "morphhb_match_method": "test",
                    },
                ],
                "inputs": {},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    hits, meta = lexicon_hits_for_text("prefix keepterm suffix", p)
    assert meta["status"] == "ok"
    assert meta["hit_count"] == 1
    assert hits == {"keepterm"}


def test_evaluate_report_merges_lexicon_into_route_baseline(tmp_path: Path) -> None:
    clear_codebook_cache()
    p = tmp_path / "master_codebook_lexicon_v1_1_rows_latest.json"
    p.write_text(
        json.dumps(
            {
                "schema": "master_codebook_lexicon_v1",
                "row_count": 1,
                "entries": [
                    {
                        "atom_id": "a1",
                        "lang": "en",
                        "normalized_form": "keepterm",
                        "lexicon_match_method": "test",
                        "morphhb_match_method": "test",
                    }
                ],
                "inputs": {},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    doc = {
        "compression_cases": [
            {
                "id": "1",
                "raw_text": "alpha keepterm beta",
                "compressed_text": "c",
                "reconstructed_text": "alpha keepterm beta",
            }
        ],
        "fusion_answer_cases": [],
    }
    rep = evaluate_report(
        doc,
        source_input="fixture",
        mode="baseline",
        strategy="C",
        intensity="high",
        must_keep=set(),
        use_domain_router=False,
        use_master_codebook_lexicon_v1=True,
        master_codebook_lexicon_path=p,
    )
    row0 = rep["compression_metrics"]["cases"][0]
    route = row0.get("route") or {}
    m = route.get("master_codebook_lexicon_v1") or {}
    assert m.get("status") == "ok"
    assert m.get("hit_count", 0) >= 1
    assert "keepterm" in m.get("hits_sample", [])


def test_resolve_explicit_path() -> None:
    p = Path("nonexistent_codebook_xyz.json")
    assert resolve_latest_codebook_path(explicit=p) is None
