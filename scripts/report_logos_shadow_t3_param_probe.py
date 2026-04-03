#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Small param probe for T3 (2023-2024) to recover precrash-window recall."""
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_logos_kospi_shadow_test.py"
DATA = ROOT / "research" / "market_data" / "kospi_daily_external_yf.csv"
OUT = ROOT / "reports" / "research" / "logos_shadow_v1" / "logos_kospi_shadow_t3_param_probe_latest.json"
CV_DIR = ROOT / "reports" / "research" / "logos_shadow_v1" / "cv_windows"

_lib_path = Path(__file__).resolve().parent / "logos_shadow_eval_lib.py"
_spec = importlib.util.spec_from_file_location("logos_shadow_eval_lib", _lib_path)
if _spec is None or _spec.loader is None:
    raise RuntimeError(f"cannot load {_lib_path}")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
load_kospi_yf_rows = _mod.load_kospi_yf_rows

T3 = ("2023-01-01", "2024-12-31")


def _score(metrics: dict[str, Any]) -> float:
    # Prioritize precrash utility with moderate penalty on load/false alerts.
    recall = float(metrics.get("crash_warning_recall", 0.0))
    precision = float(metrics.get("precrash_zone_precision", 0.0))
    load = float(metrics.get("warning_load_ratio", 0.0))
    false_d = float(metrics.get("false_alert_density", 0.0))
    return 2.4 * recall + 1.2 * precision - 0.6 * load - 0.8 * false_d


def main() -> int:
    ap = argparse.ArgumentParser(description="Probe T3 for recall/precision recovery candidates.")
    ap.add_argument("--script", type=Path, default=SCRIPT)
    ap.add_argument("--data-csv", type=Path, default=DATA)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--out-dir", type=Path, default=CV_DIR)
    args = ap.parse_args()

    rows = [r for r in load_kospi_yf_rows(args.data_csv) if T3[0] <= r["date"] <= T3[1]]
    args.out_dir.mkdir(parents=True, exist_ok=True)
    p_in = args.out_dir / "t3_param_probe_input.json"
    p_in.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    grid: list[dict[str, Any]] = []
    for cm in [0, 4, 6, 8, 10]:
        for rf in [0, 2, 4, 6, 8]:
            for comp_thr in [0.14, 0.16, 0.18]:
                for use_layer in [False, True]:
                    layer_variants: list[tuple[int, int]] = [(1, 3)] if not use_layer else [(1, 3), (2, 2), (3, 1)]
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
                        cmd = [sys.executable, str(args.script), "--input-json", str(p_in), "--out-dir", str(args.out_dir)] + extra
                        cp = subprocess.run(cmd, capture_output=True, text=True)
                        if cp.returncode != 0:
                            continue
                        metrics = json.loads(cp.stdout).get("metrics", {})
                        row = {
                            "args": extra,
                            "use_recent_precision_layer": use_layer,
                            "metrics": metrics,
                            "probe_score": round(_score(metrics), 6),
                        }
                        grid.append(row)

    grid.sort(key=lambda x: x["probe_score"], reverse=True)
    top = grid[:10]
    payload = {
        "schema": "logos_kospi_shadow_t3_param_probe_v1",
        "ts_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window": {"period": [T3[0], T3[1]], "rows": len(rows)},
        "grid_size": len(grid),
        "top10": top,
        "note": "Research-only probe for T3; choose candidates then validate on temporal/holdout bundle.",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(args.out.resolve()), "grid_size": len(grid)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
