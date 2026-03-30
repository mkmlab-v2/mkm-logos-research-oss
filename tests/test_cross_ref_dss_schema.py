# @MKM12-METADATA
# Type: Logic
# Purpose: CI schema lock for B-Track → HQ handoff (CROSS_REF_DSS_TO_STATES_DRAFT.json).
# Keywords: dss, cross-ref, constitution, draft

"""Smoke-test docs/final/artifacts/CROSS_REF_DSS_TO_STATES_DRAFT.json contract.

§4.5-aligned rows: entry_id, satellite_ref, corpus_type, link_type, state_candidate_id, rationale.
Legacy ``source_id`` retained for human diff. Does not validate verse pipeline or trading logic.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_DRAFT = _ROOT / "docs" / "final" / "artifacts" / "CROSS_REF_DSS_TO_STATES_DRAFT.json"
_SCHEMA = _ROOT / "docs" / "final" / "CROSS_REF_DRAFT_V2_DOCUMENT.schema.json"

_CORPUS = frozenset({"dss", "apocrypha", "pseudepigrapha", "myeongni_probe"})
_LINKS = frozenset(
    {
        "thematic",
        "lexical",
        "geometric",
        "temporal",
        "analogy_bench",
    }
)


def test_cross_ref_dss_draft_exists_and_top_level_schema() -> None:
    assert _DRAFT.is_file(), f"missing tracked artifact: {_DRAFT}"
    doc = json.loads(_DRAFT.read_text(encoding="utf-8"))
    assert doc.get("schema") == "cross_ref_dss_to_states_draft_v2"
    assert "disclaimer" in doc and str(doc["disclaimer"]).strip()
    assert "entries" in doc
    assert isinstance(doc["entries"], list)


def test_cross_ref_dss_draft_entry_rows_contract() -> None:
    doc = json.loads(_DRAFT.read_text(encoding="utf-8"))
    assert len(doc["entries"]) == 5
    for i, row in enumerate(doc["entries"]):
        assert isinstance(row, dict), f"entries[{i}] must be object"
        eid = row.get("entry_id")
        assert isinstance(eid, str) and eid.startswith("ENTRY_"), f"entries[{i}].entry_id"
        assert row.get("canonical_ref") is None, f"entries[{i}]: canonical_ref TBD until A-Track link"
        sat = row.get("satellite_ref")
        assert isinstance(sat, str) and sat.strip(), f"entries[{i}].satellite_ref required"
        assert "source_id" in row and row["source_id"] == sat, f"entries[{i}].source_id mirrors satellite_ref"
        ct = row.get("corpus_type")
        assert ct in _CORPUS, f"entries[{i}].corpus_type invalid: {ct}"
        lt = row.get("link_type")
        assert lt in _LINKS, f"entries[{i}].link_type invalid: {lt}"
        cf = row.get("confidence")
        assert cf is None or (isinstance(cf, (int, float)) and 0.0 <= float(cf) <= 1.0), (
            f"entries[{i}].confidence"
        )
        sid = row["state_candidate_id"]
        assert isinstance(sid, int), f"entries[{i}].state_candidate_id must be int"
        assert 1 <= sid <= 16, f"entries[{i}].state_candidate_id out of range 1–16"
        assert "rationale" in row and str(row["rationale"]).strip(), (
            f"entries[{i}].rationale required (non-empty string)"
        )


def test_cross_ref_draft_validates_against_json_schema() -> None:
    """Draft-07 validation via jsonschema (dev/CI dependency)."""
    jsonschema = pytest.importorskip("jsonschema")
    assert _SCHEMA.is_file(), f"missing schema: {_SCHEMA}"
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    doc = json.loads(_DRAFT.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(doc)
