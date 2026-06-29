from __future__ import annotations

import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
P15_GATE = _ROOT / "docs/final/artifacts/sasang_rail_p15_gate_v1_latest.json"
EVAL_PATH = _ROOT / "docs/final/artifacts/sasang_joint_benchmark_eval_path_policy_gate_v1_latest.json"
EVAL_CHAIN = _ROOT / "reports/sasang_attested_only_eval_chain_v1_latest.json"
ARCHIVE_SNAP = _ROOT / "reports/sasang_dummy_archive_weekly_snapshot_v1_latest.json"
WEBHOOK_STUB = _ROOT / "reports/sasang_4agent_dual_probe_drift_webhook_stub_v1_latest.json"
CLINICAL = _ROOT / "docs/final/artifacts/sasang_commander_clinical_pending_gate_v1_latest.json"
POLICY = _ROOT / "docs/final/artifacts/sasang_joint_benchmark_eval_path_policy_v1.json"
PENDING = _ROOT / "data/myeongni/curated_commander_clinical_pending_v1.jsonl"
MAINLINE = _ROOT / "data/myeongni/sasang_saju_joint_benchmark_v1.jsonl"
MASTER = _ROOT / "docs/final/artifacts/sasang_rail_master_gate_v1_latest.json"
STUB_ID = "commander_attested_clinical_stub_v1"
DEID_ID = "commander_attested_clinical_deid_v1"


def test_p15_gate() -> None:
    if not P15_GATE.is_file():
        pytest.skip("p15 gate missing")
    gate = json.loads(P15_GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    assert gate.get("sasang_rail_p15_status") == "eval_path_locked_ok"
    assert gate.get("send_gate") == "HOLD"


def test_eval_path_policy() -> None:
    assert POLICY.is_file()
    pol = json.loads(POLICY.read_text(encoding="utf-8-sig"))
    assert "attested_only" in str(pol.get("default_eval_dataset") or "")
    if EVAL_PATH.is_file():
        doc = json.loads(EVAL_PATH.read_text(encoding="utf-8-sig"))
        assert doc.get("gate_ok") is True


def test_attested_eval_chain() -> None:
    if not EVAL_CHAIN.is_file():
        pytest.skip("eval chain report missing")
    doc = json.loads(EVAL_CHAIN.read_text(encoding="utf-8-sig"))
    assert doc.get("all_ok") is True


def test_archive_weekly_snapshot() -> None:
    if not ARCHIVE_SNAP.is_file():
        pytest.skip("archive snapshot missing")
    doc = json.loads(ARCHIVE_SNAP.read_text(encoding="utf-8-sig"))
    assert doc.get("snapshot_ok") is True
    assert int(doc.get("archive_rows") or 0) >= 3


def test_drift_webhook_stub() -> None:
    if not WEBHOOK_STUB.is_file():
        pytest.skip("webhook stub missing")
    doc = json.loads(WEBHOOK_STUB.read_text(encoding="utf-8-sig"))
    assert doc.get("stub_ok") is True
    assert doc.get("live_post_requested") is False


def test_clinical_stub_pending_not_mainline() -> None:
    p16 = _ROOT / "docs/final/artifacts/sasang_rail_p16_gate_v1_latest.json"
    if p16.is_file():
        pytest.skip("p16 ingested clinical row; see test_sasang_rail_p16_v1.py")
    assert PENDING.is_file()
    pending_ids = set()
    for line in PENDING.read_text(encoding="utf-8").splitlines():
        if line.strip():
            pending_ids.add(json.loads(line).get("person_id"))
    assert DEID_ID in pending_ids or "commander_attested_clinical_stub_v1" in pending_ids


def test_master_includes_p15() -> None:
    if not MASTER.is_file():
        pytest.skip("master gate missing")
    gate = json.loads(MASTER.read_text(encoding="utf-8-sig"))
    checks = gate.get("checks") or {}
    assert checks.get("p15_gate_ok", {}).get("passed") is True
