# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.9, L:0.8, K:0.7, M:0.4}
# Balance: 91
# Purpose: Orchestrate live trading health checks and emit unified status JSON.
# Keywords: ops, health, orchestrator, powershell, runtime
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[4]
OPS_DIR = ROOT / "projects" / "bitcoin-trading" / "ops" / "windows-rehearsal"
MEM_V2_OPS = ROOT / "projects" / "bitcoin-trading" / "memory" / "v2" / "ops"

HEALTH_PS1 = OPS_DIR / "check_live_trading_health.ps1"
BLOCKERS_PS1 = OPS_DIR / "diagnose_live_trading_blockers.ps1"
NOFILL_PS1 = OPS_DIR / "check_no_fill_stall_alert.ps1"
RECOVER_PS1 = OPS_DIR / "recover_live_trading_stack.ps1"

HEALTH_JSON = MEM_V2_OPS / "live_trading_health_latest.json"
BLOCKERS_JSON = MEM_V2_OPS / "live_trading_blockers_latest.json"
NOFILL_JSON = MEM_V2_OPS / "live_trading_nofill_alert_latest.json"

DEFAULT_OUT = MEM_V2_OPS / "live_ops_orchestrator_latest.json"


@dataclass
class StepResult:
    step: str
    script: str
    exit_code: int
    ok: bool
    stdout: str
    stderr: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_ps1(script_path: Path) -> StepResult:
    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script_path),
    ]
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=False,
    )
    return StepResult(
        step=script_path.stem,
        script=str(script_path),
        exit_code=int(proc.returncode),
        ok=proc.returncode == 0,
        stdout=(proc.stdout or "").strip(),
        stderr=(proc.stderr or "").strip(),
    )


def _run_nofill_ps1(script_path: Path, warn_minutes: int | None = None) -> StepResult:
    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script_path),
    ]
    if warn_minutes is not None:
        cmd.extend(["-WarnMinutes", str(int(warn_minutes))])
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=False,
    )
    return StepResult(
        step=script_path.stem,
        script=str(script_path),
        exit_code=int(proc.returncode),
        ok=proc.returncode == 0,
        stdout=(proc.stdout or "").strip(),
        stderr=(proc.stderr or "").strip(),
    )


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"missing": True, "path": str(path)}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        return {"parse_error": str(exc), "path": str(path)}


def main() -> int:
    ap = argparse.ArgumentParser(description="Run live ops health orchestrator.")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--auto-recover-on-nofill",
        action="store_true",
        help="If no-fill warns, run one recovery cycle and re-check all steps.",
    )
    ap.add_argument(
        "--nofill-warn-minutes",
        type=int,
        default=None,
        help="Override no-fill warning window minutes for check_no_fill_stall_alert.ps1",
    )
    ap.add_argument(
        "--allow-stale-window-warning",
        action="store_true",
        help="Treat nofill reason=trade_window_stale as warning-only (does not fail all_green).",
    )
    args = ap.parse_args()

    steps = [
        _run_ps1(HEALTH_PS1),
        _run_ps1(BLOCKERS_PS1),
        _run_nofill_ps1(NOFILL_PS1, warn_minutes=args.nofill_warn_minutes),
    ]

    recovery_triggered = False
    recovery_result: StepResult | None = None
    if args.auto_recover_on_nofill and steps[-1].exit_code != 0:
        recovery_triggered = True
        recovery_result = _run_ps1(RECOVER_PS1)
        post_steps = [
            _run_ps1(HEALTH_PS1),
            _run_ps1(BLOCKERS_PS1),
            _run_nofill_ps1(NOFILL_PS1, warn_minutes=args.nofill_warn_minutes),
        ]
        steps.extend(post_steps)

    health = _read_json(HEALTH_JSON)
    blockers = _read_json(BLOCKERS_JSON)
    nofill = _read_json(NOFILL_JSON)
    nofill_warn = bool(nofill.get("warn")) if isinstance(nofill, dict) else None
    nofill_reason = str(nofill.get("reason") or "") if isinstance(nofill, dict) else ""
    # Evaluate effective step state from the latest check cycle.
    # If recovery ran, use the second triad; otherwise use the initial triad.
    latest_health_ok = bool(steps[3].ok) if recovery_triggered and len(steps) >= 6 else bool(steps[0].ok)
    latest_blockers_ok = bool(steps[4].ok) if recovery_triggered and len(steps) >= 6 else bool(steps[1].ok)
    latest_nofill_ok = bool(steps[5].ok) if recovery_triggered and len(steps) >= 6 else bool(steps[2].ok)
    effective_nofill_ok = latest_nofill_ok
    if (
        args.allow_stale_window_warning
        and nofill_warn
        and nofill_reason == "trade_window_stale"
    ):
        effective_nofill_ok = True

    all_green = bool(latest_health_ok and latest_blockers_ok and effective_nofill_ok)

    blocker_count = len(blockers.get("blockers") or []) if isinstance(blockers, dict) else None
    payload = {
        "schema": "live_ops_orchestrator_v1",
        "generated_at_utc": _utc_now(),
        "all_green": bool(all_green),
        "summary": {
            "daemon_running": bool(health.get("daemon_running")) if isinstance(health, dict) else None,
            "trading_enabled": bool(health.get("trading_enabled")) if isinstance(health, dict) else None,
            "testnet": health.get("testnet") if isinstance(health, dict) else None,
            "blocker_count": blocker_count,
            "nofill_warn": nofill_warn,
            "nofill_reason": nofill_reason or None,
            "effective_nofill_ok": effective_nofill_ok,
        },
        "step_results": [
            {
                "step": s.step,
                "script": s.script,
                "exit_code": s.exit_code,
                "ok": s.ok,
                "stdout": s.stdout,
                "stderr": s.stderr,
            }
            for s in steps
        ],
        "auto_recovery": {
            "enabled": bool(args.auto_recover_on_nofill),
            "triggered": bool(recovery_triggered),
            "recovery_step": (
                {
                    "step": recovery_result.step,
                    "script": recovery_result.script,
                    "exit_code": recovery_result.exit_code,
                    "ok": recovery_result.ok,
                    "stdout": recovery_result.stdout,
                    "stderr": recovery_result.stderr,
                }
                if recovery_result is not None
                else None
            ),
        },
        "policy": {
            "nofill_warn_minutes": args.nofill_warn_minutes,
            "allow_stale_window_warning": bool(args.allow_stale_window_warning),
        },
        "artifacts": {
            "health": health,
            "blockers": blockers,
            "nofill": nofill,
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"WROTE: {args.out}")
    print(f"all_green={payload['all_green']}")
    print(
        "daemon_running={0}, trading_enabled={1}, blocker_count={2}, nofill_warn={3}".format(
            payload["summary"]["daemon_running"],
            payload["summary"]["trading_enabled"],
            payload["summary"]["blocker_count"],
            payload["summary"]["nofill_warn"],
        )
    )
    return 0 if all_green else 1


if __name__ == "__main__":
    raise SystemExit(main())
