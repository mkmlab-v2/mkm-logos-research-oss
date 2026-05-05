#!/usr/bin/env python3
"""Compare KPI impact before/after hybrid gap recovery policy."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate KPI impact of gap policy (skip + small-ffill).")
    parser.add_argument(
        "--zone-weather-csv",
        default="data/smartfarm_rda_extract_v1/out/zone_weather_features_v1.csv",
    )
    parser.add_argument(
        "--thresholds-mm",
        default="1,2,3,4,5,6,8,10",
        help="Comma-separated rain gate thresholds on rain_mm_12h.",
    )
    parser.add_argument(
        "--risk-base-col",
        default="rain_mm_1h",
        choices=("rain_mm_1h", "rain_mm_6h", "rain_mm_12h", "rain_mm_24h"),
    )
    parser.add_argument(
        "--risk-min-mm",
        type=float,
        default=0.1,
    )
    parser.add_argument(
        "--gap-hours-threshold",
        type=float,
        default=3.0,
    )
    parser.add_argument(
        "--small-ffill-max-hours",
        type=float,
        default=6.0,
    )
    parser.add_argument(
        "--output-csv",
        default="data/smartfarm_rda_extract_v1/out/gap_policy_kpi_impact_v1.csv",
    )
    parser.add_argument(
        "--output-json",
        default="data/smartfarm_rda_extract_v1/out/gap_policy_kpi_impact_summary_v1.json",
    )
    return parser.parse_args()


def _expect_exists(path: Path) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")
    return path


def _parse_thresholds(raw: str) -> list[float]:
    vals = sorted({float(x.strip()) for x in raw.split(",") if x.strip()})
    if not vals:
        raise ValueError("No threshold values parsed.")
    return vals


def _safe_ratio(num: int, den: int) -> float | None:
    if den == 0:
        return None
    return num / den


def _compute_metrics(df: pd.DataFrame, thresholds: list[float], risk_base_col: str, risk_min_mm: float, policy_name: str) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    total_rows = int(len(df))
    risk_mask = df[risk_base_col] >= risk_min_mm
    risk_runs = int(risk_mask.sum())

    for threshold in thresholds:
        gate_mask = df["rain_mm_12h"] >= threshold
        gate_runs = int(gate_mask.sum())
        blocked_risky = int((gate_mask & risk_mask).sum())
        blocked_not_risky = int((gate_mask & ~risk_mask).sum())
        rows.append(
            {
                "policy": policy_name,
                "threshold_mm_12h": threshold,
                "total_runs": total_rows,
                "potential_rain_risk_runs": risk_runs,
                "gate_trigger_runs": gate_runs,
                "blocked_and_risky_runs": blocked_risky,
                "blocked_but_not_risky_runs": blocked_not_risky,
                "kpi06_rain_loss_avoidance_ratio": _safe_ratio(blocked_risky, risk_runs),
                "gate_trigger_rate": _safe_ratio(gate_runs, total_rows),
                "gate_precision_like": _safe_ratio(blocked_risky, gate_runs),
                "risk_base_col": risk_base_col,
                "risk_min_mm": risk_min_mm,
            }
        )
    return pd.DataFrame(rows)


def main() -> int:
    args = _parse_args()
    src = _expect_exists(Path(args.zone_weather_csv))
    out_csv = Path(args.output_csv)
    out_json = Path(args.output_json)
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(src)
    for col in ("rain_mm_1h", "rain_mm_6h", "rain_mm_12h", "rain_mm_24h"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    df["agmet_ts_local"] = pd.to_datetime(df["agmet_ts_local"], errors="coerce")
    df = df.dropna(subset=["agmet_ts_local"]).sort_values(["farm_id", "zone_id", "agmet_ts_local"]).reset_index(drop=True)

    if args.risk_base_col not in df.columns:
        raise ValueError(f"Missing risk base column: {args.risk_base_col}")
    if "rain_mm_12h" not in df.columns:
        raise ValueError("Missing required column: rain_mm_12h")

    # Mark gap incidents.
    df["prev_ts_local"] = df.groupby(["farm_id", "zone_id"])["agmet_ts_local"].shift(1)
    df["gap_hours"] = (df["agmet_ts_local"] - df["prev_ts_local"]).dt.total_seconds() / 3600.0
    df["is_gap_incident"] = df["gap_hours"] > args.gap_hours_threshold
    df["is_small_gap"] = df["is_gap_incident"] & (df["gap_hours"] <= args.small_ffill_max_hours)
    df["is_large_gap"] = df["is_gap_incident"] & (df["gap_hours"] > args.small_ffill_max_hours)

    thresholds = _parse_thresholds(args.thresholds_mm)

    baseline_df = df.copy()
    baseline_metrics = _compute_metrics(
        baseline_df, thresholds, args.risk_base_col, args.risk_min_mm, "baseline_no_recovery"
    )

    # Hybrid policy:
    # 1) small gaps: forward-fill rain_mm_12h once at incident point within group
    # 2) large gaps: skip the incident row (non-action window)
    hybrid_df = df.copy()
    for (farm_id, zone_id), group_idx in hybrid_df.groupby(["farm_id", "zone_id"]).groups.items():
        idx = list(group_idx)
        group = hybrid_df.loc[idx]
        # Prepare forward-fill candidate on rain feature only.
        series = group["rain_mm_12h"].copy()
        # For small-gap incident rows, ffill from previous valid value.
        small_incident_mask = group["is_small_gap"].fillna(False)
        if small_incident_mask.any():
            series_ffill = series.ffill()
            series.loc[small_incident_mask] = series_ffill.loc[small_incident_mask]
        hybrid_df.loc[idx, "rain_mm_12h"] = series.values

    # Skip large-gap incident rows
    hybrid_eval = hybrid_df[~hybrid_df["is_large_gap"]].copy()
    hybrid_metrics = _compute_metrics(
        hybrid_eval, thresholds, args.risk_base_col, args.risk_min_mm, "hybrid_skip_large_ffill_small"
    )

    impact = baseline_metrics.merge(
        hybrid_metrics,
        on=["threshold_mm_12h", "risk_base_col", "risk_min_mm"],
        suffixes=("_baseline", "_hybrid"),
    )
    impact["delta_kpi06"] = (
        impact["kpi06_rain_loss_avoidance_ratio_hybrid"] - impact["kpi06_rain_loss_avoidance_ratio_baseline"]
    )
    impact["delta_gate_trigger_rate"] = impact["gate_trigger_rate_hybrid"] - impact["gate_trigger_rate_baseline"]
    impact["delta_gate_precision_like"] = impact["gate_precision_like_hybrid"] - impact["gate_precision_like_baseline"]

    impact.to_csv(out_csv, index=False, encoding="utf-8-sig")

    best = impact.sort_values(
        by=["kpi06_rain_loss_avoidance_ratio_hybrid", "gate_precision_like_hybrid"],
        ascending=[False, False],
        na_position="last",
    ).head(1)
    best_row = best.to_dict(orient="records")[0] if not best.empty else None

    summary = {
        "schema": "smartfarm_gap_policy_kpi_impact_summary_v1",
        "source_csv": str(src),
        "output_csv": str(out_csv),
        "parameters": {
            "gap_hours_threshold": args.gap_hours_threshold,
            "small_ffill_max_hours": args.small_ffill_max_hours,
            "risk_base_col": args.risk_base_col,
            "risk_min_mm": args.risk_min_mm,
            "thresholds_mm_12h": thresholds,
        },
        "incident_counts": {
            "total_gap_incidents": int(df["is_gap_incident"].sum()),
            "small_gap_incidents": int(df["is_small_gap"].sum()),
            "large_gap_incidents": int(df["is_large_gap"].sum()),
        },
        "row_counts": {
            "baseline_rows": int(len(baseline_df)),
            "hybrid_rows_after_skip": int(len(hybrid_eval)),
            "rows_dropped_by_skip": int(len(baseline_df) - len(hybrid_eval)),
        },
        "best_threshold_by_hybrid": best_row,
        "notes": [
            "Hybrid policy applies ffill only for small gaps and skips large-gap incident rows.",
            "This is replay analysis; live gating still requires explicit forecast feed and telemetry contract.",
        ],
    }
    out_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[ok] impact rows: {len(impact)} -> {out_csv}")
    print(f"[ok] summary: {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

