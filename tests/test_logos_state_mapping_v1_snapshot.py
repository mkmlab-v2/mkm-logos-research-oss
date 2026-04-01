# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.2, L:0.65, K:0.45, M:0.35}
# Balance: 80
# Purpose: CI Fact-Lock for tracked LOGOS_STATE_MAPPING_V1.json (no 88MB verse pipeline on runner).
# Keywords: logos, myeongni, snapshot, CI

"""Validate docs/final/artifacts/LOGOS_STATE_MAPPING_V1.json shape and regression totals.

Full recomputation requires local ``data/logos/verse_4pipeline_full_31102.json`` (~88MB, often untracked).
This test locks the committed snapshot only.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_ART = _ROOT / "docs" / "final" / "artifacts" / "LOGOS_STATE_MAPPING_V1.json"

# Regression lock (update when intentionally re-running join_logos_verses_myeongni_states_4d.py)
_EXPECTED_TOTAL = 14.15594185053369
_EXPECTED_MEAN = 0.8847463656583556


def test_logos_state_mapping_v1_exists_and_schema() -> None:
    assert _ART.is_file(), f"missing tracked artifact: {_ART}"
    doc = json.loads(_ART.read_text(encoding="utf-8"))
    assert doc.get("schema") == "logos_myeongni_state_join_v1"
    assert "manseryeok_scope" in doc
    assert doc["manseryeok_scope"].get("manseryeok_applicable") is False
    assert "assignments" in doc
    assert len(doc["assignments"]) == 16
    ids = [a["state_id"] for a in doc["assignments"]]
    assert sorted(ids) == list(range(1, 17))
    for a in doc["assignments"]:
        assert "verse_id" in a and str(a["verse_id"]).strip()
        assert "cosine_state_verse" in a
        assert -1.0 <= float(a["cosine_state_verse"]) <= 1.0


def test_logos_state_mapping_v1_regression_totals() -> None:
    doc = json.loads(_ART.read_text(encoding="utf-8"))
    assert doc["total_cosine_sum"] == pytest.approx(_EXPECTED_TOTAL, rel=0, abs=1e-9)
    assert doc["mean_cosine_per_pair"] == pytest.approx(_EXPECTED_MEAN, rel=0, abs=1e-12)
