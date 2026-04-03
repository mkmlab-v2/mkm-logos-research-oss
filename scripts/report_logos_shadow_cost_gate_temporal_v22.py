#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Recompute temporal cost gate using v21 precrash_zone_precision (not directional hit rate)."""
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
DEFAULT_OUT = ROOT / "reports" / "research" / "logos_shadow_v1" / "logos_kospi_shadow_cost_gate_temporal_v22_latest.json"

WINDOWS: list[tuple[str, str, str]] = [
    ("t1_2003_2007_pre_gfc", "2003-01-01", "2007-12-31"),
    ("t2_2010_2014_post_gfc", "2010-01-01", "2014-12-31"),
    ("t3_2023_2024_recent", "2023-01-01", "2024-12-31"),
]


def main() -> int:
    ap = argparse.ArgumentParser(description="Temporal cost gate with precrash_zone_precision (v21 definition).")
    ap.add_argument("--script", type=Path, default=DEFAULT_SCRIPT)
    ap.add_argument("--data-csv", type=Path, default=DEFAULT_DATA)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--out-dir", type=Path, default=ROOT / "reports" / "research" / "logos_shadow_v1" / "cv_windows")
    ap.add_argument("--load-cost-coeff", type=float, default=4.8, help="Matches inline sweep: load term coefficient")
    ap.add_argument("--false-cost-coeff", type=float, default=1.5, help="Matches inline sweep: false-alert density coefficient")
    ap.add_argument("--min-cost-efficiency-score", type=float, default=0.35)
    ap.add_argument(
        "--bare",
        action="store_true",
        help="Pass no shadow extra args (legacy baseline). Default applies sparsification + recent precision layer.",
    )
    args, extra = ap.parse_known_args()

    extra_list = list(extra)
    if not extra_list and not args.bare:
        extra_list = list(DEFAULT_SHADOW_EXTRA)

    rows = load_kospi_yf_rows(args.data_csv)
    per = run_windows(
        rows=rows,
        windows=WINDOWS,
        script=args.script,
        out_dir=args.out_dir,
        extra=extra_list,
        input_prefix="v22",
    )
    agg = aggregate_cost_metrics(
        per,
        load_cost_coeff=float(args.load_cost_coeff),
        false_cost_coeff=float(args.false_cost_coeff),
        min_cost_efficiency_score=float(args.min_cost_efficiency_score),
    )

    payload: dict[str, Any] = {
        "schema": "logos_kospi_shadow_cost_gate_temporal_v22",
        "ts_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "precision_definition": "precrash_zone_precision (v21; not directional hit_direction_rate)",
        "cost_formula": "avg_precrash_zone_precision / (1 + load_coeff*avg_load_ratio + false_coeff*avg_false_alert_density)",
        "coefficients": {"load": float(args.load_cost_coeff), "false_alert_density": float(args.false_cost_coeff)},
        "min_cost_efficiency_score": float(args.min_cost_efficiency_score),
        "extra_args": extra_list,
        "windows": per,
        "aggregate": agg,
        "note": "Uses v21 metric separation; temporal splits t1/t2/t3. Research-only (OBSERVATION_ONLY).",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "output": str(args.out.resolve()),
                "pass_cost_gate": agg["pass_cost_gate"],
                "cost_efficiency_score": agg["cost_efficiency_score"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
