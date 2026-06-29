"""RQ-028 Track C dashboard a_code_governor slice tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "reports/a_code_governor_evidence_pack_v1_latest.json"


@pytest.mark.skipif(not EVIDENCE.is_file(), reason="evidence pack missing")
def test_trackc_dashboard_includes_a_code_governor_slice() -> None:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_mkm_trackc_ops_dashboard_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    dash_path = ROOT / "docs/final/artifacts/mkm_trackc_ops_dashboard_latest.json"
    doc = json.loads(dash_path.read_text(encoding="utf-8"))
    ac = (doc.get("trackc") or {}).get("a_code_governor") or {}
    assert ac.get("role") == "a_code_governor_research_slice_v1"
    assert ac.get("research_only") is True
    assert ac.get("non_gating") is True
    assert ac.get("state") in {"OK", "NODATA"}
    if ac.get("state") == "OK":
        assert ac.get("gate_decision") in {"WATCH_CONTINUE", "HOLD_RESEARCH"}
        assert "operator_hint" in ac
        assert ac.get("human_signoff_status") in {"ABSENT", "PENDING", "APPROVED", "INVALID", None}
        assert "promotion_discussion_eligible" in ac
    evidence = doc.get("evidence") or {}
    assert "a_code_governor_evidence_pack" in evidence
