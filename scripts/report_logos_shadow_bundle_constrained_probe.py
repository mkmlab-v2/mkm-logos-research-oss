#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""7-window bundle probe: maximize bottleneck = min(temporal CE, holdout CE) to reduce holdout mirage."""
from __future__ import annotations

import argparse
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

_lib_path = Path(__file__).resolve().parent / "logos_shadow_eval_lib.py"
_spec = importlib.util.spec_from_file_location("logos_shadow_eval_lib", _lib_path)
if _spec is None or _spec.loader is None:
    raise RuntimeError(f"cannot load {_lib_path}")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
aggregate_cost_metrics = _mod.aggregate_cost_metrics
load_kospi_yf_rows = _mod.load_kospi_yf_rows
run_windows = _mod.run_windows

SCRIPT = ROOT / "scripts" / "run_logos_kospi_shadow_test.py"
DATA = ROOT / "research" / "market_data" / "kospi_daily_external_yf.csv"
DEFAULT_OUT = ROOT / "reports" / "research" / "logos_shadow_v1" / "logos_kospi_shadow_bundle_constrained_probe_latest.json"
CV_DIR = ROOT / "reports" / "research" / "logos_shadow_v1" / "cv_windows"

WINDOWS_TEMPORAL: list[tuple[str, str, str]] = [
    ("t1_2003_2007_pre_gfc", "2003-01-01", "2007-12-31"),
    ("t2_2010_2014_post_gfc", "2010-01-01", "2014-12-31"),
    ("t3_2023_2024_recent", "2023-01-01", "2024-12-31"),
]
WINDOWS_HOLDOUT: list[tuple[str, str, str]] = [
    ("h1_2011_euro_daily", "2011-07-01", "2012-01-31"),
    ("h2_2015_cn_deval_daily", "2015-06-01", "2016-02-29"),
    ("h3_2018_q4_riskoff_daily", "2018-08-01", "2019-01-31"),
    ("h4_2022_rate_shock_daily", "2022-01-01", "2022-12-31"),
]
TEMPORAL_IDS = {w[0] for w in WINDOWS_TEMPORAL}
HOLDOUT_IDS = {w[0] for w in WINDOWS_HOLDOUT}
ALL_WINDOWS = WINDOWS_TEMPORAL + WINDOWS_HOLDOUT


def main() -> int:
    ap = argparse.ArgumentParser(description="Bundle probe with bottleneck objective min(temporal_CE, holdout_CE).")
    ap.add_argument("--script", type=Path, default=SCRIPT)
    ap.add_argument("--data-csv", type=Path, default=DATA)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--out-dir", type=Path, default=CV_DIR)
    ap.add_argument("--load-cost-coeff", type=float, default=4.8)
    ap.add_argument("--false-cost-coeff", type=float, default=1.5)
    ap.add_argument("--min-cost-efficiency-score", type=float, default=0.35)
    ap.add_argument(
        "--lookbacks",
        type=int,
        nargs="+",
        default=[20, 60],
        help="precrash_lookback_days values; full grid runs per value (pass-through to run_logos_kospi_shadow_test).",
    )
    args = ap.parse_args()

    rows = load_kospi_yf_rows(args.data_csv)
    kw: dict[str, Any] = {
        "load_cost_coeff": float(args.load_cost_coeff),
        "false_cost_coeff": float(args.false_cost_coeff),
        "min_cost_efficiency_score": float(args.min_cost_efficiency_score),
    }

    runs: list[dict[str, Any]] = []
    for plb in args.lookbacks:
        plb = max(1, int(plb))
        grid: list[dict[str, Any]] = []
        for cm in [0, 4, 8]:
            for rf in [4, 6, 8, 10]:
                for comp_thr in [0.14, 0.16, 0.18]:
                    for use_layer in [False, True]:
                        layer_variants: list[tuple[int, int]] = [(1, 3)] if not use_layer else [(2, 2), (3, 1)]
                        for min_ev, den_max in layer_variants:
                            extra = [
                                "--precrash-lookback-days",
                                str(plb),
                                "--cluster-merge-days",
                                str(cm),
                                "--refractory-days",
                                str(rf),
                                "--recent-composite-warn-threshold",
                                str(comp_thr),
                            ]
                            if use_layer:
                                extra += [
                                    "--enable-recent-precision-layer",
                                    "--recent-precision-min-evidence",
                                    str(min_ev),
                                    "--recent-precision-density-window",
                                    "30",
                                    "--recent-precision-density-max",
                                    str(den_max),
                                ]
                            per = run_windows(
                                rows=rows,
                                windows=ALL_WINDOWS,
                                script=args.script,
                                out_dir=args.out_dir,
                                extra=extra,
                                input_prefix=f"bprobe_lb{plb}",
                            )
                            temporal_rows = [x for x in per if x["window"] in TEMPORAL_IDS]
                            holdout_rows = [x for x in per if x["window"] in HOLDOUT_IDS]
                            agg_t = aggregate_cost_metrics(temporal_rows, **kw)
                            agg_h = aggregate_cost_metrics(holdout_rows, **kw)
                            agg_c = aggregate_cost_metrics(per, **kw)
                            ce_t = float(agg_t["cost_efficiency_score"])
                            ce_h = float(agg_h["cost_efficiency_score"])
                            bottleneck = min(ce_t, ce_h)
                            grid.append(
                                {
                                    "args": extra,
                                    "use_recent_precision_layer": use_layer,
                                    "temporal_aggregate": agg_t,
                                    "holdout_aggregate": agg_h,
                                    "combined_aggregate": agg_c,
                                    "bottleneck_cost_efficiency": round(bottleneck, 6),
                                    "temporal_pass": agg_t["pass_cost_gate"],
                                    "holdout_pass": agg_h["pass_cost_gate"],
                                    "combined_pass": agg_c["pass_cost_gate"],
                                }
                            )

        grid.sort(key=lambda x: (x["bottleneck_cost_efficiency"], x["combined_aggregate"]["cost_efficiency_score"]), reverse=True)
        top = grid[0] if grid else {}
        runs.append(
            {
                "precrash_lookback_days": plb,
                "grid_size": len(grid),
                "top15": grid[:15],
                "best": {
                    "bottleneck_cost_efficiency": top.get("bottleneck_cost_efficiency"),
                    "combined_pass": (top.get("combined_aggregate") or {}).get("pass_cost_gate"),
                    "temporal_pass": top.get("temporal_pass"),
                    "holdout_pass": top.get("holdout_pass"),
                    "args": top.get("args"),
                },
            }
        )

    payload = {
        "schema": "logos_kospi_shadow_bundle_constrained_probe_v2",
        "ts_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "objective": "bottleneck = min(temporal cost_efficiency, holdout cost_efficiency); tie-break by combined CE",
        "coefficients": {"load": kw["load_cost_coeff"], "false_alert_density": kw["false_cost_coeff"]},
        "min_cost_efficiency_score": kw["min_cost_efficiency_score"],
        "lookbacks_evaluated": [r["precrash_lookback_days"] for r in runs],
        "runs": runs,
        "note": "Research-only OBSERVATION_ONLY. precrash_lookback_days changes label geometry; compare runs only at same lookback.",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(args.out.resolve()), "runs": [r["precrash_lookback_days"] for r in runs]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
