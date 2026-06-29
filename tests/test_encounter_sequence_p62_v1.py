"""TKM encounter_sequence P62 grand-stack stack closure gate smoke."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p62_gate_v1_latest.json"
CLOSURE = ROOT / "reports/tkm_encounter_sequence_grand_stack_stack_closure_v1_latest.json"
ARTIFACT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_grand_stack_stack_closure_v1_latest.json"
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"


def test_p62_gate() -> None:
    if not GATE.is_file():
        pytest.skip("p62 gate missing")
    gate = json.loads(GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    assert gate.get("tkm_encounter_sequence_p62_status") == "grand_stack_stack_closure_wire_ok"
    assert gate.get("send_gate") == "HOLD"


def test_grand_stack_stack_closure() -> None:
    if not CLOSURE.is_file():
        pytest.skip("grand stack stack closure missing")
    doc = json.loads(CLOSURE.read_text(encoding="utf-8-sig"))
    assert doc.get("grand_stack_stack_closure_ok") is True
    assert int(doc.get("gates_ok_count") or 0) >= 5
    assert doc.get("grand_post_export_closure_ok") is True
    assert doc.get("grand_export_bundle_vault_sync_ok") is True
    assert doc.get("post_grand_passive_observation_ok") is True
    assert doc.get("full_grand_stack_final_closure_ok") is True
    assert doc.get("grand_stack_extension_export_bundle_ok") is True
    assert ARTIFACT.is_file()


def test_weekly_grand_stack_stack_closure_sync() -> None:
    if not WEEKLY.is_file():
        pytest.skip("weekly report missing")
    doc = json.loads(WEEKLY.read_text(encoding="utf-8-sig"))
    assert doc.get("version") in ("4.8.0", "4.9.0", "5.0.0")
    gssc = doc.get("grand_stack_stack_closure_kpi")
    assert isinstance(gssc, dict)
    assert gssc.get("grand_stack_stack_closure_headline_ok") is True
