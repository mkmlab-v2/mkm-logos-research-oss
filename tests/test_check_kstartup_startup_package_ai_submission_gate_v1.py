"""Regression: 340 submission gate blocks upload when human blockers todo."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "scripts/check_kstartup_startup_package_ai_submission_gate_v1.py"
CHECKLIST = ROOT / "docs/final/artifacts/startup_package_ai_2026_submission_checklist_v1_latest.json"


def test_submission_gate_fails_when_g0_todo() -> None:
    doc = json.loads(CHECKLIST.read_text(encoding="utf-8"))
    assert doc.get("ready_for_kstartup_upload") is False
    g0 = (doc.get("gates") or {}).get("G0_eligibility") or {}
    assert g0.get("status") == "todo"

    proc = subprocess.run(
        [sys.executable, str(GATE)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    assert "SUBMISSION_GATE FAIL" in proc.stdout


def test_submission_gate_draft_ok_exits_zero() -> None:
    proc = subprocess.run(
        [sys.executable, str(GATE), "--draft-ok"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
