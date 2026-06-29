"""TKM encounter_sequence P39 lens stack rollup gate smoke."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p39_gate_v1_latest.json"
ROLLUP = ROOT / "reports/tkm_encounter_sequence_lens_stack_rollup_v1_latest.json"
ARTIFACT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_lens_stack_rollup_v1_latest.json"
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"


def test_p39_gate() -> None:
    if not GATE.is_file():
        pytest.skip("p39 gate missing")
    gate = json.loads(GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    assert gate.get("tkm_encounter_sequence_p39_status") == "lens_stack_rollup_wire_ok"
    assert gate.get("send_gate") == "HOLD"


def test_lens_stack_rollup() -> None:
    if not ROLLUP.is_file():
        pytest.skip("lens stack rollup missing")
    doc = json.loads(ROLLUP.read_text(encoding="utf-8-sig"))
    assert doc.get("rollup_ok") is True
    gates = doc.get("gates") if isinstance(doc.get("gates"), dict) else {}
    for key in ("p33", "p34", "p35", "p36", "p37", "p38"):
        assert (gates.get(key) or {}).get("gate_ok") is True
    assert ARTIFACT.is_file()


def test_weekly_lens_stack_rollup_sync() -> None:
    if not WEEKLY.is_file():
        pytest.skip("weekly report missing")
    doc = json.loads(WEEKLY.read_text(encoding="utf-8-sig"))
    assert doc.get("version") in ("2.5.0", "2.6.0", "2.7.0")
    lr = doc.get("lens_stack_rollup_kpi")
    assert isinstance(lr, dict)
    assert lr.get("lens_stack_rollup_headline_ok") is True
