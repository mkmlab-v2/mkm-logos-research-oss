"""TKM encounter_sequence P61 grand-stack extension export bundle gate smoke."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p61_gate_v1_latest.json"
BUNDLE = ROOT / "reports/tkm_encounter_sequence_grand_stack_extension_export_bundle_v1_latest.json"
ARTIFACT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_grand_stack_extension_export_bundle_v1_latest.json"
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"


def test_p61_gate() -> None:
    if not GATE.is_file():
        pytest.skip("p61 gate missing")
    gate = json.loads(GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    assert gate.get("tkm_encounter_sequence_p61_status") == "grand_stack_extension_export_bundle_wire_ok"
    assert gate.get("send_gate") == "HOLD"


def test_grand_stack_extension_export_bundle() -> None:
    if not BUNDLE.is_file():
        pytest.skip("grand stack extension export bundle missing")
    doc = json.loads(BUNDLE.read_text(encoding="utf-8-sig"))
    assert doc.get("grand_stack_extension_export_bundle_ok") is True
    assert int(doc.get("gates_ok_count") or 0) >= 28
    assert doc.get("post_export_extended_export_bundle_ok") is True
    assert doc.get("full_grand_stack_final_closure_ok") is True
    snap = doc.get("rollup_snapshot") if isinstance(doc.get("rollup_snapshot"), dict) else {}
    assert snap.get("grand_export_bundle_vault_sync_ok") is True
    assert snap.get("post_grand_passive_observation_ok") is True
    assert snap.get("full_grand_stack_final_closure_ok") is True
    assert ARTIFACT.is_file()


def test_weekly_grand_stack_extension_bundle_sync() -> None:
    if not WEEKLY.is_file():
        pytest.skip("weekly report missing")
    doc = json.loads(WEEKLY.read_text(encoding="utf-8-sig"))
    assert doc.get("version") in ("4.7.0", "4.8.0", "4.9.0")
    gseb = doc.get("grand_stack_extension_export_bundle_kpi")
    assert isinstance(gseb, dict)
    assert gseb.get("grand_stack_extension_export_headline_ok") is True
