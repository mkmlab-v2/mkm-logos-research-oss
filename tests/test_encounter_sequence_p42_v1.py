"""TKM encounter_sequence P42 full-stack export bundle gate smoke."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p42_gate_v1_latest.json"
BUNDLE = ROOT / "reports/tkm_encounter_sequence_full_stack_export_bundle_v1_latest.json"
ARTIFACT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_full_stack_export_bundle_v1_latest.json"
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"


def test_p42_gate() -> None:
    if not GATE.is_file():
        pytest.skip("p42 gate missing")
    gate = json.loads(GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    assert gate.get("tkm_encounter_sequence_p42_status") == "full_stack_export_bundle_wire_ok"
    assert gate.get("send_gate") == "HOLD"


def test_full_stack_export_bundle() -> None:
    if not BUNDLE.is_file():
        pytest.skip("export bundle missing")
    doc = json.loads(BUNDLE.read_text(encoding="utf-8-sig"))
    assert doc.get("export_bundle_ok") is True
    gates = doc.get("gates") if isinstance(doc.get("gates"), dict) else {}
    for key in ("p33", "p34", "p35", "p36", "p37", "p38", "p39", "p40", "p41"):
        assert (gates.get(key) or {}).get("gate_ok") is True
    snap = doc.get("rollup_snapshot") if isinstance(doc.get("rollup_snapshot"), dict) else {}
    assert snap.get("lens_stack_rollup_ok") is True
    assert snap.get("passive_integrated_ok") is True
    assert snap.get("clinical_validation_stub_ok") is True
    assert ARTIFACT.is_file()


def test_weekly_export_bundle_sync() -> None:
    if not WEEKLY.is_file():
        pytest.skip("weekly report missing")
    doc = json.loads(WEEKLY.read_text(encoding="utf-8-sig"))
    assert doc.get("version") in ("2.8.0", "2.9.0", "3.0.0")
    fb = doc.get("full_stack_export_bundle_kpi")
    assert isinstance(fb, dict)
    assert fb.get("full_stack_export_headline_ok") is True
