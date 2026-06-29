"""TKM encounter_sequence P46 GPU+Interpret observability gate smoke."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p46_gate_v1_latest.json"
OBS = ROOT / "reports/tkm_encounter_sequence_gpu_interpret_observation_v1_latest.json"
ARTIFACT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_gpu_interpret_observation_v1_latest.json"
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"


def test_p46_gate() -> None:
    if not GATE.is_file():
        pytest.skip("p46 gate missing")
    gate = json.loads(GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    assert gate.get("tkm_encounter_sequence_p46_status") == "gpu_interpret_observation_wire_ok"
    assert gate.get("send_gate") == "HOLD"


def test_gpu_interpret_observation() -> None:
    if not OBS.is_file():
        pytest.skip("gpu interpret observation missing")
    doc = json.loads(OBS.read_text(encoding="utf-8-sig"))
    assert doc.get("observation_ok") is True
    assert doc.get("interpret_cpu_guard_ok") is True
    assert doc.get("passive_observation_ok") is True
    assert doc.get("curated_milestone_ok") is True
    assert ARTIFACT.is_file()


def test_weekly_gpu_interpret_sync() -> None:
    if not WEEKLY.is_file():
        pytest.skip("weekly report missing")
    doc = json.loads(WEEKLY.read_text(encoding="utf-8-sig"))
    assert doc.get("version") in ("3.3.0", "3.4.0", "3.5.0")
    gio = doc.get("gpu_interpret_observation_kpi")
    assert isinstance(gio, dict)
    assert gio.get("gpu_interpret_observation_headline_ok") is True
