from __future__ import annotations

import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
P13_GATE = _ROOT / "docs/final/artifacts/sasang_rail_p13_gate_v1_latest.json"
ARCHIVE = _ROOT / "reports/sasang_joint_benchmark_dummy_archive_export_v1_latest.json"
SNAPSHOT = _ROOT / "reports/sasang_joint_benchmark_attested_only_snapshot_v1_latest.json"
DRIFT = _ROOT / "reports/sasang_4agent_dual_probe_drift_v1_latest.json"
ABLATION = _ROOT / "reports/sasang_4agent_dual_probe_ablation_v1_latest.json"
ARCHIVE_JSONL = _ROOT / "data/myeongni/sasang_saju_joint_benchmark_dummy_archive_v1.jsonl"
MASTER = _ROOT / "docs/final/artifacts/sasang_rail_master_gate_v1_latest.json"


def test_p13_gate() -> None:
    if not P13_GATE.is_file():
        pytest.skip("p13 gate missing")
    gate = json.loads(P13_GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    assert gate.get("sasang_rail_p13_status") == "archive_drift_ok"
    assert gate.get("send_gate") == "HOLD"


def test_dummy_archive_export() -> None:
    if not ARCHIVE.is_file():
        pytest.skip("archive export missing")
    doc = json.loads(ARCHIVE.read_text(encoding="utf-8-sig"))
    assert doc.get("export_ok") is True
    assert int(doc.get("dummy_rows_exported") or 0) >= 1
    assert ARCHIVE_JSONL.is_file()


def test_attested_snapshot() -> None:
    if not SNAPSHOT.is_file():
        pytest.skip("snapshot missing")
    doc = json.loads(SNAPSHOT.read_text(encoding="utf-8-sig"))
    assert doc.get("snapshot_ok") is True
    assert len(doc.get("commander_attested_ids") or []) >= 1


def test_dual_probe_drift() -> None:
    if not DRIFT.is_file():
        pytest.skip("drift report missing")
    doc = json.loads(DRIFT.read_text(encoding="utf-8-sig"))
    assert doc.get("drift_ok") is True


def test_dual_probe_ablation() -> None:
    if not ABLATION.is_file():
        pytest.skip("ablation missing")
    doc = json.loads(ABLATION.read_text(encoding="utf-8-sig"))
    assert doc.get("all_ok") is True
    assert doc.get("compare_ok") is True


def test_master_includes_p13() -> None:
    if not MASTER.is_file():
        pytest.skip("master gate missing")
    gate = json.loads(MASTER.read_text(encoding="utf-8-sig"))
    checks = gate.get("checks") or {}
    assert checks.get("p13_gate_ok", {}).get("passed") is True
