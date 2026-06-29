"""TKM encounter_sequence P47 stack extension closure gate smoke."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p47_gate_v1_latest.json"
CLOSURE = ROOT / "reports/tkm_encounter_sequence_stack_extension_closure_v1_latest.json"
ARTIFACT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_stack_extension_closure_v1_latest.json"
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"


def test_p47_gate() -> None:
    if not GATE.is_file():
        pytest.skip("p47 gate missing")
    gate = json.loads(GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    assert gate.get("tkm_encounter_sequence_p47_status") == "stack_extension_closure_wire_ok"
    assert gate.get("send_gate") == "HOLD"


def test_stack_extension_closure() -> None:
    if not CLOSURE.is_file():
        pytest.skip("stack extension closure missing")
    doc = json.loads(CLOSURE.read_text(encoding="utf-8-sig"))
    assert doc.get("extension_closure_ok") is True
    assert int(doc.get("gates_ok_count") or 0) >= 14
    assert doc.get("stack_final_closure_ok") is True
    assert doc.get("curated_milestone_ok") is True
    assert doc.get("gpu_interpret_observation_ok") is True
    assert ARTIFACT.is_file()


def test_weekly_extension_closure_sync() -> None:
    if not WEEKLY.is_file():
        pytest.skip("weekly report missing")
    doc = json.loads(WEEKLY.read_text(encoding="utf-8-sig"))
    assert doc.get("version") in ("3.3.0", "3.4.0", "3.5.0")
    ec = doc.get("stack_extension_closure_kpi")
    assert isinstance(ec, dict)
    assert ec.get("stack_extension_closure_headline_ok") is True
