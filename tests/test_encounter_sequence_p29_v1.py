"""TKM encounter_sequence P29 L0 router wire gate smoke."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p29_gate_v1_latest.json"
L0_KPI = ROOT / "reports/tkm_encounter_sequence_l0_kpi_v1_latest.json"
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"


def test_p29_gate() -> None:
    if not GATE.is_file():
        pytest.skip("p29 gate missing")
    gate = json.loads(GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    assert gate.get("tkm_encounter_sequence_p29_status") == "l0_router_wire_ok"


def test_l0_kpi_artifact() -> None:
    if not L0_KPI.is_file():
        pytest.skip("l0 kpi missing")
    doc = json.loads(L0_KPI.read_text(encoding="utf-8-sig"))
    assert doc.get("kpi_ok") is True
    ledger = doc.get("all_ledger")
    assert isinstance(ledger, dict)
    assert int(ledger.get("l0_router_wired_count") or 0) >= 1
    assert int(ledger.get("l0_summary_trigger_events") or 0) >= 1


def test_weekly_l0_safety_kpi() -> None:
    if not WEEKLY.is_file():
        pytest.skip("weekly report missing")
    doc = json.loads(WEEKLY.read_text(encoding="utf-8-sig"))
    assert doc.get("version") in ("1.6.0", "1.7.0", "1.8.0", "1.9.0", "2.0.0", "2.1.0", "2.2.0", "2.3.0", "2.4.0", "5.4.0", "5.5.0", "5.6.0")
    l0 = doc.get("l0_safety_kpi")
    assert isinstance(l0, dict)
    assert l0.get("l0_safety_headline_ok") is True
    assert l0.get("non_gating") is True


def test_clinic_convert_attaches_l0_router() -> None:
    import importlib.util

    fixture = ROOT / "tests/fixtures/clinic_constitution_mvp_capture_v1.example.json"
    if not fixture.is_file():
        pytest.skip("clinic fixture missing")
    capture = json.loads(fixture.read_text(encoding="utf-8-sig"))
    capture["physician_constitution"]["notes"] = "severe_abdominal_pain reported; physician review."
    convert_path = ROOT / "scripts/convert_clinic_capture_to_encounter_sequence_v1.py"
    spec = importlib.util.spec_from_file_location("convert", convert_path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    doc = mod.convert_capture(capture, sequence_id="SEQ-P29-L0-TEST")
    assert isinstance(doc.get("l0_router_events"), list)
    assert doc["l0_router_events"][0]["triggered"] is True
    assert "severe_abdominal_pain" in (doc["l0_router_events"][0].get("keyword_hits") or [])
