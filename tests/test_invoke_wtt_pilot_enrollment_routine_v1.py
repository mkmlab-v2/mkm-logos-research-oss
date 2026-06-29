"""Invoke-WttPilotEnrollmentRoutine_v1.ps1 smoke."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PS1 = ROOT / "scripts/Invoke-WttPilotEnrollmentRoutine_v1.ps1"


def test_enrollment_routine_auto() -> None:
    proc = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(PS1),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=180,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    checklist = ROOT / "docs/final/artifacts/wtt_pilot_enrollment_checklist_v1_latest.json"
    gate = ROOT / "reports/wtt_human_n30_gate_v1_latest.json"
    stub = ROOT / "data/wtt/examples/wtt_customer_masked_stub_v1.example.jsonl"
    assert checklist.is_file()
    assert gate.is_file()
    assert stub.is_file()
    doc = json.loads(checklist.read_text(encoding="utf-8"))
    assert doc["human_n30_gate_met"] is False
    assert doc["enrollment_ready"] is True
