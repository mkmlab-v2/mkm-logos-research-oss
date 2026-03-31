# @MKM12-METADATA
# Type: Logic
# Purpose: CI lock for B-Track SASANG bench (SASANG_CROSS_REF_DRAFT.json vs chunk table + LOGOS).
# Keywords: ijeoma, sasang, cross-ref, constitution

"""Smoke-test docs/final/artifacts/SASANG_CROSS_REF_DRAFT.json.

Bench-only: analogy_bench rows; chunk_id must exist in IJEOMA_CHUNK_TABLE; canonical_ref matches
LOGOS_STATE_MAPPING_V1 for each state_candidate_id. Does not validate prescription or dual_regime.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

_ROOT = Path(__file__).resolve().parents[1]
_SASANG = _ROOT / "docs" / "final" / "artifacts" / "SASANG_CROSS_REF_DRAFT.json"
_CHUNK_TABLE = _ROOT / "data" / "corpus" / "ijeoma" / "_inventory" / "IJEOMA_CHUNK_TABLE_2026-03-29.jsonl"
_LOGOS_ASSIGN = _ROOT / "docs" / "final" / "artifacts" / "LOGOS_STATE_MAPPING_V1.json"

_LINKS = frozenset(
    {"thematic", "lexical", "geometric", "temporal", "analogy_bench"}
)
_CORPUS_IJEOMA = "ijeoma_chunk"
_SASANG_TYPES = frozenset(
    {
        "tae_yang",
        "meta_yin_yang_change",
        "so_eum",
        "so_yang",
        "tae_eum",
    }
)
# Bench v1 minimum (formerly fixed at 3); grow rows without lowering per-entry checks.
_MIN_ENTRIES = 3
_MAX_ENTRIES = 512


def _state_id_to_verse_id() -> dict[int, str]:
    logos = json.loads(_LOGOS_ASSIGN.read_text(encoding="utf-8"))
    out: dict[int, str] = {}
    for a in logos["assignments"]:
        out[int(a["state_id"])] = str(a["verse_id"])
    return out


def _chunk_rows_by_id() -> dict[str, dict]:
    out: dict[str, dict] = {}
    text = _CHUNK_TABLE.read_text(encoding="utf-8")
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        out[str(row["chunk_id"])] = row
    return out


def test_sasang_cross_ref_draft_exists_and_schema() -> None:
    assert _SASANG.is_file(), f"missing tracked artifact: {_SASANG}"
    doc = json.loads(_SASANG.read_text(encoding="utf-8"))
    assert doc.get("schema") == "sasang_cross_ref_draft_v1"
    assert "disclaimer" in doc and str(doc["disclaimer"]).strip()
    assert doc.get("chunk_table_ssot") == "data/corpus/ijeoma/_inventory/IJEOMA_CHUNK_TABLE_2026-03-29.jsonl"
    assert "entries" in doc and isinstance(doc["entries"], list)


def test_sasang_cross_ref_entries_contract() -> None:
    assert _LOGOS_ASSIGN.is_file(), f"missing: {_LOGOS_ASSIGN}"
    if not _CHUNK_TABLE.is_file():
        pytest.skip(f"optional chunk table artifact missing in this environment: {_CHUNK_TABLE}")
    by_state = _state_id_to_verse_id()
    chunks = _chunk_rows_by_id()
    doc = json.loads(_SASANG.read_text(encoding="utf-8"))
    entries = doc["entries"]
    assert len(entries) >= _MIN_ENTRIES, (
        f"SASANG bench v1: need at least {_MIN_ENTRIES} rows, got {len(entries)}"
    )
    assert len(entries) <= _MAX_ENTRIES, (
        f"SASANG bench: cap {_MAX_ENTRIES} rows for CI sanity (got {len(entries)})"
    )
    for i, row in enumerate(entries):
        eid = row.get("entry_id")
        assert isinstance(eid, str) and eid.startswith("SASANG_ENTRY_"), f"entries[{i}].entry_id"
        cid = row.get("chunk_id")
        assert cid in chunks, f"entries[{i}].chunk_id not in chunk table: {cid}"
        cr = chunks[cid]
        assert int(row["line_start"]) == int(cr["line_start"]), f"entries[{i}] line_start vs table"
        assert int(row["line_end"]) == int(cr["line_end"]), f"entries[{i}] line_end vs table"
        st = row.get("sasang_type")
        assert st in _SASANG_TYPES, f"entries[{i}].sasang_type must be v1 enum: {st}"
        sid = row["state_candidate_id"]
        assert isinstance(sid, int) and 1 <= sid <= 16
        exp_verse = by_state[int(sid)]
        assert row.get("canonical_ref") == exp_verse, (
            f"entries[{i}].canonical_ref must match LOGOS_STATE_MAPPING_V1 for state_id={sid}"
        )
        assert row.get("corpus_type") == _CORPUS_IJEOMA
        assert row.get("link_type") in _LINKS
        cf = row.get("confidence")
        assert isinstance(cf, (int, float)) and 0.0 <= float(cf) <= 1.0, f"entries[{i}].confidence"
        assert isinstance(row.get("satellite_ref"), str) and row["satellite_ref"].strip()
        assert "[HYPO]" in str(row.get("rationale", "")), f"entries[{i}].rationale must tag [HYPO]"
