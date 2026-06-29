"""TKM encounter_sequence P33 cross-lens resonance gate smoke."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p33_gate_v1_latest.json"
CROSS = ROOT / "reports/tkm_encounter_sequence_cross_lens_kpi_v1_latest.json"
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"


def test_p33_gate() -> None:
    if not GATE.is_file():
        pytest.skip("p33 gate missing")
    gate = json.loads(GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    assert gate.get("tkm_encounter_sequence_p33_status") == "cross_lens_resonance_wire_ok"


def test_cross_lens_kpi() -> None:
    if not CROSS.is_file():
        pytest.skip("cross lens kpi missing")
    doc = json.loads(CROSS.read_text(encoding="utf-8-sig"))
    assert doc.get("kpi_ok") is True
    assert doc.get("non_gating") is True
    assert int(doc.get("l4_l5_l6_complete_row_count") or 0) >= 1
    assert isinstance(doc.get("cross_lens_resonance_index"), (int, float))


def test_weekly_l7_cross_lens_sync() -> None:
    if not WEEKLY.is_file():
        pytest.skip("weekly report missing")
    doc = json.loads(WEEKLY.read_text(encoding="utf-8-sig"))
    assert doc.get("version") in ("2.0.0", "2.1.0", "2.2.0", "2.3.0", "2.4.0", "5.4.0", "5.5.0", "5.6.0")
    l7 = doc.get("l7_cross_lens_kpi")
    assert isinstance(l7, dict)
    assert l7.get("cross_lens_headline_ok") is True
    assert l7.get("non_gating") is True
