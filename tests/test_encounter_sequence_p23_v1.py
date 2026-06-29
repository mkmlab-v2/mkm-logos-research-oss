"""TKM encounter_sequence P23 gate smoke."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p23_gate_v1_latest.json"
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"


def test_p23_gate() -> None:
    if not GATE.is_file():
        pytest.skip("p23 gate missing")
    gate = json.loads(GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    assert gate.get("tkm_encounter_sequence_p23_status") == "physician_gold_dual_lane_headline_ok"


def test_weekly_dual_lane_headline() -> None:
    if not WEEKLY.is_file():
        pytest.skip("weekly report missing")
    doc = json.loads(WEEKLY.read_text(encoding="utf-8-sig"))
    headline = doc.get("headline_kpi")
    assert isinstance(headline, dict)
    assert headline.get("dual_lane_headline_ok") is True
    assert headline.get("lane") == "physician_gold_only"
    assert int(headline.get("encounter_sequence_count") or 0) >= 3
    dummy = headline.get("operational_dummy_lane")
    assert isinstance(dummy, dict)
    blended = doc.get("blended_all_ledger")
    assert isinstance(blended, dict)
    assert doc.get("sequence_count") == headline.get("encounter_sequence_count")
