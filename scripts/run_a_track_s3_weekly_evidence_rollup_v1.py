# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.8, L:0.7, K:0.6, M:0.6}
# Balance: 91
# Purpose: Roll up weekly S3 evidence and refresh A-track hold checklist.
# Keywords: track_a, s3, weekly, rollup, checklist
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRACKER = ROOT / "scripts" / "build_a_track_multiweek_stability_tracker_v1.py"
CHECKLIST = ROOT / "scripts" / "build_a_track_hold_release_checklist_v1.py"


def _run(cmd: list[str]) -> int:
    proc = subprocess.run(cmd, cwd=ROOT)
    return proc.returncode


def main() -> int:
    ap = argparse.ArgumentParser(description="Run Track A S3 weekly evidence rollup.")
    ap.add_argument(
        "--skip-increment",
        action="store_true",
        help="Do not increment weekly counter; only refresh artifacts.",
    )
    args = ap.parse_args()

    tracker_cmd = [sys.executable, str(TRACKER), "--out", "docs/final/artifacts/a_track_multiweek_stability_tracker_v1_latest.json"]
    if not args.skip_increment:
        tracker_cmd.append("--increment-week")
    rc = _run(tracker_cmd)
    if rc != 0:
        return rc

    checklist_cmd = [
        sys.executable,
        str(CHECKLIST),
        "--unlock-policy",
        "docs/final/artifacts/a_track_price_output_unlock_policy_v1_latest.json",
        "--approval-protocol",
        "docs/final/artifacts/a_track_operator_approval_protocol_v1_latest.json",
        "--hr-release-plan",
        "docs/final/artifacts/a_track_high_reliability_release_plan_v1_latest.json",
        "--policy-governance-decision",
        "docs/final/artifacts/a_track_policy_floor_governance_decision_v1_latest.json",
        "--multiweek-tracker",
        "docs/final/artifacts/a_track_multiweek_stability_tracker_v1_latest.json",
        "--out",
        "docs/final/artifacts/a_track_hold_release_checklist_v1_latest.json",
    ]
    return _run(checklist_cmd)


if __name__ == "__main__":
    raise SystemExit(main())
