"""Contract: Sunday automation LastResult audit script."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "Invoke-CheckSundayAutomationLastResult_v1.ps1"
REGISTER = ROOT / "scripts" / "Register-SundayAutomationAuditTask_v1.ps1"


def test_sunday_audit_script_contract() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert "sunday_automation_audit_v1" in text
    assert "MKM-BTrack-RecommendedEval-AutoSweep-Weekly" in text
    assert "prophecy_hit_rate_ssot_pointer_v1_latest.json" in text
    assert "stale_last_run" in text
    assert "AlsoVerifyHeadlineLane" in text


def test_register_sunday_audit_task_contract() -> None:
    text = REGISTER.read_text(encoding="utf-8")
    assert "MKM-Sunday-Automation-LastResult-Audit" in text
    assert "Invoke-CheckSundayAutomationLastResult_v1.ps1" in text
