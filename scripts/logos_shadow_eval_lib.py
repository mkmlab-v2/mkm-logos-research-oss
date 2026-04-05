#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared helpers for logos KOSPI shadow cost / window evaluation (v22+)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

# When evaluation scripts receive no CLI extra args: sparsification + v20-style recent precision layer.
# OBSERVATION_ONLY research default; override with explicit extra args or --bare on bundle scripts.
# v24: slightly stronger post-filter (refractory + recent-era min evidence) without changing labels/OHLCV.
DEFAULT_SHADOW_EXTRA_ARGS: list[str] = [
    "--cluster-merge-days",
    "10",
    "--refractory-days",
    "12",
    "--enable-recent-precision-layer",
    "--recent-precision-min-evidence",
    "4",
    "--recent-precision-density-window",
    "30",
    "--recent-precision-density-max",
    "1",
]


def load_kospi_yf_rows(csv_path: Path) -> list[dict[str, Any]]:
    import pandas as pd

    df = pd.read_csv(csv_path, skiprows=[1, 2]).rename(
        columns={"Price": "date", "Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"}
    )
    rows: list[dict[str, Any]] = []
    for r in df[["date", "open", "high", "low", "close", "volume"]].dropna().itertuples(index=False):
        rows.append(
            {
                "date": str(r.date)[:10],
                "open": float(r.open),
                "high": float(r.high),
                "low": float(r.low),
                "close": float(r.close),
                "volume": float(r.volume),
            }
        )
    return rows


def run_windows(
    *,
    rows: list[dict[str, Any]],
    windows: list[tuple[str, str, str]],
    script: Path,
    out_dir: Path,
    extra: list[str],
    input_prefix: str,
) -> list[dict[str, Any]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    per: list[dict[str, Any]] = []
    for wname, s, e in windows:
        sub = [r for r in rows if s <= r["date"] <= e]
        p_in = out_dir / f"{wname}_{input_prefix}_input.json"
        p_in.write_text(json.dumps(sub, ensure_ascii=False, indent=2), encoding="utf-8")
        cmd = [sys.executable, str(script), "--input-json", str(p_in), "--out-dir", str(out_dir)] + extra
        cp = subprocess.run(cmd, capture_output=True, text=True)
        if cp.returncode != 0:
            raise RuntimeError(cp.stderr or cp.stdout or f"exit {cp.returncode}")
        m = json.loads(cp.stdout)["metrics"]
        per.append({"window": wname, "period": [s, e], "rows": len(sub), "metrics": m})
    return per


def aggregate_cost_metrics(
    per: list[dict[str, Any]],
    *,
    load_cost_coeff: float = 4.8,
    false_cost_coeff: float = 1.5,
    min_cost_efficiency_score: float = 0.35,
) -> dict[str, Any]:
    n = len(per)
    if n == 0:
        return {
            "avg_crash_warning_recall": 0.0,
            "avg_precrash_zone_precision": 0.0,
            "avg_hit_direction_rate": 0.0,
            "avg_warning_load_ratio": 0.0,
            "avg_false_alert_density": 0.0,
            "cost_efficiency_score": 0.0,
            "pass_cost_gate": False,
        }
    avg_recall = sum(x["metrics"]["crash_warning_recall"] for x in per) / n
    avg_prec = sum(x["metrics"]["precrash_zone_precision"] for x in per) / n
    avg_load = sum(x["metrics"]["warning_load_ratio"] for x in per) / n
    avg_false = sum(x["metrics"]["false_alert_density"] for x in per) / n
    avg_hit_dir = sum(x["metrics"]["hit_direction_rate"] for x in per) / n
    denom = 1.0 + avg_load * float(load_cost_coeff) + avg_false * float(false_cost_coeff)
    cost_eff = (avg_prec / denom) if denom > 0 else 0.0
    pass_gate = cost_eff >= float(min_cost_efficiency_score)
    return {
        "avg_crash_warning_recall": round(avg_recall, 6),
        "avg_precrash_zone_precision": round(avg_prec, 6),
        "avg_hit_direction_rate": round(avg_hit_dir, 6),
        "avg_warning_load_ratio": round(avg_load, 6),
        "avg_false_alert_density": round(avg_false, 6),
        "cost_efficiency_score": round(cost_eff, 6),
        "pass_cost_gate": pass_gate,
    }
