#!/usr/bin/env python3
"""Run 24h watchdog chain for lens-combo limited-live payload."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
REPORTS = ROOT / "reports"

DEFAULT_ENGINE = ART / "btc_limited_live_engine_input_from_lens_combo_latest.json"
DEFAULT_PREFLIGHT = ART / "lens_combo_engine_submit_preflight_v1_latest.json"
DEFAULT_BREAKER = ART / "lens_combo_circuit_breaker_rehearsal_v1_latest.json"
DEFAULT_LOG = REPORTS / "lens_combo_24h_watchdog_log.jsonl"


def _run(cmd: list[str]) -> int:
    return int(subprocess.run(cmd, cwd=str(ROOT)).returncode)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--engine-input-json", type=Path, default=DEFAULT_ENGINE)
    ap.add_argument("--preflight-json", type=Path, default=DEFAULT_PREFLIGHT)
    ap.add_argument("--breaker-json", type=Path, default=DEFAULT_BREAKER)
    ap.add_argument("--duration-hours", type=float, default=24.0)
    ap.add_argument("--poll-seconds", type=int, default=300)
    ap.add_argument("--auto-rollback", action="store_true")
    ap.add_argument("--min-candidate-days", type=int, default=20)
    ap.add_argument("--log-jsonl", type=Path, default=DEFAULT_LOG)
    args = ap.parse_args()

    # Always regenerate breaker artifact against the current lens payload.
    rc_breaker = _run(
        [
            sys.executable,
            str(ROOT / "scripts" / "run_role_router_circuit_breaker_rehearsal_v1.py"),
            "--engine-input-json",
            str(args.engine_input_json),
            "--out",
            str(args.breaker_json),
        ]
    )
    if rc_breaker != 0:
        return rc_breaker

    cmd_watchdog = [
        sys.executable,
        str(ROOT / "scripts" / "run_role_router_24h_watchdog_v1.py"),
        "--engine-input-json",
        str(args.engine_input_json),
        "--preflight-json",
        str(args.preflight_json),
        "--breaker-json",
        str(args.breaker_json),
        "--duration-hours",
        str(args.duration_hours),
        "--poll-seconds",
        str(args.poll_seconds),
        "--min-candidate-days",
        str(args.min_candidate_days),
        "--log-jsonl",
        str(args.log_jsonl),
    ]
    if args.auto_rollback:
        cmd_watchdog.append("--auto-rollback")
    return _run(cmd_watchdog)


if __name__ == "__main__":
    raise SystemExit(main())

