#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _spawn(cmd: list[str]) -> subprocess.Popen[bytes]:
    return subprocess.Popen(cmd, cwd=str(ROOT))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline-runs", type=int, default=20)
    ap.add_argument("--live-runs", type=int, default=20)
    ap.add_argument("--execute-guard", action="store_true")
    ap.add_argument("--guard-samples", type=int, default=1)
    args = ap.parse_args()

    offline_cmd = [
        sys.executable,
        "scripts/run_e2e_memory_proof_offline_ab_v1.py",
        "--runs",
        str(max(1, args.offline_runs)),
    ]
    live_cmd = [
        sys.executable,
        "scripts/run_e2e_memory_proof_live_ab_v1.py",
        "--runs",
        str(max(1, args.live_runs)),
        "--guard-samples",
        str(max(1, args.guard_samples)),
    ]
    if args.execute_guard:
        live_cmd.append("--execute-guard")

    p_offline = _spawn(offline_cmd)
    p_live = _spawn(live_cmd)
    rc_offline = p_offline.wait()
    rc_live = p_live.wait()
    if rc_offline != 0:
        return rc_offline
    if rc_live != 0:
        return rc_live

    for step in [
        [sys.executable, "scripts/aggregate_e2e_memory_proof_stats_v1.py"],
        [sys.executable, "scripts/build_e2e_memory_proof_b2b_pack_v1.py"],
    ]:
        rc = subprocess.run(step, cwd=str(ROOT), check=False).returncode
        if rc != 0:
            return rc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
