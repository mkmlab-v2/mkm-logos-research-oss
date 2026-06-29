from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STACK = ROOT / "docs" / "final" / "artifacts" / "mkm_scheduler_solo_core_stack_v1.json"
AUDIT_PS1 = ROOT / "scripts" / "Invoke-MkmSchedulerSoloCoreStackAudit_v1.ps1"
AUDIT_JSON = ROOT / "reports" / "mkm_scheduler_solo_core_stack_audit_v1_latest.json"
POLICY_PY = ROOT / "scripts" / "check_mkm_scheduler_register_task_policy_v1.py"


def test_stack_ssot_has_register_policy_and_band() -> None:
    doc = json.loads(STACK.read_text(encoding="utf-8"))
    assert doc.get("schema") == "mkm_scheduler_solo_core_stack_v1"
    policy = doc.get("register_task_policy_v1") or {}
    assert policy.get("default_state") == "Disabled"
    assert policy.get("require_ssot_tier_before_enable_ready") is True
    band = doc.get("solo_target_ready_band") or {}
    assert isinstance(band.get("min"), int)
    assert isinstance(band.get("max"), int)
    assert band["min"] <= band["max"]


def test_register_task_policy_checker_exit_zero() -> None:
    r = subprocess.run(
        [sys.executable, str(POLICY_PY)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert r.returncode == 0, r.stderr + r.stdout


def test_band_gate_enforce_smoke() -> None:
    assert AUDIT_PS1.is_file()
    r = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(AUDIT_PS1),
            "-WorkspaceRoot",
            str(ROOT),
            "-EnforceSoloBand",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    assert AUDIT_JSON.is_file()
    audit = json.loads(AUDIT_JSON.read_text(encoding="utf-8-sig"))
    assert audit.get("schema") == "mkm_scheduler_solo_core_stack_audit_v1"
    band = audit.get("band_gate") or {}
    assert band.get("ok") is True
    assert band.get("enforce") is True
    assert int(band.get("unauthorized_ready_count", 1)) == 0
    counts = audit.get("counts") or {}
    solo = int(counts.get("solo_stack_ready", 0))
    assert band["band_min"] <= solo <= band["band_max"]
