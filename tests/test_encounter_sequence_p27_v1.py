"""TKM encounter_sequence P27 gate smoke."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p27_gate_v1_latest.json"
MYEONGNI_KPI = ROOT / "reports/tkm_encounter_sequence_myeongni_kpi_v1_latest.json"
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"


def test_p27_gate() -> None:
    if not GATE.is_file():
        pytest.skip("p27 gate missing")
    gate = json.loads(GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    assert gate.get("tkm_encounter_sequence_p27_status") == "myeongni_lens_wire_ok"


def test_myeongni_kpi_artifact() -> None:
    if not MYEONGNI_KPI.is_file():
        pytest.skip("myeongni kpi missing")
    doc = json.loads(MYEONGNI_KPI.read_text(encoding="utf-8-sig"))
    assert doc.get("kpi_ok") is True
    gold = doc.get("physician_gold_only")
    assert isinstance(gold, dict)
    assert int(gold.get("myeongni_sidecar_count") or 0) >= 1


def test_weekly_l5_myeongni_kpi() -> None:
    if not WEEKLY.is_file():
        pytest.skip("weekly report missing")
    doc = json.loads(WEEKLY.read_text(encoding="utf-8-sig"))
    assert doc.get("version") == "1.5.0"
    l5 = doc.get("l5_myeongni_kpi")
    assert isinstance(l5, dict)
    assert l5.get("l5_myeongni_headline_ok") is True
    assert l5.get("non_gating") is True
