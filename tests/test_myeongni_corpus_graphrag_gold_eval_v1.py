"""Myeongni corpus GraphRAG gold-path eval smoke."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_myeongni_graphrag_gold_eval_cli() -> None:
    import scripts.run_myeongni_corpus_graphrag_gold_eval_v1 as mod

    rc = mod.main(
        [
            "--output-json",
            str(ROOT / "reports/myeongni_corpus_graphrag_gold_eval_smoke_v1.json"),
            "--min-hit-rate",
            "0.0",
        ]
    )
    assert rc == 0
    out = ROOT / "reports/myeongni_corpus_graphrag_gold_eval_smoke_v1.json"
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "myeongni_corpus_graphrag_gold_eval_v1"
    assert doc["prophecy_vote"] == "none"
    assert doc["n_items"] >= 5
    assert doc["path_hit_rate"] is not None
    assert float(doc["path_hit_rate"]) >= 0.6


def test_gold_eval_rows_have_hits() -> None:
    from scripts.run_myeongni_corpus_graphrag_gold_eval_v1 import eval_gold

    gold = json.loads(
        (ROOT / "docs/final/artifacts/myeongni_corpus_graphrag_gold_human_v1.json").read_text(
            encoding="utf-8"
        )
    )
    doc = eval_gold(
        gold=gold,
        chunk_table=ROOT / "data/corpus/ijeoma/_inventory/IJEOMA_CHUNK_TABLE_2026-03-29.jsonl",
        state_probe=ROOT / "data/myeongni/16_STATE_MASTER_PROBE_v1.json",
        myeongni_lens=ROOT / "docs/final/artifacts/myeongni_independent_lens_latest.json",
        top_k=5,
    )
    assert any(r.get("hit") for r in doc["rows"])
