"""B-track: deterministic va_tag_boost_v1 rows from fixture (policy contract, no chain)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_va_fusion_policy_golden_fixture_matches_fusion_multiplier() -> None:
    from scripts.build_cross_lens_fusion_report_v1 import fusion_multiplier

    fixture = ROOT / "tests/fixtures/va_fusion_policy_golden_v1.json"
    doc = json.loads(fixture.read_text(encoding="utf-8"))
    assert doc.get("schema") == "va_fusion_policy_golden_v1"
    rows = doc.get("rows")
    assert isinstance(rows, list) and rows
    for row in rows:
        v = float(row["valence"])
        a = float(row["arousal"])
        tags = [str(t) for t in row["tags"]]
        m, matched = fusion_multiplier(v, a, tags)
        assert m == pytest.approx(float(row["expect_multiplier"]), abs=1e-9)
        for x in row.get("expect_matched_contains") or []:
            assert str(x) in matched, (row, matched)
