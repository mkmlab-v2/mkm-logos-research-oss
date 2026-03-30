#!/usr/bin/env python3
"""One-shot local runner: verify -> apply -> evaluate -> lock -> regression check."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _run(cmd: list[str]) -> None:
    print(f"[run] {' '.join(cmd)}")
    proc = subprocess.run(cmd, cwd=ROOT)
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)


def main() -> int:
    ap = argparse.ArgumentParser(description="Run B-Track verified-only gate and lock in one shot")
    ap.add_argument("--python", default=sys.executable, help="Python executable")
    args = ap.parse_args()

    py = args.python

    # 1) Ensure slots are promoted from CROSS_REF alignment.
    _run([py, "scripts/update_btrack_anchor_evidence.py"])

    # 2) Verify evidence slots (verified-only subset).
    _run([py, "scripts/verify_btrack_anchor_evidence.py"])

    # 3) Apply verified-only slots to B-track bench.
    _run(
        [
            py,
            "scripts/apply_btrack_anchor_evidence.py",
            "--slots",
            "data/logos/btrack_pilot/bench/btrack_anchor_evidence_slots_verified.jsonl",
            "--out-b",
            "data/logos/btrack_pilot/bench/b_track_eval_anchor_verified_only.jsonl",
        ]
    )

    # 4) Recompute quality/gate.
    _run(
        [
            py,
            "scripts/collect_btrack_quality_metrics.py",
            "--b",
            "data/logos/btrack_pilot/bench/b_track_eval_anchor_verified_only.jsonl",
            "--out",
            "reports/constitution/btrack_pilot/btrack_quality_anchor_verified_only_latest.json",
            "--details-out",
            "reports/constitution/btrack_pilot/btrack_pair_details_anchor_verified_only_latest.jsonl",
        ]
    )
    _run(
        [
            py,
            "scripts/evaluate_btrack_promotion_gate.py",
            "--report",
            "reports/constitution/btrack_pilot/btrack_quality_anchor_verified_only_latest.json",
            "--out",
            "reports/constitution/btrack_pilot/btrack_promotion_gate_anchor_verified_only_latest.json",
        ]
    )

    # 5) Lock baseline and run regression check.
    _run([py, "scripts/lock_btrack_verified_baseline.py"])
    _run([py, "scripts/check_btrack_regression.py"])

    print("OK: B-Track one-shot gate+lock completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
