from __future__ import annotations

import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
P10_GATE = _ROOT / "docs/final/artifacts/sasang_rail_p10_gate_v1_latest.json"
REAL_SLICE = _ROOT / "docs/final/artifacts/sasang_4agent_collision_btrack_protocol_real_slice_latest.json"
CLASS_SMOKE = _ROOT / "reports/sasang_joint_benchmark_non_dummy_classification_smoke_v1_latest.json"
MASTER = _ROOT / "docs/final/artifacts/sasang_rail_master_gate_v1_latest.json"


def test_p10_gate() -> None:
    if not P10_GATE.is_file():
        pytest.skip("p10 gate missing")
    gate = json.loads(P10_GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    assert gate.get("sasang_rail_p10_status") == "exploratory_probe_ok"
    assert gate.get("send_gate") == "HOLD"


def test_real_slice_protocol() -> None:
    if not REAL_SLICE.is_file():
        pytest.skip("real slice protocol missing")
    doc = json.loads(REAL_SLICE.read_text(encoding="utf-8-sig"))
    exp = doc.get("experiment") or {}
    assert doc.get("schema") == "sasang_4agent_collision_btrack_protocol_v1"
    assert exp.get("data_mode") == "real_slice_backtest_adapter"
    hint = doc.get("promotion_gate_hint") or {}
    assert hint.get("decision") != "GO_CANDIDATE"


def test_non_dummy_classification_smoke() -> None:
    if not CLASS_SMOKE.is_file():
        pytest.skip("classification smoke missing")
    doc = json.loads(CLASS_SMOKE.read_text(encoding="utf-8-sig"))
    assert doc.get("classification_ok") is True
    assert int(doc.get("rows_non_dummy") or 0) >= 1


def test_master_includes_p10() -> None:
    if not MASTER.is_file():
        pytest.skip("master gate missing")
    gate = json.loads(MASTER.read_text(encoding="utf-8-sig"))
    checks = gate.get("checks") or {}
    assert checks.get("p10_gate_ok", {}).get("passed") is True
    assert gate.get("send_gate") == "HOLD"
