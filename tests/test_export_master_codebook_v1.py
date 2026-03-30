"""Master codebook lexicon V1 export contract."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
REPORT = REPO / "reports" / "constitution" / "btrack_pilot" / "master_codebook_lexicon_v1_41769_rows_latest.json"


def test_master_codebook_lexicon_v1_shape():
    if not REPORT.is_file():
        pytest.skip("master_codebook_lexicon_v1 export not generated")
    raw = REPORT.read_text(encoding="utf-8")
    d = json.loads(raw)
    assert d.get("schema") == "master_codebook_lexicon_v1"
    assert d.get("row_count") == 41769
    assert len(d.get("entries") or []) == 41769
    inp = d.get("inputs") or {}
    assert "atoms" in inp and inp["atoms"].get("sha256")
    ent0 = d["entries"][0]
    assert "atom_id" in ent0 and "lexicon_match_method" in ent0 and "morphhb_match_method" in ent0
