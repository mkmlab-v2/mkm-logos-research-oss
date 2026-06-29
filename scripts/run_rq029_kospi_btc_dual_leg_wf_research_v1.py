#!/usr/bin/env python3
"""[HYPO] RQ-029 KOSPI+BTC dual-leg instrument-combo blocked WF (research_only).

Builds an isolated dual-leg score panel (does not overwrite operational score JSON),
then runs instrument-combo walk-forward to reports/rq029_*.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_KOSPI = ROOT / "research/market_data/kospi_daily_external_yf.csv"
DEFAULT_BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
DEFAULT_HYP = ROOT / "docs/final/artifacts/btrack_hypothesis_prophecy_latest.json"
DEFAULT_SCORE = ROOT / "reports/rq029_btrack_prophecy_score_dual_leg_v1_latest.json"
DEFAULT_WF_OUT = ROOT / "reports/rq029_kospi_btc_dual_leg_wf_v1_latest.json"
DEFAULT_WF_COMPARE = ROOT / "reports/kospi_prophecy_wf_holdout_compare_v1_latest.json"
SCHEMA = "rq029_kospi_btc_dual_leg_wf_research_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        o = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return o if isinstance(o, dict) else None


def _run(cmd: list[str]) -> int:
    print("RUN:", " ".join(cmd), flush=True)
    return int(subprocess.run(cmd, cwd=str(ROOT), check=False).returncode)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--recent-trading-days", type=int, default=252)
    ap.add_argument("--n-folds", type=int, default=5)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--wf-output", type=Path, default=DEFAULT_WF_OUT)
    ap.add_argument("--skip-score-build", action="store_true")
    args = ap.parse_args(argv)

    if not args.skip_score_build:
        rc = _run(
            [
                sys.executable,
                "scripts/build_btrack_prophecy_score_from_ohlcv.py",
                "--hypothesis-json",
                str(DEFAULT_HYP),
                "--kospi-csv",
                str(DEFAULT_KOSPI),
                "--btc-csv",
                str(DEFAULT_BTC),
                "--force-dual-leg-panel",
                "--recent-trading-days",
                str(args.recent_trading_days),
                "--output",
                str(args.score_json),
            ]
        )
        if rc != 0:
            return rc

    if not args.score_json.is_file():
        print(f"missing score: {args.score_json}", file=sys.stderr)
        return 2

    rc = _run(
        [
            sys.executable,
            "scripts/run_prophecy_instrument_combo_walkforward_v1.py",
            "--score-json",
            str(args.score_json),
            "--kospi-csv",
            str(DEFAULT_KOSPI),
            "--btc-csv",
            str(DEFAULT_BTC),
            "--n-folds",
            str(args.n_folds),
            "--output",
            str(args.wf_output),
        ]
    )
    if rc != 0:
        return rc

    wf_doc = _load_json(args.wf_output) or {}
    wf_compare = _load_json(DEFAULT_WF_COMPARE) or {}
    wf_arms = ((wf_compare.get("blocked_walkforward_test_only") or {}).get("arms") or [])
    majority_hr = next(
        (a.get("pooled_test_directional_hit_rate") for a in wf_arms if a.get("arm_id") == "majority_from_train"),
        None,
    )
    agg = wf_doc.get("aggregate") or {}
    inst_mean = agg.get("mean_test_accuracy") or wf_doc.get("mean_test_accuracy")
    inst_pooled = None
    folds = wf_doc.get("folds") or wf_doc.get("fold_results") or []
    if isinstance(folds, list) and folds:
        ns = [int(f.get("test_n") or f.get("n_evaluated") or 0) for f in folds]
        hs = [int(f.get("test_hits") or f.get("price_hits") or 0) for f in folds]
        tn = sum(ns)
        inst_pooled = round(sum(hs) / tn, 6) if tn else None

    bundle = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "rq_id": "RQ-029",
        "prior_rq": "RQ-028",
        "score_json": str(args.score_json.relative_to(ROOT)).replace("\\", "/"),
        "instrument_combo_wf": str(args.wf_output.relative_to(ROOT)).replace("\\", "/"),
        "recent_trading_days": args.recent_trading_days,
        "n_folds": args.n_folds,
        "compare": {
            "wf_kospi_majority_pooled_hr": majority_hr,
            "instrument_combo_mean_test_accuracy": inst_mean,
            "instrument_combo_pooled_hr_est": inst_pooled,
            "instrument_combo_vs_kospi_majority_pp": (
                round(float(inst_mean) - float(majority_hr), 4)
                if inst_mean is not None and majority_hr is not None
                else None
            ),
        },
        "wf_doc_summary": {
            "schema": wf_doc.get("schema"),
            "aggregate": agg,
            "n_walkforward_folds": (wf_doc.get("inputs") or {}).get("n_walkforward_folds"),
        },
        "caveat_ko": "듀얼레그 instrument combo ≠ KOSPI-only WF majority; operational score JSON 미변경.",
    }
    out_path = ROOT / "reports/rq029_kospi_btc_dual_leg_wf_research_v1_latest.json"
    out_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
