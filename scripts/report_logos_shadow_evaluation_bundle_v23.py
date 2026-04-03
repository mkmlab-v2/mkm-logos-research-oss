#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Single bundle: temporal (t1-t3) + holdout (h1-h4) cost gates using v21 precrash precision."""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
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
DEFAULT_SHADOW_EXTRA = _mod.DEFAULT_SHADOW_EXTRA_ARGS

DEFAULT_SCRIPT = ROOT / "scripts" / "run_logos_kospi_shadow_test.py"
DEFAULT_DATA = ROOT / "research" / "market_data" / "kospi_daily_external_yf.csv"
DEFAULT_OUT = ROOT / "reports" / "research" / "logos_shadow_v1" / "logos_kospi_shadow_evaluation_bundle_v23_latest.json"

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


def main() -> int:
    ap = argparse.ArgumentParser(description="v23 unified temporal + holdout evaluation bundle.")
    ap.add_argument("--script", type=Path, default=DEFAULT_SCRIPT)
    ap.add_argument("--data-csv", type=Path, default=DEFAULT_DATA)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--out-dir", type=Path, default=ROOT / "reports" / "research" / "logos_shadow_v1" / "cv_windows")
    ap.add_argument("--load-cost-coeff", type=float, default=4.8)
    ap.add_argument("--false-cost-coeff", type=float, default=1.5)
    ap.add_argument("--min-cost-efficiency-score", type=float, default=0.35)
    ap.add_argument(
        "--bare",
        action="store_true",
        help="Pass no shadow extra args (reproduces legacy empty-extra baseline). Default applies sparsification + recent precision layer.",
    )
    args, extra = ap.parse_known_args()

    extra_list = list(extra)
    if not extra_list and not args.bare:
        extra_list = list(DEFAULT_SHADOW_EXTRA)

    rows = load_kospi_yf_rows(args.data_csv)
    temporal = run_windows(
        rows=rows,
        windows=WINDOWS_TEMPORAL,
        script=args.script,
        out_dir=args.out_dir,
        extra=extra_list,
        input_prefix="v23_t",
    )
    holdout = run_windows(
        rows=rows,
        windows=WINDOWS_HOLDOUT,
        script=args.script,
        out_dir=args.out_dir,
        extra=extra_list,
        input_prefix="v23_h",
    )
    combined = temporal + holdout

    kw: dict[str, Any] = {
        "load_cost_coeff": float(args.load_cost_coeff),
        "false_cost_coeff": float(args.false_cost_coeff),
        "min_cost_efficiency_score": float(args.min_cost_efficiency_score),
    }
    agg_temporal = aggregate_cost_metrics(temporal, **kw)
    agg_holdout = aggregate_cost_metrics(holdout, **kw)
    agg_combined = aggregate_cost_metrics(combined, **kw)

    payload: dict[str, Any] = {
        "schema": "logos_kospi_shadow_evaluation_bundle_v23",
        "ts_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "precision_definition": "precrash_zone_precision (v21)",
        "cost_formula": "avg_precrash_zone_precision / (1 + load_coeff*avg_load_ratio + false_coeff*avg_false_alert_density)",
        "coefficients": {"load": float(args.load_cost_coeff), "false_alert_density": float(args.false_cost_coeff)},
        "min_cost_efficiency_score": float(args.min_cost_efficiency_score),
        "extra_args": extra_list,
        "temporal": {"windows": WINDOWS_TEMPORAL, "per_window": temporal, "aggregate": agg_temporal},
        "holdout": {"windows": WINDOWS_HOLDOUT, "per_window": holdout, "aggregate": agg_holdout},
        "combined_all_windows": {"per_window": combined, "aggregate": agg_combined},
        "note": "Research-only OBSERVATION_ONLY; combined uses 7 windows (3 temporal + 4 holdout).",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "output": str(args.out.resolve()),
                "temporal_pass": agg_temporal["pass_cost_gate"],
                "holdout_pass": agg_holdout["pass_cost_gate"],
                "combined_pass": agg_combined["pass_cost_gate"],
                "combined_cost_efficiency_score": agg_combined["cost_efficiency_score"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
