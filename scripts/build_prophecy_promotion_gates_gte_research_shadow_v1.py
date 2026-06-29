#!/usr/bin/env python3
"""[HYPO] Eval promotion gates with lens gte comparator — research shadow only."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SIGNOFF = ROOT / "reports/prophecy_lens_beat_bull_gte_human_signoff_latest.json"
DEFAULT_LENS_WF = ROOT / "reports/prophecy_per_date_combo_walkforward_recommended_chain_v1_latest.json"
DEFAULT_INST_WF = ROOT / "reports/prophecy_instrument_combo_walkforward_recommended_chain_v1_latest.json"
DEFAULT_SCORE = ROOT / "reports/btrack_prophecy_score_recommended_eval_chain_v1_latest.json"
DEFAULT_HYPO = ROOT / "docs/final/artifacts/btrack_hypothesis_prophecy_latest.json"
DEFAULT_OUT = ROOT / "reports/prophecy_promotion_gates_gte_research_shadow_v1_latest.json"
EVAL = ROOT / "scripts/eval_prophecy_promotion_gates_v1.py"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--signoff-json", type=Path, default=DEFAULT_SIGNOFF)
    ap.add_argument("--lens-walkforward-json", type=Path, default=DEFAULT_LENS_WF)
    ap.add_argument("--instrument-walkforward-json", type=Path, default=DEFAULT_INST_WF)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--hypothesis-json", type=Path, default=DEFAULT_HYPO)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--calibration-note",
        default="gte_research_shadow_human_signoff_lane",
    )
    args = ap.parse_args()

    cmd = [
        sys.executable,
        str(EVAL),
        "--promotion-track-mode",
        "dual",
        "--lens-walkforward-json",
        str(args.lens_walkforward_json),
        "--instrument-walkforward-json",
        str(args.instrument_walkforward_json),
        "--score-json",
        str(args.score_json),
        "--hypothesis-json",
        str(args.hypothesis_json),
        "--lens-beat-bull-comparator",
        "gte",
        "--instrument-beat-bull-comparator",
        "gt",
        "--gte-human-signoff-json",
        str(args.signoff_json),
        "--calibration-note",
        str(args.calibration_note),
        "--output",
        str(args.output),
    ]
    return int(subprocess.run(cmd, cwd=str(ROOT)).returncode)


if __name__ == "__main__":
    raise SystemExit(main())
