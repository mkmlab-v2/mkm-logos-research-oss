"""Smoke: symbolic archetype stub contract + input paths."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STUB = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/SYMBOLIC_ARCHETYPE_PREDICTIVE_INDEX_STUB_V1.json"
)


def test_stub_exists_and_contract():
    assert STUB.is_file(), STUB
    doc = json.loads(STUB.read_text(encoding="utf-8-sig"))
    assert doc["schema"] == "symbolic_archetype_predictive_index_stub_v1"
    assert doc["research_only"] is True
    assert doc["track_a_active_write"] is False
    assert doc["track_a_promotion_signoff"] is False
    assert doc["status"] == "watch"
    assert doc["forbidden"]["ms_headline_paste_allowed"] is False


def test_stub_input_paths_exist():
    doc = json.loads(STUB.read_text(encoding="utf-8-sig"))
    for rel in doc["inputs"]:
        assert (ROOT / rel).is_file(), rel
