# @MKM12-METADATA
# Type: Logic
# Purpose: CI schema lock for B-Track → HQ handoff (CROSS_REF_DSS_TO_STATES_DRAFT.json).
# Keywords: dss, cross-ref, constitution, draft

"""Smoke-test docs/final/artifacts/CROSS_REF_DSS_TO_STATES_DRAFT.json contract.

§4.5-aligned rows: entry_id, satellite_ref, corpus_type, link_type, state_candidate_id, rationale; optional `note` (bench meta).
Legacy ``source_id`` retained for human diff. Does not validate verse pipeline or trading logic.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_DRAFT = _ROOT / "docs" / "final" / "artifacts" / "CROSS_REF_DSS_TO_STATES_DRAFT.json"
_SCHEMA = _ROOT / "docs" / "final" / "CROSS_REF_DRAFT_V2_DOCUMENT.schema.json"
_LOGOS_ASSIGN = _ROOT / "docs" / "final" / "artifacts" / "LOGOS_STATE_MAPPING_V1.json"

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


def _state_id_to_verse_id() -> dict[int, str]:
    logos = json.loads(_LOGOS_ASSIGN.read_text(encoding="utf-8"))
    out: dict[int, str] = {}
    for a in logos["assignments"]:
        out[int(a["state_id"])] = str(a["verse_id"])
    return out


def test_cross_ref_dss_draft_exists_and_top_level_schema() -> None:
    assert _DRAFT.is_file(), f"missing tracked artifact: {_DRAFT}"
    doc = json.loads(_DRAFT.read_text(encoding="utf-8"))
    assert doc.get("schema") == "cross_ref_dss_to_states_draft_v2"
    assert "disclaimer" in doc and str(doc["disclaimer"]).strip()
    assert doc.get("canonical_join_ssot") == "docs/final/artifacts/LOGOS_STATE_MAPPING_V1.json"
    assert "entries" in doc
    assert isinstance(doc["entries"], list)


def test_cross_ref_dss_draft_entry_rows_contract() -> None:
    assert _LOGOS_ASSIGN.is_file(), f"missing: {_LOGOS_ASSIGN}"
    by_state = _state_id_to_verse_id()
    doc = json.loads(_DRAFT.read_text(encoding="utf-8"))
    assert len(doc["entries"]) == 16
    for i, row in enumerate(doc["entries"]):
        assert isinstance(row, dict), f"entries[{i}] must be object"
        eid = row.get("entry_id")
        assert isinstance(eid, str) and eid.startswith("ENTRY_"), f"entries[{i}].entry_id"
        sid = row["state_candidate_id"]
        exp_verse = by_state[int(sid)]
        assert row.get("canonical_ref") == exp_verse, (
            f"entries[{i}].canonical_ref must match LOGOS_STATE_MAPPING_V1 for state_id={sid}"
        )
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
        assert isinstance(sid, int), f"entries[{i}].state_candidate_id must be int"
        assert 1 <= sid <= 16, f"entries[{i}].state_candidate_id out of range 1–16"
        assert "rationale" in row and str(row["rationale"]).strip(), (
            f"entries[{i}].rationale required (non-empty string)"
        )
        note = row.get("note")
        assert note is None or (isinstance(note, str) and note.strip()), f"entries[{i}].note must be non-empty if present"

    e11 = next(e for e in doc["entries"] if e.get("entry_id") == "ENTRY_11")
    assert "note" in e11 and "NL v2.1" in e11["note"] and "[HYPO]" in e11["note"], (
        "ENTRY_11 must retain NL v2.1 bench note block (ISOLATE_AND_REFINE)"
    )


def test_cross_ref_draft_validates_against_json_schema() -> None:
    """Draft-07 validation via jsonschema (dev/CI dependency)."""
    jsonschema = pytest.importorskip("jsonschema")
    assert _SCHEMA.is_file(), f"missing schema: {_SCHEMA}"
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    doc = json.loads(_DRAFT.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(doc)


def test_entry_12_13_16_anchor_gate_locked_until_evidence_update() -> None:
    """ENTRY_12/13/16 must stay blocked until concrete anchors are added."""
    doc = json.loads(_DRAFT.read_text(encoding="utf-8"))
    for eid in ("ENTRY_12", "ENTRY_13", "ENTRY_16"):
        row = next(e for e in doc["entries"] if e.get("entry_id") == eid)
        sat = str(row.get("satellite_ref", ""))
        assert "status=missing_anchor_until_source_update" in sat, (
            f"{eid} must stay locked with missing_anchor gate in satellite_ref"
        )


def test_entry_14_partial_anchor_verified_gate() -> None:
    """ENTRY_14 keeps fragment line TBD but records DJD XIV witness+plates."""
    doc = json.loads(_DRAFT.read_text(encoding="utf-8"))
    row = next(e for e in doc["entries"] if e.get("entry_id") == "ENTRY_14")
    sat = str(row.get("satellite_ref", ""))
    assert "status=partial_anchor_verified (witness-set+plates)" in sat
    assert "Pls I-XXXI" in sat


def test_entry_15_partial_anchor_verified_gate() -> None:
    """ENTRY_15 keeps Gen.49.19 line TBD but records DJD XII witness+plates."""
    doc = json.loads(_DRAFT.read_text(encoding="utf-8"))
    row = next(e for e in doc["entries"] if e.get("entry_id") == "ENTRY_15")
    sat = str(row.get("satellite_ref", ""))
    assert "status=partial_anchor_verified (witness-set+plates)" in sat
    assert "Pls VI-XIII" in sat


def test_entry_06_07_08_10_partial_anchor_gates() -> None:
    """Entries with verified subset anchors keep explicit partial status."""
    doc = json.loads(_DRAFT.read_text(encoding="utf-8"))
    expected = {
        "ENTRY_06": "status=partial_anchor_verified (column)",
        "ENTRY_07": "status=partial_anchor_verified (column-range)",
        "ENTRY_08": "status=partial_anchor_verified (sigla+plates)",
        "ENTRY_10": "status=partial_anchor_verified (plates)",
        "ENTRY_09": "status=partial_anchor_verified (frag+col)",
        "ENTRY_15": "status=partial_anchor_verified (witness-set+plates)",
    }
    for eid, marker in expected.items():
        row = next(e for e in doc["entries"] if e.get("entry_id") == eid)
        sat = str(row.get("satellite_ref", ""))
        assert marker in sat, f"{eid} must retain marker: {marker}"
