#!/usr/bin/env python3
"""
run_deriv_factor_research_cycle_v1

Research-only cycle:
  1) build_deriv_factor_panel_v1.py
  2) evaluate_deriv_factor_ev_v1.py
  3) select_deriv_alpha_events_v1.py

실매매/집행 연동 없음. 측정 아티팩트 생성 전용.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import List


def _workspace_root() -> Path:
    here = Path(__file__).resolve()
    if (
        here.parent.name == "scripts"
        and here.parent.parent.name == "bitcoin-trading"
        and here.parents[2].name == "projects"
    ):
        return here.parents[3]
    return here.parents[3] if len(here.parents) > 3 else here.parent


def _run(cmd: List[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(
            f"Command failed ({proc.returncode}): {' '.join(cmd)}\n"
            f"stdout:\n{proc.stdout}\n"
            f"stderr:\n{proc.stderr}"
        )


def main() -> int:
    ws = _workspace_root()
    scripts = ws / "projects" / "bitcoin-trading" / "scripts"
    reports = ws / "reports"

    parser = argparse.ArgumentParser(description="Run deriv factor research cycle (collect->eval->select).")
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--samples", type=int, default=120)
    parser.add_argument("--interval-sec", type=float, default=30.0)
    parser.add_argument("--horizons-sec", default="300,900,3600")
    parser.add_argument("--roundtrip-cost-bps", type=float, default=6.0)
    parser.add_argument("--top-k", type=int, default=2)
    parser.add_argument("--min-count", type=int, default=20)
    args = parser.parse_args()

    py = sys.executable
    build_script = scripts / "build_deriv_factor_panel_v1.py"
    eval_script = scripts / "evaluate_deriv_factor_ev_v1.py"
    select_script = scripts / "select_deriv_alpha_events_v1.py"

    _run(
        [
            py,
            str(build_script),
            "--symbol",
            args.symbol,
            "--samples",
            str(args.samples),
            "--interval-sec",
            str(args.interval_sec),
            "--out-dir",
            str(reports),
        ]
    )
    _run(
        [
            py,
            str(eval_script),
            "--symbol",
            args.symbol,
            "--horizons-sec",
            args.horizons_sec,
            "--roundtrip-cost-bps",
            str(args.roundtrip_cost_bps),
        ]
    )
    _run(
        [
            py,
            str(select_script),
            "--top-k",
            str(args.top_k),
            "--min-count",
            str(args.min_count),
        ]
    )

    out = {
        "ok": True,
        "cycle": "deriv_factor_research_cycle_v1",
        "symbol": args.symbol,
        "artifacts": {
            "panel_rows": str(reports / "deriv_factor_panel_rows_v1.jsonl"),
            "panel_summary": str(reports / "deriv_factor_panel_summary_v1.json"),
            "ev_report": str(reports / "deriv_factor_ev_report_v1.json"),
            "candidates": str(reports / "deriv_alpha_event_candidates_v1.json"),
        },
    }
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
