from __future__ import annotations

import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
P11_GATE = _ROOT / "docs/final/artifacts/sasang_rail_p11_gate_v1_latest.json"
TIMESERIES = _ROOT / "docs/final/artifacts/sasang_4agent_collision_btrack_protocol_timeseries_kospi_latest.json"
REBALANCE = _ROOT / "reports/sasang_joint_benchmark_dummy_rebalance_v1_latest.json"
ENRICH = _ROOT / "reports/sasang_literature_auto_enrich_refresh_chain_v1_latest.json"
MASTER = _ROOT / "docs/final/artifacts/sasang_rail_master_gate_v1_latest.json"


def test_p11_gate() -> None:
    if not P11_GATE.is_file():
        pytest.skip("p11 gate missing")
    gate = json.loads(P11_GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    assert gate.get("sasang_rail_p11_status") == "dual_probe_enrich_ok"
    assert gate.get("send_gate") == "HOLD"


def test_timeseries_kospi_protocol() -> None:
    if not TIMESERIES.is_file():
        pytest.skip("timeseries protocol missing")
    doc = json.loads(TIMESERIES.read_text(encoding="utf-8-sig"))
    exp = doc.get("experiment") or {}
    assert exp.get("data_mode") == "timeseries_file_adapter"
    assert int(exp.get("ticks") or 0) >= 40


def test_dummy_rebalance() -> None:
    if not REBALANCE.is_file():
        pytest.skip("rebalance report missing")
    doc = json.loads(REBALANCE.read_text(encoding="utf-8-sig"))
    assert doc.get("rebalance_ok") is True
    assert int(doc.get("rows_non_dummy") or 0) >= 5


def test_literature_enrich_refresh() -> None:
    if not ENRICH.is_file():
        pytest.skip("enrich refresh missing")
    doc = json.loads(ENRICH.read_text(encoding="utf-8-sig"))
    assert doc.get("all_ok") is True


def test_master_includes_p11() -> None:
    if not MASTER.is_file():
        pytest.skip("master gate missing")
    gate = json.loads(MASTER.read_text(encoding="utf-8-sig"))
    checks = gate.get("checks") or {}
    assert checks.get("p11_gate_ok", {}).get("passed") is True
