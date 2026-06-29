from __future__ import annotations

import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
P12_GATE = _ROOT / "docs/final/artifacts/sasang_rail_p12_gate_v1_latest.json"
COMPARE = _ROOT / "reports/sasang_4agent_dual_probe_compare_v1_latest.json"
PARTITION = _ROOT / "reports/sasang_joint_benchmark_tier_partition_v1_latest.json"
P5_CHAIN = _ROOT / "reports/sasang_rail_p5_chain_v1_latest.json"
MASTER = _ROOT / "docs/final/artifacts/sasang_rail_master_gate_v1_latest.json"


def test_p12_gate() -> None:
    if not P12_GATE.is_file():
        pytest.skip("p12 gate missing")
    gate = json.loads(P12_GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    assert gate.get("sasang_rail_p12_status") == "partition_compare_ok"
    assert gate.get("send_gate") == "HOLD"


def test_dual_probe_compare() -> None:
    if not COMPARE.is_file():
        pytest.skip("compare report missing")
    doc = json.loads(COMPARE.read_text(encoding="utf-8-sig"))
    assert doc.get("compare_ok") is True
    assert doc.get("real_slice", {}).get("data_mode") == "real_slice_backtest_adapter"
    assert doc.get("timeseries_kospi", {}).get("data_mode") == "timeseries_file_adapter"


def test_tier_partition() -> None:
    if not PARTITION.is_file():
        pytest.skip("partition report missing")
    doc = json.loads(PARTITION.read_text(encoding="utf-8-sig"))
    assert doc.get("partition_ok") is True
    assert int(doc.get("attested_tier", {}).get("count") or 0) >= 5


def test_p5_enrich_wired() -> None:
    if not P5_CHAIN.is_file():
        pytest.skip("p5 chain missing")
    chain = json.loads(P5_CHAIN.read_text(encoding="utf-8-sig"))
    scripts = {str(s.get("script") or "") for s in chain.get("steps") or []}
    assert "auto_enrich_sasang_from_literature_stub_v1.py" in scripts
    assert "run_sasang_literature_supervised_chain_v1.py" in scripts


def test_master_includes_p12() -> None:
    if not MASTER.is_file():
        pytest.skip("master gate missing")
    gate = json.loads(MASTER.read_text(encoding="utf-8-sig"))
    checks = gate.get("checks") or {}
    assert checks.get("p12_gate_ok", {}).get("passed") is True
