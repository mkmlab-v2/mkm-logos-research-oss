"""TKM encounter_sequence P24 gate smoke."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p24_gate_v1_latest.json"
DUAL = ROOT / "reports/tkm_clinic_encounter_dual_lane_summary_v1_latest.json"


def test_p24_gate() -> None:
    if not GATE.is_file():
        pytest.skip("p24 gate missing")
    gate = json.loads(GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    assert gate.get("tkm_encounter_sequence_p24_status") == "encounter_match_rate_ok"


def test_encounter_match_rate_populated() -> None:
    if not DUAL.is_file():
        pytest.skip("dual lane summary missing")
    doc = json.loads(DUAL.read_text(encoding="utf-8-sig"))
    gold = doc.get("physician_gold_only")
    assert isinstance(gold, dict)
    rate = gold.get("encounter_match_rate")
    assert rate is not None
    assert 0.0 <= float(rate) <= 1.0
