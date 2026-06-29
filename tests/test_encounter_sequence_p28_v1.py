"""TKM encounter_sequence P28 gate smoke."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p28_gate_v1_latest.json"
CROSS = ROOT / "reports/tkm_encounter_sequence_myeongni_cross_refresh_v1_latest.json"
MYEONGNI_KPI = ROOT / "reports/tkm_encounter_sequence_myeongni_kpi_v1_latest.json"
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"


def test_p28_gate() -> None:
    if not GATE.is_file():
        pytest.skip("p28 gate missing")
    gate = json.loads(GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    assert gate.get("tkm_encounter_sequence_p28_status") == "myeongni_cross_check_ok"


def test_cross_refresh_artifact() -> None:
    if not CROSS.is_file():
        pytest.skip("cross refresh missing")
    doc = json.loads(CROSS.read_text(encoding="utf-8-sig"))
    assert doc.get("ok") is True
    assert int(doc.get("cross_check_computed_count") or 0) >= 1


def test_myeongni_kpi_cross_computed() -> None:
    if not MYEONGNI_KPI.is_file():
        pytest.skip("myeongni kpi missing")
    doc = json.loads(MYEONGNI_KPI.read_text(encoding="utf-8-sig"))
    assert doc.get("kpi_ok") is True
    ledger = doc.get("all_ledger")
    assert isinstance(ledger, dict)
    assert int(ledger.get("cross_check_computed_count") or 0) >= 1


def test_weekly_l5_cross_check() -> None:
    if not WEEKLY.is_file():
        pytest.skip("weekly report missing")
    doc = json.loads(WEEKLY.read_text(encoding="utf-8-sig"))
    assert doc.get("version") in ("1.6.0", "1.7.0", "1.8.0", "1.9.0", "2.0.0", "2.1.0", "2.2.0", "2.3.0", "2.4.0", "5.4.0", "5.5.0", "5.6.0")
    l5 = doc.get("l5_myeongni_kpi")
    assert isinstance(l5, dict)
    assert l5.get("l5_myeongni_headline_ok") is True
    assert int(l5.get("cross_check_computed_count") or 0) >= 1


def test_romanized_sasang_label_cross_check() -> None:
    from scripts.core.patient_intake_myeongni_sasang_cross_v1 import assess_myeongni_sasang_cross

    report = {
        "structure_analysis": {
            "element_profile": {
                "element_counts_visible": {"목": 1, "화": 0, "토": 2, "금": 1, "수": 2}
            }
        },
        "day_master": {"stem_element_hint": "수(陽)"},
    }
    doc = assess_myeongni_sasang_cross(report, "soeum")
    assert doc["constitution_id"] == "soeum_in"
    assert doc["status"] in ("match", "partial", "mismatch", "insufficient")
