"""TKM encounter_sequence P20 gate smoke."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p20_gate_v1_latest.json"
DUAL = ROOT / "reports/tkm_clinic_encounter_dual_lane_summary_v1_latest.json"
API = ROOT / "reports/encounter_sequence_clinician_api_e2e_smoke_v1_latest.json"


def test_p20_gate() -> None:
    if not GATE.is_file():
        pytest.skip("p20 gate missing")
    gate = json.loads(GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    assert gate.get("tkm_encounter_sequence_p20_status") == "api_e2e_dummy_separated_ok"


def test_dual_lane_summary() -> None:
    if not DUAL.is_file():
        pytest.skip("dual lane summary missing")
    doc = json.loads(DUAL.read_text(encoding="utf-8-sig"))
    assert doc.get("dual_lane_ok") is True
    gold = doc.get("physician_gold_only") or {}
    assert int(gold.get("clinic_capture_count") or 0) >= 1


def test_api_route_file() -> None:
    route = ROOT / "projects/no1kmedi/src/app/api/clinician/encounter-sequence-v1/route.ts"
    assert route.is_file()


def test_api_smoke_artifact() -> None:
    if not API.is_file():
        pytest.skip("api smoke missing")
    doc = json.loads(API.read_text(encoding="utf-8-sig"))
    assert doc.get("smoke_ok") is True
