"""Canon-only MorphHB unmatched top-N audit contract."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
REPORT = REPO / "reports" / "constitution" / "btrack_pilot" / "canon_unmatched_top100_audit_latest.json"


def test_canon_unmatched_top100_audit_shape():
    if not REPORT.is_file():
        pytest.skip("canon_unmatched_top100_audit_latest.json not generated")
    d = json.loads(REPORT.read_text(encoding="utf-8"))
    assert d.get("schema") == "canon_unmatched_morphhb_top_audit_v1"
    assert d.get("filter", {}).get("exclusive_pattern") == "canon_decode_only"
    rows = d.get("rows") or []
    assert len(rows) <= 100
    if rows:
        assert "occurrences" in rows[0]
        assert "normalized_form" in rows[0]
