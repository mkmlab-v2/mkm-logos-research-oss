#!/usr/bin/env python3
"""24h watchdog for role-router limited-live operations (research-safe).

Checks key artifacts periodically and optionally triggers HOLD rollback on failure.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
REPORTS = ROOT / "reports"

DEFAULT_ENGINE = ART / "btc_limited_live_engine_input_from_role_router_latest.json"
DEFAULT_PREFLIGHT = ART / "role_router_engine_submit_preflight_v1_latest.json"
DEFAULT_BREAKER = ART / "role_router_circuit_breaker_rehearsal_v1_latest.json"
DEFAULT_LOG = REPORTS / "role_router_24h_watchdog_log.jsonl"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _health_status(engine: dict[str, Any] | None, preflight: dict[str, Any] | None, breaker: dict[str, Any] | None) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if not engine:
        reasons.append("engine_input_missing_or_invalid")
    else:
        if str(engine.get("status") or "") != "READY_FOR_ENGINE_SUBMIT":
            reasons.append("engine_status_not_ready")
        if str(engine.get("action") or "") != "submit_to_engine_queue":
            reasons.append("engine_action_not_submit")
        if not bool((engine.get("guards") or {}).get("candidate_tradable")):
            reasons.append("candidate_not_tradable")

    if not preflight or str(preflight.get("result") or "") != "PASS":
        reasons.append("preflight_not_pass")
    if not breaker or str(breaker.get("result") or "") != "PASS":
        reasons.append("breaker_rehearsal_not_pass")
    return len(reasons) == 0, reasons


def _trigger_hold_rollback(min_candidate_days: int) -> tuple[int, str]:
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "run_role_router_limited_live_engine_handoff_v1.py"),
        "--role-router-json",
        str(ART / "prophecy_role_router_multiscenario_opt_v1_latest.json"),
        "--min-candidate-days",
        str(min_candidate_days),
    ]
    res = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    output = (res.stdout or "") + (res.stderr or "")
    return int(res.returncode), output.strip()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--engine-input-json", type=Path, default=DEFAULT_ENGINE)
    ap.add_argument("--preflight-json", type=Path, default=DEFAULT_PREFLIGHT)
    ap.add_argument("--breaker-json", type=Path, default=DEFAULT_BREAKER)
    ap.add_argument("--duration-hours", type=float, default=24.0)
    ap.add_argument("--poll-seconds", type=int, default=300)
    ap.add_argument("--auto-rollback", action="store_true", help="Trigger HOLD rollback when health fails.")
    ap.add_argument("--min-candidate-days", type=int, default=20)
    ap.add_argument("--log-jsonl", type=Path, default=DEFAULT_LOG)
    args = ap.parse_args()

    deadline = time.time() + max(1.0, float(args.duration_hours) * 3600.0)
    poll = max(5, int(args.poll_seconds))
    rolled_back = False

    while True:
        now = _now()
        engine = _read(args.engine_input_json)
        preflight = _read(args.preflight_json)
        breaker = _read(args.breaker_json)
        ok, reasons = _health_status(engine, preflight, breaker)

        event: dict[str, Any] = {
            "ts_utc": now,
            "schema": "role_router_24h_watchdog_row_v1",
            "healthy": ok,
            "reasons": reasons,
            "engine_status": (engine or {}).get("status"),
            "preflight_result": (preflight or {}).get("result"),
            "breaker_result": (breaker or {}).get("result"),
            "auto_rollback_enabled": bool(args.auto_rollback),
            "auto_rollback_executed": False,
            "auto_rollback_rc": None,
        }

        if (not ok) and args.auto_rollback and (not rolled_back):
            rc, out = _trigger_hold_rollback(int(args.min_candidate_days))
            rolled_back = True
            event["auto_rollback_executed"] = True
            event["auto_rollback_rc"] = rc
            event["auto_rollback_output"] = out[-4000:] if out else ""

        _append_jsonl(args.log_jsonl, event)
        print(f"[{now}] healthy={ok} reasons={','.join(reasons) if reasons else 'none'}")

        if time.time() >= deadline:
            break
        time.sleep(poll)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
