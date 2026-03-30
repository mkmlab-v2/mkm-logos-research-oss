# @MKM12-METADATA
# Type: Logic
# Purpose: CI schema lock for B-Track → HQ handoff (CROSS_REF_DSS_TO_STATES_DRAFT.json).
# Keywords: dss, cross-ref, constitution, draft

"""Smoke-test docs/final/artifacts/CROSS_REF_DSS_TO_STATES_DRAFT.json contract.

Required per-row fields: source_id, state_candidate_id, rationale.
Does not validate verse pipeline or trading logic — JSON shape only.
"""

from __future__ import annotations

import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_DRAFT = _ROOT / "docs" / "final" / "artifacts" / "CROSS_REF_DSS_TO_STATES_DRAFT.json"


def test_cross_ref_dss_draft_exists_and_top_level_schema() -> None:
    assert _DRAFT.is_file(), f"missing tracked artifact: {_DRAFT}"
    doc = json.loads(_DRAFT.read_text(encoding="utf-8"))
    assert doc.get("schema") == "cross_ref_dss_to_states_draft_v1"
    assert "disclaimer" in doc and str(doc["disclaimer"]).strip()
    assert "entries" in doc
    assert isinstance(doc["entries"], list)


def test_cross_ref_dss_draft_entry_rows_contract() -> None:
    doc = json.loads(_DRAFT.read_text(encoding="utf-8"))
    for i, row in enumerate(doc["entries"]):
        assert isinstance(row, dict), f"entries[{i}] must be object"
        assert "source_id" in row and str(row["source_id"]).strip(), (
            f"entries[{i}].source_id required (non-empty string)"
        )
        sid = row["state_candidate_id"]
        assert isinstance(sid, int), f"entries[{i}].state_candidate_id must be int"
        assert 1 <= sid <= 16, f"entries[{i}].state_candidate_id out of range 1–16"
        assert "rationale" in row and str(row["rationale"]).strip(), (
            f"entries[{i}].rationale required (non-empty string)"
        )
