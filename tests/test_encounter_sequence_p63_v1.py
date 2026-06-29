"""TKM encounter_sequence P63 ultra-grand post-export closure gate smoke."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p63_gate_v1_latest.json"
CLOSURE = ROOT / "reports/tkm_encounter_sequence_ultra_grand_post_export_closure_v1_latest.json"
ARTIFACT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_ultra_grand_post_export_closure_v1_latest.json"
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"


def test_p63_gate() -> None:
    if not GATE.is_file():
        pytest.skip("p63 gate missing")
    gate = json.loads(GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    assert gate.get("tkm_encounter_sequence_p63_status") == "ultra_grand_post_export_closure_wire_ok"
    assert gate.get("send_gate") == "HOLD"


def test_ultra_grand_post_export_closure() -> None:
    if not CLOSURE.is_file():
        pytest.skip("ultra grand post export closure missing")
    doc = json.loads(CLOSURE.read_text(encoding="utf-8-sig"))
    assert doc.get("ultra_grand_post_export_closure_ok") is True
    assert int(doc.get("gates_ok_count") or 0) >= 30
    assert doc.get("grand_stack_stack_closure_ok") is True
    assert doc.get("grand_stack_extension_export_bundle_ok") is True
    assert doc.get("full_grand_stack_final_closure_ok") is True
    assert doc.get("grand_post_export_closure_ok") is True
    assert doc.get("post_export_stack_closure_ok") is True
    assert doc.get("full_extension_closure_ok") is True
    assert doc.get("integrated_closure_ok") is True
    assert ARTIFACT.is_file()


def test_weekly_ultra_grand_post_export_sync() -> None:
    if not WEEKLY.is_file():
        pytest.skip("weekly report missing")
    doc = json.loads(WEEKLY.read_text(encoding="utf-8-sig"))
    assert doc.get("version") in ("4.9.0", "5.0.0", "5.1.0")
    ugpec = doc.get("ultra_grand_post_export_closure_kpi")
    assert isinstance(ugpec, dict)
    assert ugpec.get("ultra_grand_post_export_closure_headline_ok") is True
