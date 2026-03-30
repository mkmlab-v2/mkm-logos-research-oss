"""Coverage v2 merged report contract."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


def test_coverage_v2_latest_shape():
    p = REPO / "reports" / "constitution" / "btrack_pilot" / "master_atoms_lexicon_coverage_summary_v2_latest.json"
    if not p.is_file():
        pytest.skip("coverage v2 not generated")
    d = json.loads(p.read_text(encoding="utf-8"))
    assert d.get("schema") == "master_atoms_lexicon_coverage_summary_v2"
    assert "by_rail" in d
    for rid in ("rail_strongs_seed", "rail_morphhb", "rail_step_audit"):
        assert rid in d["by_rail"]
    assert "corpus_buckets_ref" in d
