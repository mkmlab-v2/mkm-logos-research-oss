from __future__ import annotations

import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
P16_GATE = _ROOT / "docs/final/artifacts/sasang_rail_p16_gate_v1_latest.json"
ATTESTED_DRILL = _ROOT / "reports/sasang_attested_joint_promote_drill_v1_latest.json"
CLINICAL_INGEST = _ROOT / "docs/final/artifacts/sasang_commander_clinical_ingest_gate_v1_latest.json"
WEBHOOK_DRILL = _ROOT / "reports/sasang_dual_probe_drift_webhook_drill_v1_latest.json"
MAINLINE = _ROOT / "data/myeongni/sasang_saju_joint_benchmark_v1.jsonl"
MASTER = _ROOT / "docs/final/artifacts/sasang_rail_master_gate_v1_latest.json"
DEID_ID = "commander_attested_clinical_deid_v1"


def test_p16_gate() -> None:
    if not P16_GATE.is_file():
        pytest.skip("p16 gate missing")
    gate = json.loads(P16_GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    assert gate.get("sasang_rail_p16_status") == "promote_drill_attested_ok"
    assert gate.get("send_gate") == "HOLD"


def test_attested_promote_drill() -> None:
    if not ATTESTED_DRILL.is_file():
        pytest.skip("attested drill missing")
    doc = json.loads(ATTESTED_DRILL.read_text(encoding="utf-8-sig"))
    assert doc.get("all_ok") is True
    assert doc.get("promote_drill_mode") == "attested_default"


def test_clinical_deid_ingested() -> None:
    if not CLINICAL_INGEST.is_file():
        pytest.skip("clinical ingest gate missing")
    doc = json.loads(CLINICAL_INGEST.read_text(encoding="utf-8-sig"))
    assert doc.get("gate_ok") is True
    assert doc.get("clinical_ingest_status") == "ingested_ok"
    assert MAINLINE.is_file()
    ids = {
        json.loads(ln).get("person_id")
        for ln in MAINLINE.read_text(encoding="utf-8").splitlines()
        if ln.strip()
    }
    assert DEID_ID in ids


def test_drift_webhook_drill_dry_run() -> None:
    if not WEBHOOK_DRILL.is_file():
        pytest.skip("webhook drill missing")
    doc = json.loads(WEBHOOK_DRILL.read_text(encoding="utf-8-sig"))
    assert doc.get("drill_ok") is True
    assert doc.get("live_mode") is False


def test_master_includes_p16() -> None:
    if not MASTER.is_file():
        pytest.skip("master gate missing")
    gate = json.loads(MASTER.read_text(encoding="utf-8-sig"))
    checks = gate.get("checks") or {}
    assert checks.get("p16_gate_ok", {}).get("passed") is True
