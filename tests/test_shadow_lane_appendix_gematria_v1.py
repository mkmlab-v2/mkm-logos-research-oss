from __future__ import annotations

import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
APPENDIX = _ROOT / "reports/shadow_lane_appendix_gematria_v1_latest.json"
GATE = _ROOT / "docs/final/artifacts/shadow_lane_gematria_gate_v1_latest.json"
CANON = _ROOT / "reports/constitution/btrack_pilot/logos_verse_4d_v1_latest.jsonl"


def test_appendix_schema_and_isolation_flags() -> None:
    if not APPENDIX.is_file():
        pytest.skip("appendix not built")
    doc = json.loads(APPENDIX.read_text(encoding="utf-8-sig"))
    assert doc.get("schema") == "shadow_lane_appendix_gematria_v1"
    tw = doc.get("track_wall") or {}
    assert tw.get("merge_into_canon_31k_41k") is False
    assert int((doc.get("summary") or {}).get("total_rows") or 0) >= 100
    lanes = (doc.get("summary") or {}).get("by_lane") or {}
    assert lanes.get("dss", 0) >= 1
    assert lanes.get("apocrypha", 0) >= 1


def test_gate_ok_and_canon_untouched() -> None:
    if not GATE.is_file():
        pytest.skip("gate not built")
    doc = json.loads(GATE.read_text(encoding="utf-8-sig"))
    assert doc.get("gate_ok") is True
    if CANON.is_file():
        for line in CANON.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            vid = str(row.get("verse_id") or "")
            assert not vid.startswith("apo:")
            assert not vid.lower().startswith("dss")
