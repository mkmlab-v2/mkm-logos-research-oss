"""TKM encounter_sequence P22 gate smoke."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p22_gate_v1_latest.json"
HTTP = ROOT / "reports/no1kmedi_encounter_sequence_api_http_smoke_v1_latest.json"


def test_p22_gate() -> None:
    if not GATE.is_file():
        pytest.skip("p22 gate missing")
    gate = json.loads(GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    assert gate.get("tkm_encounter_sequence_p22_status") == "live_api_weekly_churn_ok"


def test_http_smoke_artifact() -> None:
    if not HTTP.is_file():
        pytest.skip("http smoke artifact missing")
    doc = json.loads(HTTP.read_text(encoding="utf-8-sig"))
    assert doc.get("http_smoke_ok") is True
