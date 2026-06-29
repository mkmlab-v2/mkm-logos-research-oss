"""RQ-029 promotion checklist readiness tests."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/check_a_code_promotion_checklist_readiness_v1.py"
CHECKLIST = ROOT / "experiments/a_code_12ai_v2/specs/a_code_promotion_checklist_v1.json"
GATE = ROOT / "reports/a_code_governor_promotion_gate_v1_latest.json"


def _load_module():
    spec = importlib.util.spec_from_file_location("a_code_checklist", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_checklist_schema_present() -> None:
    doc = json.loads(CHECKLIST.read_text(encoding="utf-8"))
    assert doc.get("schema") == "a_code_promotion_checklist_v1"
    assert doc.get("parent_rq") == "RQ-028"
    assert len(doc.get("items") or []) >= 5


@pytest.mark.skipif(not GATE.is_file(), reason="gate artifact missing")
def test_readiness_mechanical_ready_when_gate_ok() -> None:
    mod = _load_module()
    checklist = json.loads(CHECKLIST.read_text(encoding="utf-8"))
    evidence = mod._read(ROOT / "reports/a_code_governor_evidence_pack_v1_latest.json")
    gate = mod._read(GATE)
    replay = mod._read(ROOT / "reports/a_code_governor_knob_multiday_replay_v1_latest.json")
    report = mod.evaluate_readiness(
        checklist=checklist,
        evidence=evidence,
        gate=gate,
        replay=replay,
        run_pytest=False,
    )
    assert report.get("schema") == "a_code_promotion_checklist_readiness_v1"
    assert report["summary"]["gate_decision"] in {"WATCH_CONTINUE", "HOLD_RESEARCH", None}
    if gate.get("summary", {}).get("decision") == "WATCH_CONTINUE" and evidence.get("status") == "WATCH":
        assert report["summary"]["mechanical_ready"] is True
    assert report["summary"].get("human_signoff_status") in {"ABSENT", "PENDING", "APPROVED", "INVALID", None}
    assert report["summary"].get("promotion_discussion_eligible") is False or (
        report["summary"].get("mechanical_ready") is True
        and report["summary"].get("human_signoff_status") == "APPROVED"
    )


def test_readiness_cli_writes_json(tmp_path: Path) -> None:
    if not GATE.is_file():
        pytest.skip("gate artifact missing")
    out = tmp_path / "ready.json"
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--out", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert "items" in doc
    assert "mechanical_ready" in doc.get("summary", {})
