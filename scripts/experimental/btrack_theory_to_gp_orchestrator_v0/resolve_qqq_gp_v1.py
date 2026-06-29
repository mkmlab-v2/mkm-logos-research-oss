#!/usr/bin/env python3
"""Evaluate + optional apply resolve for Logos QQQ general_prophecy (B-track)."""
from __future__ import annotations

import argparse
import sys
from functools import partial
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.experimental.btrack_theory_to_gp_orchestrator_v0.equity_gp_resolve_lib_v1 import (
    REGISTRY,
    eval_new_high,
    run_resolve_cli,
)

QQQ_CSV = ROOT / "research" / "market_data" / "qqq_daily_external_yf.csv"
DEFAULT_OUT = ROOT / "reports" / "general_prophecy_qqq_resolve_eval_v1_latest.json"

REFERENCE_DATE = "2026-06-03"
WINDOW_START = "2026-06-04"
WINDOW_END = "2026-09-30"
DEADLINE_UTC = "2026-10-01T00:00:00Z"

QQQ_QID = "gp_2026_logos_qqq_new_high_before_0930"


def _evaluators():
    fn = partial(
        eval_new_high,
        reference_date=REFERENCE_DATE,
        window_start=WINDOW_START,
        window_end=WINDOW_END,
    )
    return {QQQ_QID: fn}


def evaluate_all(csv_path: Path):
    from scripts.experimental.btrack_theory_to_gp_orchestrator_v0.equity_gp_resolve_lib_v1 import (
        evaluate_from_csv,
    )

    return evaluate_from_csv(csv_path, evaluators=_evaluators())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", type=Path, default=QQQ_CSV)
    ap.add_argument("--registry", type=Path, default=REGISTRY)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--force-apply", action="store_true")
    ap.add_argument("--run-brier", action="store_true")
    ns = ap.parse_args()
    return run_resolve_cli(
        schema="general_prophecy_qqq_resolve_eval_v1",
        csv_path=ns.csv,
        registry=ns.registry,
        out_json=ns.out_json,
        deadline_utc=DEADLINE_UTC,
        evaluators=_evaluators(),
        notes_tag="auto_qqq_resolve_v1",
        apply=ns.apply,
        force_apply=ns.force_apply,
        run_brier=ns.run_brier,
    )


if __name__ == "__main__":
    raise SystemExit(main())
