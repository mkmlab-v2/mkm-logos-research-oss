from __future__ import annotations

import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
P14_GATE = _ROOT / "docs/final/artifacts/sasang_rail_p14_gate_v1_latest.json"
PRUNE = _ROOT / "reports/sasang_joint_benchmark_mainline_prune_v1_latest.json"
CLASS_GATE = _ROOT / "docs/final/artifacts/sasang_attested_only_classification_gate_v1_latest.json"
CLINICAL = _ROOT / "docs/final/artifacts/sasang_commander_attested_clinical_template_gate_v1_latest.json"
ALERT = _ROOT / "reports/sasang_4agent_dual_probe_weekly_drift_alert_v1_latest.json"
BENCH = _ROOT / "data/myeongni/sasang_saju_joint_benchmark_v1.jsonl"
ARCHIVE = _ROOT / "data/myeongni/sasang_saju_joint_benchmark_dummy_archive_v1.jsonl"
MASTER = _ROOT / "docs/final/artifacts/sasang_rail_master_gate_v1_latest.json"


def _is_dummy_line(line: str) -> bool:
    row = json.loads(line)
    pid = str(row.get("person_id") or "").lower()
    disp = str(row.get("display_name") or "")
    return "dummy" in pid or "[dummy]" in disp.lower() or "DUMMYCSV" in pid or "DUMMYJSONL" in pid


def test_p14_gate() -> None:
    if not P14_GATE.is_file():
        pytest.skip("p14 gate missing")
    gate = json.loads(P14_GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    assert gate.get("sasang_rail_p14_status") == "mainline_eval_ok"
    assert gate.get("send_gate") == "HOLD"


def test_mainline_pruned() -> None:
    if not PRUNE.is_file():
        pytest.skip("prune report missing")
    doc = json.loads(PRUNE.read_text(encoding="utf-8-sig"))
    assert doc.get("prune_ok") is True
    assert doc.get("applied") is True or doc.get("already_pruned") is True
    if BENCH.is_file():
        dummies = [ln for ln in BENCH.read_text(encoding="utf-8").splitlines() if ln.strip() and _is_dummy_line(ln)]
        assert len(dummies) == 0


def test_dummy_archive_preserved() -> None:
    assert ARCHIVE.is_file()
    rows = [ln for ln in ARCHIVE.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(rows) >= 1


def test_attested_classification_gate() -> None:
    if not CLASS_GATE.is_file():
        pytest.skip("classification gate missing")
    doc = json.loads(CLASS_GATE.read_text(encoding="utf-8-sig"))
    assert doc.get("gate_ok") is True


def test_clinical_template_gate() -> None:
    if not CLINICAL.is_file():
        pytest.skip("clinical template gate missing")
    doc = json.loads(CLINICAL.read_text(encoding="utf-8-sig"))
    assert doc.get("gate_ok") is True


def test_weekly_drift_alert() -> None:
    if not ALERT.is_file():
        pytest.skip("drift alert missing")
    doc = json.loads(ALERT.read_text(encoding="utf-8-sig"))
    assert doc.get("alert_ok") is True


def test_master_includes_p14() -> None:
    if not MASTER.is_file():
        pytest.skip("master gate missing")
    gate = json.loads(MASTER.read_text(encoding="utf-8-sig"))
    checks = gate.get("checks") or {}
    assert checks.get("p14_gate_ok", {}).get("passed") is True
