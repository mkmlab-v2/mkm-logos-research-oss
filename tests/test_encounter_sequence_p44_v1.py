"""TKM encounter_sequence P44 stack final closure gate smoke."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p44_gate_v1_latest.json"
CLOSURE = ROOT / "reports/tkm_encounter_sequence_stack_final_closure_v1_latest.json"
ARTIFACT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_stack_final_closure_v1_latest.json"
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"


def test_p44_gate() -> None:
    if not GATE.is_file():
        pytest.skip("p44 gate missing")
    gate = json.loads(GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    assert gate.get("tkm_encounter_sequence_p44_status") == "stack_final_closure_wire_ok"
    assert gate.get("send_gate") == "HOLD"


def test_stack_final_closure() -> None:
    if not CLOSURE.is_file():
        pytest.skip("stack final closure missing")
    doc = json.loads(CLOSURE.read_text(encoding="utf-8-sig"))
    assert doc.get("final_closure_ok") is True
    assert int(doc.get("gates_ok_count") or 0) >= 11
    assert doc.get("export_bundle_ok") is True
    assert doc.get("observability_ok") is True
    assert int(doc.get("curated_reviewed_count") or 0) >= 1
    assert ARTIFACT.is_file()


def test_weekly_final_closure_sync() -> None:
    if not WEEKLY.is_file():
        pytest.skip("weekly report missing")
    doc = json.loads(WEEKLY.read_text(encoding="utf-8-sig"))
    assert doc.get("version") in ("3.0.0", "3.1.0", "3.2.0", "3.3.0", "3.4.0")
    fc = doc.get("stack_final_closure_kpi")
    assert isinstance(fc, dict)
    assert fc.get("stack_final_closure_headline_ok") is True
