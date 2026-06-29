"""TKM encounter_sequence P19 gate smoke."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p19_gate_v1_latest.json"
UNIFIED = ROOT / "reports/tkm_clinic_encounter_unified_disagreement_summary_v1_latest.json"


def test_p19_gate() -> None:
    if not GATE.is_file():
        pytest.skip("p19 gate missing")
    gate = json.loads(GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    assert gate.get("tkm_encounter_sequence_p19_status") == "clinic_bridge_weekly_ok"


def test_unified_summary() -> None:
    if not UNIFIED.is_file():
        pytest.skip("unified summary missing")
    doc = json.loads(UNIFIED.read_text(encoding="utf-8-sig"))
    assert doc.get("unified_ok") is True
    assert int(doc["clinic_mvp"]["row_count"] or 0) >= 1
    assert int(doc["encounter_sequence"]["sequence_count"] or 0) >= 1
