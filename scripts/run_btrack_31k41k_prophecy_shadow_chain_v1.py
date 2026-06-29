#!/usr/bin/env python3
"""One-shot B-track 31k/41k shadow chain (timeseries_v2 panel + v2b_strict SSOT).

Runbooks:
  --daily-fast     KPI-B refresh skipped (default)
  --weekly-full    KPI-B refresh before panel
  --allowlist-review  second gate pass requiring human signoff file
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOLD_STRICT = "docs/final/artifacts/btrack_31k41k_prophecy_shadow_fold_stability_v2b_strict_v1_latest.json"
FOLD_MAX = "docs/final/artifacts/btrack_31k41k_prophecy_shadow_fold_stability_v1_latest.json"


def _run(cmd: list[str]) -> int:
    print("+", " ".join(cmd))
    return subprocess.run(cmd, cwd=str(ROOT)).returncode


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--daily-fast",
        action="store_true",
        help="Skip KPI-B refresh (default runbook).",
    )
    ap.add_argument(
        "--weekly-full",
        action="store_true",
        help="Run KPI-B refresh before shadow panel (mutually exclusive with --daily-fast).",
    )
    ap.add_argument(
        "--skip-kpi-b-refresh",
        action="store_true",
        help="Legacy alias for --daily-fast.",
    )
    ap.add_argument("--skip-gate", action="store_true")
    ap.add_argument("--skip-drill", action="store_true")
    ap.add_argument("--skip-daily-panel", action="store_true")
    ap.add_argument(
        "--legacy-max-merge",
        action="store_true",
        help="Diagnostic: use v2b max merge instead of v2b_strict SSOT.",
    )
    ap.add_argument(
        "--allowlist-review",
        action="store_true",
        help="After routine gate, run allowlist_review gate (requires human signoff JSON).",
    )
    args = ap.parse_args()

    if args.weekly_full and (args.daily_fast or args.skip_kpi_b_refresh):
        raise SystemExit("use either --weekly-full or --daily-fast/--skip-kpi-b-refresh, not both")
    skip_kpi = args.daily_fast or args.skip_kpi_b_refresh or not args.weekly_full

    overlay = "v2b" if args.legacy_max_merge else "v2b_strict"
    fold_out = FOLD_MAX if args.legacy_max_merge else FOLD_STRICT

    py = sys.executable
    steps: list[list[str]] = []
    if not skip_kpi:
        steps.append([py, "scripts/run_btrack_kpi_b_shadow_eval_v1.py"])
    if not args.skip_daily_panel:
        steps.append(
            [
                py,
                "scripts/build_btrack_31k41k_daily_anchor_panel_v1.py",
                "--feature-mode",
                "timeseries_v2",
                "--rolling-sample-size",
                "256",
            ]
        )
    steps.extend(
        [
            [py, "scripts/run_btrack_31k41k_prophecy_shadow_eval_v1.py", "--overlay-version", overlay],
            [
                py,
                "scripts/run_btrack_31k41k_prophecy_shadow_fold_stability_v1.py",
                "--overlay-version",
                overlay,
                "--out-json",
                fold_out,
            ],
        ]
    )
    if not args.skip_gate:
        gate_cmd = [
            py,
            "scripts/check_btrack_31k41k_prophecy_shadow_gate_v1.py",
            "--gate-mode",
            "routine",
            "--fold-json",
            fold_out,
        ]
        if args.legacy_max_merge:
            gate_cmd.append("--allow-legacy-max-merge")
        steps.append(gate_cmd)
        if args.allowlist_review:
            steps.append(
                [
                    py,
                    "scripts/check_btrack_31k41k_prophecy_shadow_gate_v1.py",
                    "--gate-mode",
                    "allowlist_review",
                    "--fold-json",
                    fold_out,
                ]
            )
    steps.extend(
        [
            [py, "scripts/append_btrack_31k41k_prophecy_shadow_log_v1.py", "--append-contrast-audit"],
            [py, "scripts/summarize_btrack_31k41k_prophecy_shadow_log_v1.py"],
        ]
    )
    if not args.skip_drill:
        steps.append(
            [
                py,
                "scripts/build_btrack_31k41k_prophecy_shadow_fold_drill_v1.py",
                "--fold-json",
                fold_out,
            ]
        )

    rc = 0
    for cmd in steps:
        step_rc = _run(cmd)
        if step_rc != 0:
            rc = step_rc
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
