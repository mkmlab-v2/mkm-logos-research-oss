"""TKM encounter_sequence P43 GPU+passive+curated observability gate smoke."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p43_gate_v1_latest.json"
ROLLUP = ROOT / "reports/tkm_encounter_sequence_p43_observability_rollup_v1_latest.json"
ARTIFACT = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p43_observability_rollup_v1_latest.json"
WEEKLY = ROOT / "reports/encounter_sequence_weekly_report_v1_latest.json"


def test_p43_gate() -> None:
    if not GATE.is_file():
        pytest.skip("p43 gate missing")
    gate = json.loads(GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    assert gate.get("tkm_encounter_sequence_p43_status") == "gpu_passive_curated_observation_wire_ok"
    assert gate.get("send_gate") == "HOLD"


def test_p43_observability_rollup() -> None:
    if not ROLLUP.is_file():
        pytest.skip("p43 observability rollup missing")
    doc = json.loads(ROLLUP.read_text(encoding="utf-8-sig"))
    assert doc.get("observability_ok") is True
    assert doc.get("passive_observation_ok") is True
    assert doc.get("interpret_cpu_guard_ok") is True
    assert doc.get("curated_review_mark_ok") is True
    assert int((doc.get("curated_review_counts") or {}).get("reviewed") or 0) >= 1
    assert doc.get("auto_training_forbidden") is True
    assert ARTIFACT.is_file()


def test_weekly_p43_observability_sync() -> None:
    if not WEEKLY.is_file():
        pytest.skip("weekly report missing")
    doc = json.loads(WEEKLY.read_text(encoding="utf-8-sig"))
    assert doc.get("version") in ("2.9.0", "3.0.0", "3.1.0")
    ob = doc.get("p43_observability_kpi")
    assert isinstance(ob, dict)
    assert ob.get("p43_observability_headline_ok") is True
