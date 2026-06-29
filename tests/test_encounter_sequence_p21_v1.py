"""TKM encounter_sequence P21 gate smoke."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p21_gate_v1_latest.json"
MULTI = ROOT / "reports/encounter_sequence_multiturn_smoke_v1_latest.json"


def test_p21_gate() -> None:
    if not GATE.is_file():
        pytest.skip("p21 gate missing")
    gate = json.loads(GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    assert gate.get("tkm_encounter_sequence_p21_status") == "physician_gold_multiturn_ok"


def test_multiturn_smoke_artifact() -> None:
    if not MULTI.is_file():
        pytest.skip("multiturn smoke missing")
    doc = json.loads(MULTI.read_text(encoding="utf-8-sig"))
    assert doc.get("smoke_ok") is True
    assert int(doc.get("turn_count") or 0) >= 3
