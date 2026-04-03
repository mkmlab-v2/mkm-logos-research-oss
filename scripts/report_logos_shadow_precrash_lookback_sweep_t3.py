#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sweep --precrash-lookback-days on T3 (2023-2024) with fixed shadow extra args (OBSERVATION_ONLY)."""
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

_lib_path = Path(__file__).resolve().parent / "logos_shadow_eval_lib.py"
_spec = importlib.util.spec_from_file_location("logos_shadow_eval_lib", _lib_path)
if _spec is None or _spec.loader is None:
    raise RuntimeError(f"cannot load {_lib_path}")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
DEFAULT_SHADOW_EXTRA = _mod.DEFAULT_SHADOW_EXTRA_ARGS
load_kospi_yf_rows = _mod.load_kospi_yf_rows

SCRIPT = ROOT / "scripts" / "run_logos_kospi_shadow_test.py"
DATA = ROOT / "research" / "market_data" / "kospi_daily_external_yf.csv"
OUT = ROOT / "reports" / "research" / "logos_shadow_v1" / "logos_kospi_shadow_precrash_lookback_sweep_t3_latest.json"
CV_DIR = ROOT / "reports" / "research" / "logos_shadow_v1" / "cv_windows"

T3 = ("2023-01-01", "2024-12-31")

# Bundle-constrained probe winner (same family as temporal bottleneck).
WINNER_EXTRA = [
    "--cluster-merge-days",
    "0",
    "--refractory-days",
    "8",
    "--recent-composite-warn-threshold",
    "0.14",
    "--enable-recent-precision-layer",
    "--recent-precision-min-evidence",
    "3",
    "--recent-precision-density-window",
    "30",
    "--recent-precision-density-max",
    "1",
]


def main() -> int:
    ap = argparse.ArgumentParser(description="Precrash lookback sweep on T3 window.")
    ap.add_argument("--data-csv", type=Path, default=DATA)
    ap.add_argument("--script", type=Path, default=SCRIPT)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--out-dir", type=Path, default=CV_DIR)
    ap.add_argument(
        "--lookbacks",
        type=int,
        nargs="*",
        default=[10, 15, 20, 30, 40, 60],
        help="precrash_lookback_days values to try",
    )
    ap.add_argument("--use-default-shadow-extra", action="store_true", help="Use logos_shadow_eval_lib.DEFAULT_SHADOW_EXTRA_ARGS instead of WINNER_EXTRA.")
    args = ap.parse_args()

    rows = [r for r in load_kospi_yf_rows(args.data_csv) if T3[0] <= r["date"] <= T3[1]]
    args.out_dir.mkdir(parents=True, exist_ok=True)
    p_in = args.out_dir / "t3_precrash_sweep_input.json"
    p_in.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    base = list(DEFAULT_SHADOW_EXTRA) if args.use_default_shadow_extra else list(WINNER_EXTRA)
    results: list[dict[str, Any]] = []
    for m in args.lookbacks:
        extra = base + ["--precrash-lookback-days", str(int(m))]
        cmd = [sys.executable, str(args.script), "--input-json", str(p_in), "--out-dir", str(args.out_dir)] + extra
        cp = subprocess.run(cmd, capture_output=True, text=True)
        if cp.returncode != 0:
            results.append({"precrash_lookback_days": m, "ok": False, "error": (cp.stderr or cp.stdout)[:2000]})
            continue
        metrics = json.loads(cp.stdout).get("metrics", {})
        results.append(
            {
                "precrash_lookback_days": int(m),
                "ok": True,
                "metrics": metrics,
            }
        )

    payload = {
        "schema": "logos_kospi_shadow_precrash_lookback_sweep_t3_v1",
        "ts_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window": {"period": list(T3), "rows": len(rows)},
        "base_extra_args": base,
        "rows": results,
        "observation_only": True,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(args.out.resolve()), "n": len(results)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
