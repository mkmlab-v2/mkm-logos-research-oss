"""TKM encounter_sequence P41 clinical validation stub gate smoke."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p41_gate_v1_latest.json"
STUB = ROOT / "reports/tkm_encounter_sequence_clinical_validation_stub_v1_latest.json"
ARTIFACT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_clinical_validation_stub_v1_latest.json"
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"


def test_p41_gate() -> None:
    if not GATE.is_file():
        pytest.skip("p41 gate missing")
    gate = json.loads(GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    assert gate.get("tkm_encounter_sequence_p41_status") == "clinical_validation_stub_wire_ok"
    assert gate.get("send_gate") == "HOLD"
    assert gate.get("research_only") is True


def test_clinical_validation_stub() -> None:
    if not STUB.is_file():
        pytest.skip("clinical validation stub missing")
    doc = json.loads(STUB.read_text(encoding="utf-8-sig"))
    assert doc.get("validation_stub_ok") is True
    assert doc.get("boundary_contract_pass_rate") == 1.0
    assert (doc.get("physician_closure_pass_rate") or 0) >= 0.5
    assert (doc.get("lens_stack_wired_rate") or 0) >= 0.75
    assert int(doc.get("physician_gold_sequence_count") or 0) >= 3
    assert ARTIFACT.is_file()


def test_weekly_clinical_stub_sync() -> None:
    if not WEEKLY.is_file():
        pytest.skip("weekly report missing")
    doc = json.loads(WEEKLY.read_text(encoding="utf-8-sig"))
    assert doc.get("version") in ("2.7.0", "2.8.0", "2.9.0")
    cv = doc.get("clinical_validation_stub_kpi")
    assert isinstance(cv, dict)
    assert cv.get("clinical_validation_headline_ok") is True
