"""TKM encounter_sequence P48 extended stack export bundle gate smoke."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p48_gate_v1_latest.json"
BUNDLE = ROOT / "reports/tkm_encounter_sequence_extended_stack_export_bundle_v1_latest.json"
ARTIFACT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_extended_stack_export_bundle_v1_latest.json"
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"


def test_p48_gate() -> None:
    if not GATE.is_file():
        pytest.skip("p48 gate missing")
    gate = json.loads(GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    assert gate.get("tkm_encounter_sequence_p48_status") == "extended_stack_export_bundle_wire_ok"
    assert gate.get("send_gate") == "HOLD"


def test_extended_stack_export_bundle() -> None:
    if not BUNDLE.is_file():
        pytest.skip("extended stack export bundle missing")
    doc = json.loads(BUNDLE.read_text(encoding="utf-8-sig"))
    assert doc.get("extended_export_bundle_ok") is True
    assert int(doc.get("gates_ok_count") or 0) >= 15
    assert doc.get("base_export_bundle_ok") is True
    assert doc.get("extension_closure_ok") is True
    snap = doc.get("rollup_snapshot") if isinstance(doc.get("rollup_snapshot"), dict) else {}
    assert snap.get("curated_milestone_ok") is True
    assert snap.get("gpu_interpret_observation_ok") is True
    assert ARTIFACT.is_file()


def test_weekly_extended_bundle_sync() -> None:
    if not WEEKLY.is_file():
        pytest.skip("weekly report missing")
    doc = json.loads(WEEKLY.read_text(encoding="utf-8-sig"))
    assert doc.get("version") in ("3.4.0", "3.5.0", "3.6.0")
    eb = doc.get("extended_stack_export_bundle_kpi")
    assert isinstance(eb, dict)
    assert eb.get("extended_stack_export_headline_ok") is True
