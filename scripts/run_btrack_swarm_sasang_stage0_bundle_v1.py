#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One-shot B-track Swarm×Sasang Stage 0 bundle: optional re-eval + closure report."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable


def _run(cmd: list[str]) -> int:
    print("+", " ".join(cmd), flush=True)
    return subprocess.run(cmd, cwd=str(ROOT), check=False).returncode


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--re-eval",
        action="store_true",
        help="Re-run swarm corr chain (tier_b synthetic) and 4-agent ablation before closure",
    )
    ap.add_argument("--min-pairs", type=int, default=30)
    ap.add_argument("--min-krx-weekdays", type=int, default=30)
    args = ap.parse_args()

    if args.re_eval:
        steps = [
            [
                PY,
                str(ROOT / "scripts/build_swarm_sentiment_synthetic_krx_jsonl_v1.py"),
                "--date-from",
                "2026-04-01",
                "--date-to",
                "2026-06-12",
                "--calendar-mode",
                "krx_weekdays",
            ],
            [
                PY,
                str(ROOT / "scripts/run_btrack_session_panel_swarm_corr_chain_v1.py"),
                "--date-from",
                "2026-04-01",
                "--date-to",
                "2026-06-12",
                "--calendar-mode",
                "krx_weekdays",
                "--swarm-jsonl",
                "data/btrack/swarm_sentiment_synthetic_krx_hypo_v1.jsonl",
                "--ohlcv-csv",
                "research/market_data/kospi_daily_external_yf.csv",
                "--min-pairs",
                str(args.min_pairs),
                "--tag",
                "stage0_30d",
            ],
            [PY, str(ROOT / "scripts/run_sasang_4agent_protocol_ablation_v1.py")],
        ]
        for cmd in steps:
            code = _run(cmd)
            if code != 0:
                return code

    code = _run(
        [
            PY,
            str(ROOT / "scripts/check_btrack_swarm_tier_a_prereqs_v1.py"),
            "--min-krx-weekdays",
            str(args.min_krx_weekdays),
        ]
    )
    if code != 0:
        return code

    return _run(
        [
            PY,
            str(ROOT / "scripts/build_btrack_swarm_sasang_stage0_closure_v1.py"),
            "--min-krx-weekdays",
            str(args.min_krx_weekdays),
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())
