#!/usr/bin/env python3
"""[HYPO] tol × ngram_size grid sweep for fABBA sidecar (KOSPI intersection 180d / 2bps)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from itertools import product
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.prophecy_fabba_sidecar_lib_v1 import (  # noqa: E402
    load_dual_leg_intersection_window,
    run_blocked_wf_arms_for_panel,
)

DEFAULT_KOSPI = ROOT / "research/market_data/kospi_daily_external_yf.csv"
DEFAULT_BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
DEFAULT_OUT = ROOT / "reports/prophecy_fabba_sidecar_param_sweep_v1_latest.json"
SCHEMA = "prophecy_fabba_sidecar_param_sweep_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC)
    ap.add_argument("--last-n-intersection", type=int, default=180)
    ap.add_argument("--n-folds", type=int, default=6)
    ap.add_argument("--neutral-bps", type=float, default=2.0)
    ap.add_argument("--lookback", type=int, default=20)
    ap.add_argument("--tol-grid", default="0.03,0.05,0.08")
    ap.add_argument("--ngram-grid", default="2,3,4")
    ap.add_argument("--backend", choices=("auto", "apca_stub", "fabba"), default="apca_stub")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    tols = [float(x.strip()) for x in args.tol_grid.split(",") if x.strip()]
    ngrams = [int(x.strip()) for x in args.ngram_grid.split(",") if x.strip()]

    window = load_dual_leg_intersection_window(
        args.kospi_csv,
        args.btc_csv,
        last_n_intersection=args.last_n_intersection,
    )
    if window.get("status") != "ok":
        print(f"window failed: {window}", file=sys.stderr)
        return 2

    kospi = window["panels"]["kospi"]
    eval_dates = window["intersection_dates"]
    rows: list[dict[str, Any]] = []

    for tol, ngram in product(tols, ngrams):
        res = run_blocked_wf_arms_for_panel(
            instrument_id="kospi",
            dates=kospi["dates"],
            closes=kospi["closes"],
            eval_dates=eval_dates,
            n_folds=args.n_folds,
            neutral_bps=args.neutral_bps,
            lookback=args.lookback,
            ngram_size=ngram,
            tol=tol,
            backend=args.backend,
            alpha=0.1,
        )
        ngram_arm = next((a for a in res.get("arms") or [] if a.get("arm_id") == "fabba_sidecar_ngram_lut"), {})
        slope_arm = next((a for a in res.get("arms") or [] if a.get("arm_id") == "fabba_sidecar_last_slope"), {})
        rows.append(
            {
                "tol": tol,
                "ngram_size": ngram,
                "ngram_pooled_hr": ngram_arm.get("pooled_test_directional_hit_rate"),
                "ngram_n_evaluated": ngram_arm.get("total_n_evaluated"),
                "slope_pooled_hr": slope_arm.get("pooled_test_directional_hit_rate"),
            }
        )

    best = max(rows, key=lambda r: (r.get("ngram_pooled_hr") or -1.0, -(r.get("ngram_n_evaluated") or 0)))

    out = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "send_gate": "HOLD",
        "instrument": "kospi_intersection_only",
        "protocol": {
            "last_n_intersection": args.last_n_intersection,
            "neutral_bps": args.neutral_bps,
            "n_folds": args.n_folds,
            "lookback": args.lookback,
            "backend": args.backend,
        },
        "grid_rows": rows,
        "best_by_ngram_pooled_hr": best,
        "reproduce": (
            f"py scripts/run_prophecy_fabba_sidecar_param_sweep_v1.py "
            f"--tol-grid {args.tol_grid} --ngram-grid {args.ngram_grid}"
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()} best_tol={best['tol']} ngram={best['ngram_size']} hr={best['ngram_pooled_hr']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
