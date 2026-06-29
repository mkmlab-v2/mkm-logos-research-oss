"""TKM encounter_sequence P40 passive integrated observation gate smoke."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p40_gate_v1_latest.json"
ROLLUP = ROOT / "reports/tkm_encounter_sequence_passive_integrated_rollup_v1_latest.json"
ARTIFACT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_passive_integrated_rollup_v1_latest.json"
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"


def test_p40_gate() -> None:
    if not GATE.is_file():
        pytest.skip("p40 gate missing")
    gate = json.loads(GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    assert gate.get("tkm_encounter_sequence_p40_status") == "passive_integrated_observation_wire_ok"
    assert gate.get("send_gate") == "HOLD"


def test_passive_integrated_rollup() -> None:
    if not ROLLUP.is_file():
        pytest.skip("passive integrated rollup missing")
    doc = json.loads(ROLLUP.read_text(encoding="utf-8-sig"))
    assert doc.get("integrated_ok") is True
    assert doc.get("passive_observation_ok") is True
    assert doc.get("interpret_cpu_guard_ok") is True
    assert doc.get("curated_learning_ack_ok") is True
    assert int(doc.get("curated_learning_registry_row_count") or 0) >= 1
    assert ARTIFACT.is_file()


def test_weekly_passive_integrated_sync() -> None:
    if not WEEKLY.is_file():
        pytest.skip("weekly report missing")
    doc = json.loads(WEEKLY.read_text(encoding="utf-8-sig"))
    assert doc.get("version") in ("2.6.0", "2.7.0", "2.8.0")
    pi = doc.get("passive_integrated_rollup_kpi")
    assert isinstance(pi, dict)
    assert pi.get("passive_integrated_headline_ok") is True
