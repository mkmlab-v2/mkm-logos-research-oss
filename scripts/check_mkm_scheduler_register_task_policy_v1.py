#!/usr/bin/env python3
"""Validate mkm_scheduler_solo_core_stack_v1 register_task_policy_v1 contract (offline)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--workspace-root",
        default=str(Path(__file__).resolve().parents[1]),
    )
    args = parser.parse_args()
    root = Path(args.workspace_root)
    stack_path = root / "docs" / "final" / "artifacts" / "mkm_scheduler_solo_core_stack_v1.json"
    if not stack_path.is_file():
        print(f"MISSING: {stack_path}", file=sys.stderr)
        return 1

    stack = json.loads(stack_path.read_text(encoding="utf-8"))
    if stack.get("schema") != "mkm_scheduler_solo_core_stack_v1":
        print("FAIL: schema mismatch", file=sys.stderr)
        return 1

    policy = stack.get("register_task_policy_v1")
    if not isinstance(policy, dict):
        print("FAIL: register_task_policy_v1 missing", file=sys.stderr)
        return 1

    if policy.get("default_state") != "Disabled":
        print("FAIL: default_state must be Disabled", file=sys.stderr)
        return 1
    if not policy.get("require_ssot_tier_before_enable_ready"):
        print("FAIL: require_ssot_tier_before_enable_ready must be true", file=sys.stderr)
        return 1

    allowed = policy.get("allowed_tier_keys")
    if not isinstance(allowed, list) or not allowed:
        print("FAIL: allowed_tier_keys empty", file=sys.stderr)
        return 1

    for key in allowed:
        if key not in stack or not isinstance(stack[key], list):
            print(f"FAIL: tier key missing or not a list: {key}", file=sys.stderr)
            return 1

    band = stack.get("solo_target_ready_band")
    if not isinstance(band, dict) or "min" not in band or "max" not in band:
        print("FAIL: solo_target_ready_band incomplete", file=sys.stderr)
        return 1

    audit_ps1 = root / "scripts" / "Invoke-MkmSchedulerSoloCoreStackAudit_v1.ps1"
    if not audit_ps1.is_file():
        print(f"MISSING: {audit_ps1}", file=sys.stderr)
        return 1
    body = audit_ps1.read_text(encoding="utf-8")
    if "EnforceSoloBand" not in body:
        print("FAIL: audit script missing EnforceSoloBand", file=sys.stderr)
        return 1

    member_ps1 = root / "scripts" / "Test-MkmSoloCoreStackTaskMembership_v1.ps1"
    if not member_ps1.is_file():
        print(f"MISSING: {member_ps1}", file=sys.stderr)
        return 1

    # Fail-closed Ready path must exist on high-churn register scripts.
    for rel in (
        "scripts/Register-MkmContextCoordScheduledRemeasureWeeklyTask.ps1",
        "scripts/Register-MkmAutonomousPatrolDailyTask.ps1",
    ):
        p = root / rel
        if not p.is_file():
            print(f"MISSING: {rel}", file=sys.stderr)
            return 1
        text = p.read_text(encoding="utf-8")
        if "FAIL-CLOSED" not in text or "StartReady" not in text:
            print(f"FAIL: {rel} missing FAIL-CLOSED/-StartReady SSOT gate", file=sys.stderr)
            return 1
        if "Test-MkmSoloCoreStackTaskMembership_v1.ps1" not in text:
            print(f"FAIL: {rel} missing membership helper wiring", file=sys.stderr)
            return 1

    print("OK: register_task_policy_v1 + band SSOT contract + Ready fail-closed helpers")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
