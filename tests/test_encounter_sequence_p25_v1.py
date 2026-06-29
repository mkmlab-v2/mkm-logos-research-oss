"""TKM encounter_sequence P25 gate smoke."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p25_gate_v1_latest.json"
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"


def test_p25_gate() -> None:
    if not GATE.is_file():
        pytest.skip("p25 gate missing")
    gate = json.loads(GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    assert gate.get("tkm_encounter_sequence_p25_status") == "match_rate_delta_multiturn_gold_ok"
    assert int(gate.get("physician_gold_auto03_turn_count") or 0) >= 3


def test_weekly_match_rate_delta_kpi() -> None:
    if not WEEKLY.is_file():
        pytest.skip("weekly missing")
    doc = json.loads(WEEKLY.read_text(encoding="utf-8-sig"))
    delta = doc.get("match_rate_delta_kpi")
    assert isinstance(delta, dict)
    assert delta.get("delta_kpi_ok") is True
    assert delta.get("match_rate_delta_encounter_minus_clinic") is not None
