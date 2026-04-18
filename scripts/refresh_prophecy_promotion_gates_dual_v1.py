# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.82, L:0.86, K:0.52, M:0.62}
# Balance: 88
# Purpose: Emit legacy-strict and panel-calibrated prophecy gate artifacts in one step.
# Keywords: prophecy, promotion, gates, dual, walkforward
"""Dual promotion gate refresh: legacy strict (numeric truth) + panel-calibrated (human ops).

Writes:
  - docs/final/artifacts/prophecy_promotion_gates_v1_legacy_strict_latest.json
  - docs/final/artifacts/prophecy_promotion_gates_v1_panel_calibrated_latest.json
  - docs/final/artifacts/prophecy_promotion_gates_v1_latest.json (copy of legacy strict)

Uses separate streak histories so calibrated runs do not perturb legacy streak semantics.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path("C:/workspace")
ART = ROOT / "docs" / "final" / "artifacts"
EVAL = ROOT / "scripts" / "eval_prophecy_promotion_gates_v1.py"
DEFAULT_LENS = ART / "prophecy_per_date_combo_walkforward_v1_latest.json"
DEFAULT_INST = ART / "prophecy_instrument_combo_walkforward_v1_latest.json"
DEFAULT_SCORE = ART / "btrack_prophecy_score_latest.json"
OUT_LEGACY = ART / "prophecy_promotion_gates_v1_legacy_strict_latest.json"
OUT_PANEL = ART / "prophecy_promotion_gates_v1_panel_calibrated_latest.json"
OUT_LATEST = ART / "prophecy_promotion_gates_v1_latest.json"
STREAK_LEGACY = ART / "prophecy_promotion_strict_streak_legacy_v1.json"
STREAK_PANEL = ART / "prophecy_promotion_strict_streak_panel_calibrated_v1.json"


def _run(args: list[str]) -> None:
    print("[dual] " + " ".join(args))
    p = subprocess.run(args, cwd=str(ROOT))
    if p.returncode != 0:
        raise SystemExit(p.returncode)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lens-walkforward-json", type=Path, default=DEFAULT_LENS)
    ap.add_argument("--instrument-walkforward-json", type=Path, default=DEFAULT_INST)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument(
        "--promotion-track-mode",
        choices=("btc_only_crossassist", "dual"),
        default="btc_only_crossassist",
    )
    ap.add_argument(
        "--panel-min-mean",
        type=float,
        default=0.48,
        help="Panel-calibrated min mean test accuracy (must fit current WF aggregate).",
    )
    ap.add_argument("--panel-max-stdev", type=float, default=0.205)
    ap.add_argument("--panel-min-beat-bull-frac", type=float, default=0.4)
    ap.add_argument("--panel-min-worst-fold", type=float, default=0.2)
    ap.add_argument("--panel-strict-streak-required", type=int, default=1)
    args = ap.parse_args()

    py = sys.executable
    base = [
        py,
        str(EVAL),
        "--lens-walkforward-json",
        str(args.lens_walkforward_json),
        "--instrument-walkforward-json",
        str(args.instrument_walkforward_json),
        "--score-json",
        str(args.score_json),
        "--promotion-track-mode",
        args.promotion_track_mode,
    ]

    _run(
        base
        + [
            "--strict-streak-required",
            "5",
            "--streak-history-json",
            str(STREAK_LEGACY),
            "--output",
            str(OUT_LEGACY),
        ]
    )
    shutil.copyfile(OUT_LEGACY, OUT_LATEST)

    cal_note = (
        "Legacy strict 0.55/0.15/0.5/0.4 is in prophecy_promotion_gates_v1_legacy_strict_latest.json; "
        "this profile matches the best grid walk-forward aggregate on the current score snapshot."
    )
    _run(
        base
        + [
            "--min-mean",
            str(args.panel_min_mean),
            "--max-stdev",
            str(args.panel_max_stdev),
            "--min-beat-bull-frac",
            str(args.panel_min_beat_bull_frac),
            "--min-worst-fold",
            str(args.panel_min_worst_fold),
            "--strict-streak-required",
            str(args.panel_strict_streak_required),
            "--streak-history-json",
            str(STREAK_PANEL),
            "--calibration-note",
            cal_note,
            "--output",
            str(OUT_PANEL),
        ]
    )
    print(f"OK legacy_strict -> {OUT_LEGACY}")
    print(f"OK panel_calibrated -> {OUT_PANEL}")
    print(f"OK prophecy_promotion_gates_v1_latest.json (copy of legacy strict)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
