"""TKM encounter_sequence P34 passive observation + interpret micro gate smoke."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p34_gate_v1_latest.json"
PASSIVE = ROOT / "reports/tkm_encounter_sequence_passive_observation_v1_latest.json"
CROSS = ROOT / "reports/tkm_encounter_sequence_cross_lens_kpi_v1_latest.json"
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"
INTERPRET = ROOT / "reports/myeongri_interpret_micro_retrain_chain_v1_latest.json"


def test_p34_gate() -> None:
    if not GATE.is_file():
        pytest.skip("p34 gate missing")
    gate = json.loads(GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    assert gate.get("tkm_encounter_sequence_p34_status") == "passive_observation_wire_ok"
    assert gate.get("send_gate") == "HOLD"


def test_passive_observation() -> None:
    if not PASSIVE.is_file():
        pytest.skip("passive observation missing")
    doc = json.loads(PASSIVE.read_text(encoding="utf-8-sig"))
    assert doc.get("observation_ok") is True
    assert doc.get("non_gating") is True
    assert doc.get("interpret_cpu_guard_ok") is True
    assert doc.get("motif_skew_gate_ok") is True


def test_cross_lens_motif_skew() -> None:
    if not CROSS.is_file():
        pytest.skip("cross lens kpi missing")
    doc = json.loads(CROSS.read_text(encoding="utf-8-sig"))
    assert doc.get("version") == "1.1.0"
    assert doc.get("motif_skew_gate_ok") is True
    share = doc.get("motif_top1_share")
    assert isinstance(share, (int, float))
    assert float(share) < 0.65


def test_interpret_micro_cpu_guard() -> None:
    if not INTERPRET.is_file():
        pytest.skip("interpret micro chain missing")
    doc = json.loads(INTERPRET.read_text(encoding="utf-8-sig"))
    assert doc.get("cpu_guard_ok") is True
    assert doc.get("send_gate") == "HOLD"


def test_weekly_passive_observation_sync() -> None:
    if not WEEKLY.is_file():
        pytest.skip("weekly report missing")
    doc = json.loads(WEEKLY.read_text(encoding="utf-8-sig"))
    assert doc.get("version") in ("2.0.0", "2.1.0", "2.2.0", "2.3.0", "2.4.0", "5.4.0", "5.5.0", "5.6.0")
    passive = doc.get("passive_observation_kpi")
    assert isinstance(passive, dict)
    assert passive.get("observation_ok") is True
    l7 = doc.get("l7_cross_lens_kpi")
    assert isinstance(l7, dict)
    assert l7.get("motif_skew_gate_ok") is True
