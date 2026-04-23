"""Master codebook lexicon V1 export contract."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
_PILOT = REPO / "reports" / "constitution" / "btrack_pilot"
_NAME_RE = re.compile(r"master_codebook_lexicon_v1_(\d+)_rows_latest\.json$")


def _latest_export_path() -> Path | None:
    best: Path | None = None
    best_n = -1
    for p in _PILOT.glob("master_codebook_lexicon_v1_*_rows_latest.json"):
        m = _NAME_RE.search(p.name)
        if not m:
            continue
        n = int(m.group(1))
        if n > best_n:
            best_n, best = n, p
    return best


def test_master_codebook_lexicon_v1_shape():
    REPORT = _latest_export_path()
    if REPORT is None or not REPORT.is_file():
        pytest.skip("master_codebook_lexicon_v1 export not generated")
    raw = REPORT.read_text(encoding="utf-8")
    d = json.loads(raw)
    assert d.get("schema") == "master_codebook_lexicon_v1"
    rc = int(d.get("row_count") or 0)
    entries = d.get("entries") or []
    assert rc == len(entries)
    assert rc >= 1
    inp = d.get("inputs") or {}
    assert "atoms" in inp and inp["atoms"].get("sha256")
    ent0 = d["entries"][0]
    assert "atom_id" in ent0 and "lexicon_match_method" in ent0 and "morphhb_match_method" in ent0
