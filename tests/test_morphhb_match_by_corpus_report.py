"""MorphHB × corpus crosstab report contract."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]

REPORT = (
    REPO / "reports" / "constitution" / "btrack_pilot" / "master_atoms_morphhb_match_by_corpus_latest.json"
)


def test_morphhb_match_by_corpus_latest_shape():
    if not REPORT.is_file():
        pytest.skip("master_atoms_morphhb_match_by_corpus_latest.json not generated")
    d = json.loads(REPORT.read_text(encoding="utf-8"))
    assert d.get("schema") == "master_atoms_morphhb_match_by_corpus_v1"
    assert d.get("hebrew_rows_in_morphhb_seed", 0) > 0
    assert "by_match_method" in d
    assert "crosstab_match_method_x_exclusive_pattern" in d
    for rid in ("morphhb_unmatched", "morphhb_wlc", "morphhb_wlc_multi", "morphhb_wlc_no_strong"):
        assert rid in d["crosstab_match_method_x_exclusive_pattern"]
