"""RQ-031 promotion RQ readiness tests."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_a_code_promotion_rq_readiness_v1.py"
DRAFT = ROOT / "experiments/a_code_12ai_v2/specs/a_code_promotion_rq_draft_v1.json"
CHECKLIST = ROOT / "reports/a_code_promotion_checklist_readiness_v1_latest.json"


def _load_module():
    spec = importlib.util.spec_from_file_location("a_code_promotion_rq_readiness", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_draft_schema_present() -> None:
    doc = json.loads(DRAFT.read_text(encoding="utf-8"))
    assert doc.get("schema") == "a_code_promotion_rq_draft_v1"
    assert doc.get("rq_id") == "RQ-031"
    assert doc.get("track_a_auto_promotion") is False


@pytest.mark.skipif(not CHECKLIST.is_file(), reason="checklist artifact missing")
def test_readiness_discussion_ready_when_eligible() -> None:
    mod = _load_module()
    draft = json.loads(DRAFT.read_text(encoding="utf-8"))
    checklist = mod._read(CHECKLIST)
    report = mod.build_readiness(
        draft=draft,
        checklist=checklist,
        evidence=mod._read(ROOT / "reports/a_code_governor_evidence_pack_v1_latest.json"),
        gate=mod._read(ROOT / "reports/a_code_governor_promotion_gate_v1_latest.json"),
    )
    assert report.get("schema") == "a_code_promotion_rq_readiness_v1"
    if checklist.get("summary", {}).get("promotion_discussion_eligible") is True:
        assert report["summary"]["discussion_ready"] is True
    assert report["summary"]["operator_lane_ready"] is False or report["ack"].get("acknowledged") is True


def test_readiness_cli_writes_json(tmp_path: Path) -> None:
    if not CHECKLIST.is_file():
        pytest.skip("checklist artifact missing")
    out = tmp_path / "rq031.json"
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--out", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert "discussion_ready" in doc.get("summary", {})
