"""TKM encounter_sequence P37 ops closure v2 gate smoke."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p37_gate_v1_latest.json"
OPS = ROOT / "reports/tkm_encounter_sequence_ops_closure_v1_latest.json"
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"


def test_p37_gate() -> None:
    if not GATE.is_file():
        pytest.skip("p37 gate missing")
    gate = json.loads(GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    assert gate.get("tkm_encounter_sequence_p37_status") == "ops_closure_v2_wire_ok"
    assert gate.get("send_gate") == "HOLD"


def test_ops_closure_v2() -> None:
    if not OPS.is_file():
        pytest.skip("ops closure missing")
    doc = json.loads(OPS.read_text(encoding="utf-8-sig"))
    assert doc.get("version") in ("2.0.0", "2.1.0")
    assert doc.get("closure_ok") is True
    assert doc.get("full_stack_closure_ok") is True
    items = doc.get("items")
    assert isinstance(items, dict)
    for key in (
        "9_cross_lens_p33",
        "10_passive_observation_p34",
        "11_conflict_resolver_p35",
        "12_disagreement_cross_p36",
    ):
        assert (items.get(key) or {}).get("ok") is True


def test_weekly_ops_closure_sync() -> None:
    if not WEEKLY.is_file():
        pytest.skip("weekly report missing")
    doc = json.loads(WEEKLY.read_text(encoding="utf-8-sig"))
    assert doc.get("version") in ("2.3.0", "2.4.0", "2.5.0", "2.6.0")
    oc = doc.get("ops_closure_kpi")
    assert isinstance(oc, dict)
    assert oc.get("full_stack_closure_headline_ok") is True
