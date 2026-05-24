"""Lexicon hit-rate bench smoke."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_lexicon_hit_rate_bench_schema() -> None:
    from scripts.build_mkm_inter_agent_lexicon_hit_rate_bench_v1 import run_bench

    doc = run_bench()
    assert doc.get("ok") is True
    assert doc.get("schema") == "mkm_inter_agent_lexicon_hit_rate_bench_v1"
    assert doc.get("research_only") is True
    corpora = doc.get("corpora") or {}
    assert "lexicon_dense" in corpora
    dense = corpora["lexicon_dense"]
    assert dense.get("avg_atom_rate_tokens") is not None
