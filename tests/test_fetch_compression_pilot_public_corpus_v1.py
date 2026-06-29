"""Public-open corpus fetch — stats and merge contract (offline)."""

from __future__ import annotations

import json
from unittest.mock import patch

from scripts.fetch_compression_pilot_public_corpus_v1 import build_corpus, _base_row


def _fake_row(source: str, n: int) -> list[dict]:
    return [
        _base_row(
            row_id=f"test-{source}-{i:03d}",
            source=source,
            domain_tag="test",
            text=f"sample {source} {i}",
        )
        for i in range(n)
    ]


def test_build_corpus_source_stats_pre_merge_not_post_drain():
    hn = _fake_row("hn_firebase_api_v1", 3)
    wiki = _fake_row("wikipedia_rest_v1", 4)
    arxiv = _fake_row("arxiv_cs_ai_rss_v1", 2)

    with patch(
        "scripts.fetch_compression_pilot_public_corpus_v1.fetch_hn",
        return_value=hn,
    ), patch(
        "scripts.fetch_compression_pilot_public_corpus_v1.fetch_wikipedia",
        return_value=wiki,
    ), patch(
        "scripts.fetch_compression_pilot_public_corpus_v1.fetch_arxiv_rss",
        return_value=arxiv,
    ):
        merged, errors, stats = build_corpus(max_cases=6, timeout=1.0)

    assert errors == []
    assert stats["hn"] == 3
    assert stats["wikipedia"] == 4
    assert stats["arxiv_rss"] == 2
    assert stats["merged"] == 6
    assert len(merged) == 6


def test_base_row_governance_fields():
    row = _base_row(row_id="x", source="s", domain_tag="d", text="t")
    assert row["send_gate"] == "HOLD"
    assert row["ready_for_external_send"] is False
    assert "public_open_web" in row["labels"]
