#!/usr/bin/env python3
"""Evaluate rain-gate threshold sweep and KPI-06 style metrics.

Input:
  zone_weather_features_v1.csv from build_smartfarm_zone_weather_features_v1.py

Output:
  - rain_gate_threshold_sweep_v1.csv
  - rain_gate_threshold_sweep_summary_v1.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate rain-gate threshold sensitivity and KPI metrics.")
    parser.add_argument(
        "--zone-weather-csv",
        default="data/smartfarm_rda_extract_v1/out/zone_weather_features_v1.csv",
        help="Zone weather feature table path.",
    )
    parser.add_argument(
        "--output-dir",
        default="data/smartfarm_rda_extract_v1/out",
        help="Output directory.",
    )
    parser.add_argument(
        "--thresholds-mm",
        default="1,2,3,4,5,6,8,10",
        help="Comma-separated rain_mm_12h thresholds for sweep.",
    )
    parser.add_argument(
        "--risk-base-col",
        default="rain_mm_1h",
        choices=("rain_mm_1h", "rain_mm_6h", "rain_mm_12h", "rain_mm_24h"),
        help="Observed rain column used to define potential_rain_risk_runs.",
    )
    parser.add_argument(
        "--risk-min-mm",
        type=float,
        default=0.1,
        help="Potential rain-risk run if risk_base_col >= this value.",
    )
    return parser.parse_args()


def _expect_exists(path: Path) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")
    return path


def _parse_thresholds(raw: str) -> list[float]:
    values: list[float] = []
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        values.append(float(token))
    if not values:
        raise ValueError("No valid threshold values parsed.")
    return sorted(set(values))


def _safe_ratio(num: int, den: int) -> float | None:
    if den == 0:
        return None
    return num / den


def main() -> int:
    args = _parse_args()
    source_path = _expect_exists(Path(args.zone_weather_csv))
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(source_path)
    for col in ("rain_mm_1h", "rain_mm_6h", "rain_mm_12h", "rain_mm_24h"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    if "rain_mm_12h" not in df.columns:
        raise ValueError("Input does not contain required column: rain_mm_12h")
    if args.risk_base_col not in df.columns:
        raise ValueError(f"Input does not contain risk base column: {args.risk_base_col}")

    thresholds = _parse_thresholds(args.thresholds_mm)
    potential_risk_mask = df[args.risk_base_col] >= args.risk_min_mm
    total_rows = int(len(df))
    potential_risk_runs = int(potential_risk_mask.sum())

    rows: list[dict[str, object]] = []
    for threshold in thresholds:
        gate_trigger_mask = df["rain_mm_12h"] >= threshold
        gate_trigger_runs = int(gate_trigger_mask.sum())
        blocked_and_risky_runs = int((gate_trigger_mask & potential_risk_mask).sum())
        blocked_but_not_risky_runs = int((gate_trigger_mask & ~potential_risk_mask).sum())

        kpi06_rain_loss_avoidance_ratio = _safe_ratio(blocked_and_risky_runs, potential_risk_runs)
        gate_trigger_rate = _safe_ratio(gate_trigger_runs, total_rows)
        gate_precision_like = _safe_ratio(blocked_and_risky_runs, gate_trigger_runs)

        rows.append(
            {
                "threshold_mm_12h": threshold,
                "total_runs": total_rows,
                "potential_rain_risk_runs": potential_risk_runs,
                "gate_trigger_runs": gate_trigger_runs,
                "blocked_and_risky_runs": blocked_and_risky_runs,
                "blocked_but_not_risky_runs": blocked_but_not_risky_runs,
                "kpi06_rain_loss_avoidance_ratio": kpi06_rain_loss_avoidance_ratio,
                "gate_trigger_rate": gate_trigger_rate,
                "gate_precision_like": gate_precision_like,
                "risk_base_col": args.risk_base_col,
                "risk_min_mm": args.risk_min_mm,
            }
        )

    sweep_df = pd.DataFrame(rows)
    sweep_out = output_dir / "rain_gate_threshold_sweep_v1.csv"
    sweep_df.to_csv(sweep_out, index=False, encoding="utf-8-sig")

    best_row = sweep_df.sort_values(
        by=["kpi06_rain_loss_avoidance_ratio", "gate_precision_like"],
        ascending=[False, False],
        na_position="last",
    ).head(1)
    best = best_row.iloc[0].to_dict() if not best_row.empty else None

    summary = {
        "schema": "smartfarm_rain_gate_threshold_sweep_summary_v1",
        "source": str(source_path),
        "sweep_csv": str(sweep_out),
        "thresholds_mm_12h": thresholds,
        "risk_definition": {
            "risk_base_col": args.risk_base_col,
            "risk_min_mm": args.risk_min_mm,
            "rule": "potential_rain_risk_run := risk_base_col >= risk_min_mm",
        },
        "counts": {
            "total_runs": total_rows,
            "potential_rain_risk_runs": potential_risk_runs,
        },
        "best_candidate_by_ratio_then_precision": best,
        "notes": [
            "kpi06_rain_loss_avoidance_ratio follows KPI-06 spirit: blocked due to rain gate among potential rain-risk runs.",
            "This is replay analytics based on observed rain features, not live forecast performance.",
            "For production gating, compare this with actual forecast feed and field outcomes before policy change.",
        ],
    }
    summary_out = output_dir / "rain_gate_threshold_sweep_summary_v1.json"
    summary_out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[ok] sweep rows: {len(sweep_df)} -> {sweep_out}")
    print(f"[ok] summary: {summary_out}")
    if best is not None:
        print(
            "[ok] best candidate "
            f"threshold={best.get('threshold_mm_12h')} "
            f"kpi06={best.get('kpi06_rain_loss_avoidance_ratio')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

