# @MKM12-METADATA
# Type: Logic
# Purpose: §4 Fact-Lock — canonical-only guard vs satellite dummy JSON.
# Keywords: logos, multi-corpus, constitution

from __future__ import annotations

import json
from pathlib import Path

from tests.multi_corpus_policy import (
    cross_ref_artifact_name,
    corpus_type_of,
    is_canonical_for_default_guard,
    iter_canonical_only,
)

_ROOT = Path(__file__).resolve().parents[1]
_DUMMY_SAT = _ROOT / "tests" / "fixtures" / "logos_satellite_dummy_one_verse.json"


def test_satellite_dummy_fixture_is_non_canonical() -> None:
    assert _DUMMY_SAT.is_file()
    doc = json.loads(_DUMMY_SAT.read_text(encoding="utf-8"))
    v = doc["verses"][0]
    assert corpus_type_of(v) == "apocrypha"
    assert not is_canonical_for_default_guard(v)


def test_default_guard_excludes_satellite_from_merged_stream() -> None:
    core_like = {"verse_id": "GEN_1_1", "corpus_type": "canonical"}
    doc = json.loads(_DUMMY_SAT.read_text(encoding="utf-8"))
    sat = doc["verses"][0]
    merged = [sat, core_like]
    canonical_only = list(iter_canonical_only(merged, include_satellites=False))
    assert canonical_only == [core_like]
    with_sat = list(iter_canonical_only(merged, include_satellites=True))
    assert len(with_sat) == 2


def test_implicit_canonical_when_field_missing() -> None:
    legacy = {"verse_id": "X_1_1"}
    assert corpus_type_of(legacy) == "canonical"
    assert is_canonical_for_default_guard(legacy)


def test_cross_ref_naming_convention() -> None:
    assert cross_ref_artifact_name("dss_war_scroll") == "CROSS_REF_dss_war_scroll.json"
