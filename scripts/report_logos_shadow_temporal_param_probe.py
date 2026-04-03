#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Temporal (t1-t3) probe with extra weight on recent window recall."""
from __future__ import annotations

import argparse
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_logos_kospi_shadow_test.py"
DATA = ROOT / "research" / "market_data" / "kospi_daily_external_yf.csv"
OUT = ROOT / "reports" / "research" / "logos_shadow_v1" / "logos_kospi_shadow_temporal_param_probe_latest.json"
CV_DIR = ROOT / "reports" / "research" / "logos_shadow_v1" / "cv_windows"

_lib_path = Path(__file__).resolve().parent / "logos_shadow_eval_lib.py"
_spec = importlib.util.spec_from_file_location("logos_shadow_eval_lib", _lib_path)
if _spec is None or _spec.loader is None:
    raise RuntimeError(f"cannot load {_lib_path}")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
load_kospi_yf_rows = _mod.load_kospi_yf_rows
run_windows = _mod.run_windows
aggregate_cost_metrics = _mod.aggregate_cost_metrics

WINDOWS = [
    ("t1_2003_2007_pre_gfc", "2003-01-01", "2007-12-31"),
    ("t2_2010_2014_post_gfc", "2010-01-01", "2014-12-31"),
    ("t3_2023_2024_recent", "2023-01-01", "2024-12-31"),
]


def _objective(per: list[dict[str, Any]], agg: dict[str, Any]) -> float:
    # Temporal balance + explicit t3 recall rescue pressure.
    t3 = next((x for x in per if x["window"] == "t3_2023_2024_recent"), None)
    t3_recall = float((t3 or {}).get("metrics", {}).get("crash_warning_recall", 0.0))
    return (
        1.8 * float(agg.get("avg_crash_warning_recall", 0.0))
        + 1.0 * float(agg.get("avg_precrash_zone_precision", 0.0))
        + 0.8 * t3_recall
        - 0.8 * float(agg.get("avg_warning_load_ratio", 0.0))
        - 1.0 * float(agg.get("avg_false_alert_density", 0.0))
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Temporal t1-t3 probe (recent-recall-aware objective).")
    ap.add_argument("--script", type=Path, default=SCRIPT)
    ap.add_argument("--data-csv", type=Path, default=DATA)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--out-dir", type=Path, default=CV_DIR)
    args = ap.parse_args()

    rows = load_kospi_yf_rows(args.data_csv)
    grid: list[dict[str, Any]] = []
    for cm in [0, 4, 8, 10]:
        for rf in [2, 4, 6, 8, 10]:
            for comp_thr in [0.14, 0.16, 0.18]:
                for use_layer in [False, True]:
                    layer_variants: list[tuple[int, int]] = [(1, 3)] if not use_layer else [(2, 2), (3, 1)]
                    for min_ev, den_max in layer_variants:
                        extra = [
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
                            windows=WINDOWS,
                            script=args.script,
                            out_dir=args.out_dir,
                            extra=extra,
                            input_prefix="tprobe",
                        )
                        agg = aggregate_cost_metrics(per, load_cost_coeff=4.8, false_cost_coeff=1.5, min_cost_efficiency_score=0.35)
                        score = _objective(per, agg)
                        grid.append(
                            {
                                "args": extra,
                                "use_recent_precision_layer": use_layer,
                                "temporal": {"per_window": per, "aggregate": agg},
                                "probe_score": round(score, 6),
                            }
                        )

    grid.sort(key=lambda x: x["probe_score"], reverse=True)
    payload = {
        "schema": "logos_kospi_shadow_temporal_param_probe_v1",
        "ts_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "grid_size": len(grid),
        "top10": grid[:10],
        "note": "Temporal-only probe; run full bundle separately for selected candidates.",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(args.out.resolve()), "grid_size": len(grid)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
