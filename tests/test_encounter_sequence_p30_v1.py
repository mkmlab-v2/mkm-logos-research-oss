"""TKM encounter_sequence P30 physician_gold engine myeongni wire gate smoke."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p30_gate_v1_latest.json"
KPI = ROOT / "reports/tkm_encounter_sequence_myeongni_kpi_v1_latest.json"
PASSIVE = ROOT / "reports/tkm_myeongni_passive_observation_v1_latest.json"
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"


def test_p30_gate() -> None:
    if not GATE.is_file():
        pytest.skip("p30 gate missing")
    gate = json.loads(GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    assert gate.get("tkm_encounter_sequence_p30_status") == "myeongni_engine_wire_ok"


def test_myeongni_kpi_engine_linked() -> None:
    if not KPI.is_file():
        pytest.skip("myeongni kpi missing")
    doc = json.loads(KPI.read_text(encoding="utf-8-sig"))
    assert doc.get("kpi_ok") is True
    gold = doc.get("physician_gold_only")
    assert isinstance(gold, dict)
    assert int(gold.get("engine_report_linked_count") or 0) >= 1


def test_passive_observation() -> None:
    if not PASSIVE.is_file():
        pytest.skip("passive observation missing")
    doc = json.loads(PASSIVE.read_text(encoding="utf-8-sig"))
    assert doc.get("observation_ok") is True


def test_weekly_l5_engine_kpi() -> None:
    if not WEEKLY.is_file():
        pytest.skip("weekly report missing")
    doc = json.loads(WEEKLY.read_text(encoding="utf-8-sig"))
    assert doc.get("version") in ("1.7.0", "1.8.0", "1.9.0", "2.0.0", "2.1.0", "2.2.0", "2.3.0", "2.4.0", "5.4.0", "5.5.0", "5.6.0")
    l5 = doc.get("l5_myeongni_kpi")
    assert isinstance(l5, dict)
    assert l5.get("l5_myeongni_headline_ok") is True
    assert int(l5.get("engine_report_linked_count") or 0) >= 1
