"""resolve_km_classics_citations_hypo_v1 tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from resolve_km_classics_citations_hypo_v1 import load_index, resolve_classic_refs  # noqa: E402

STUB_INDEX = ROOT / "tests/fixtures/km_classics_index_hypo_v1.stub.json"


def test_resolve_by_source_id() -> None:
    doc = load_index(STUB_INDEX)
    first_id = doc["entries"][0]["source_id"]
    refs = resolve_classic_refs(doc, source_ids=[first_id])
    assert len(refs) == 1
    assert refs[0]["citation_valid"] is True
    assert refs[0]["read_only"] is True
    assert refs[0]["source_id"] == first_id


def test_resolve_by_query_donguibogam() -> None:
    doc = load_index(STUB_INDEX)
    refs = resolve_classic_refs(doc, retrieval_query="donguibogam")
    assert refs
    assert all(r["citation_valid"] for r in refs)


def test_invalid_source_id_citation_valid_false() -> None:
    doc = load_index(STUB_INDEX)
    refs = resolve_classic_refs(doc, source_ids=["kmc-deadbeef"])
    assert refs[0]["citation_valid"] is False
