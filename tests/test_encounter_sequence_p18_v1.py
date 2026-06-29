"""TKM encounter_sequence P18 gate smoke."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "docs/final/artifacts/tkm_encounter_sequence_p18_gate_v1_latest.json"
ACK = ROOT / "docs/final/artifacts/encounter_sequence_curated_learning_human_gate_ack_v1.json"
SMOKE = ROOT / "reports/intake_fusion_encounter_sequence_smoke_v1_latest.json"


def test_p18_gate() -> None:
    if not GATE.is_file():
        pytest.skip("p18 gate missing")
    gate = json.loads(GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    assert gate.get("tkm_encounter_sequence_p18_status") == "intake_l0_weekly_ok"


def test_curated_ack_artifact() -> None:
    if not ACK.is_file():
        pytest.skip("curated ack missing")
    ack = json.loads(ACK.read_text(encoding="utf-8-sig"))
    assert ack.get("human_gate_ack") is True
    assert ack.get("send_gate") == "HOLD"


def test_intake_fusion_smoke_artifact() -> None:
    if not SMOKE.is_file():
        pytest.skip("intake smoke missing")
    doc = json.loads(SMOKE.read_text(encoding="utf-8-sig"))
    assert doc.get("smoke_ok") is True
    assert doc.get("l0_in_markdown") is True
