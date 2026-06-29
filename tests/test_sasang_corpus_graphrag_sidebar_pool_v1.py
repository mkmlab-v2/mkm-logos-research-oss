"""Sasang sidebar pool + token proxy bench smoke."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_sasang_sidebar_pool_build() -> None:
    import scripts.build_sasang_corpus_graphrag_sidebar_pool_v1 as mod

    rc = mod.main(
        [
            "--output-json",
            str(ROOT / "reports/sasang_corpus_graphrag_sidebar_pool_smoke_v1.json"),
            "--report-json",
            str(ROOT / "reports/sasang_corpus_graphrag_sidebar_pool_smoke_v1.json"),
        ]
    )
    assert rc == 0
    doc = json.loads(
        (ROOT / "reports/sasang_corpus_graphrag_sidebar_pool_smoke_v1.json").read_text(encoding="utf-8")
    )
    assert doc["schema"] == "sasang_corpus_graphrag_sidebar_pool_v1"
    assert doc["prophecy_vote"] == "none"
    assert doc["pool_counts"]["total"] >= 2


def test_token_proxy_bench_cli() -> None:
    import scripts.run_myeongni_sasang_graphrag_token_proxy_bench_v1 as mod

    rc = mod.main(
        [
            "--output-json",
            str(ROOT / "reports/myeongni_sasang_graphrag_token_proxy_bench_smoke_v1.json"),
        ]
    )
    assert rc == 0
    doc = json.loads(
        (ROOT / "reports/myeongni_sasang_graphrag_token_proxy_bench_smoke_v1.json").read_text(encoding="utf-8")
    )
    assert doc["prophecy_vote"] == "none"
    assert float((doc.get("char_budget") or {}).get("estimated_char_savings_ratio") or 0) > 0
