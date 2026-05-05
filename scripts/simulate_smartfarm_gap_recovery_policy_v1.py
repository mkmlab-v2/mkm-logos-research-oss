#!/usr/bin/env python3
"""Simulate gap recovery policies on zone weather timeline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


NUMERIC_FILL_COLS = ["air_temp_c", "relative_humidity_pct", "solar_radiation", "rain_mm_1h", "rain_mm_12h", "rain_mm_24h"]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Simulate FFILL/SKIP/FLAG gap recovery policy outcomes.")
    parser.add_argument(
        "--zone-weather-csv",
        default="data/smartfarm_rda_extract_v1/out/zone_weather_features_v1.csv",
    )
    parser.add_argument(
        "--gap-hours-threshold",
        type=float,
        default=3.0,
        help="Threshold above which a segment is treated as a gap incident.",
    )
    parser.add_argument(
        "--ffill-max-hours",
        type=float,
        default=6.0,
        help="Maximum gap size allowed for FFILL policy.",
    )
    parser.add_argument(
        "--output-csv",
        default="data/smartfarm_rda_extract_v1/out/gap_recovery_policy_simulation_v1.csv",
    )
    parser.add_argument(
        "--output-json",
        default="data/smartfarm_rda_extract_v1/out/gap_recovery_policy_simulation_summary_v1.json",
    )
    return parser.parse_args()


def _expect_exists(path: Path) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")
    return path


def _safe_ratio(num: int, den: int) -> float | None:
    if den == 0:
        return None
    return num / den


def main() -> int:
    args = _parse_args()
    src = _expect_exists(Path(args.zone_weather_csv))
    out_csv = Path(args.output_csv)
    out_json = Path(args.output_json)
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(src)
    df["agmet_ts_local"] = pd.to_datetime(df["agmet_ts_local"], errors="coerce")
    df = df.dropna(subset=["agmet_ts_local"]).sort_values(["farm_id", "zone_id", "agmet_ts_local"]).reset_index(drop=True)

    df["prev_ts_local"] = df.groupby(["farm_id", "zone_id"])["agmet_ts_local"].shift(1)
    df["gap_hours"] = (df["agmet_ts_local"] - df["prev_ts_local"]).dt.total_seconds() / 3600.0
    incidents = df[df["gap_hours"] > args.gap_hours_threshold].copy()

    total_incidents = int(len(incidents))
    if total_incidents == 0:
        empty = pd.DataFrame(
            [
                {
                    "policy": "ffill",
                    "total_incidents": 0,
                    "resolved_incidents": 0,
                    "unresolved_incidents": 0,
                    "resolution_rate": None,
                },
                {
                    "policy": "skip",
                    "total_incidents": 0,
                    "resolved_incidents": 0,
                    "unresolved_incidents": 0,
                    "resolution_rate": None,
                },
                {
                    "policy": "flag_only",
                    "total_incidents": 0,
                    "resolved_incidents": 0,
                    "unresolved_incidents": 0,
                    "resolution_rate": None,
                },
            ]
        )
        empty.to_csv(out_csv, index=False, encoding="utf-8-sig")
        summary = {
            "schema": "smartfarm_gap_recovery_policy_simulation_summary_v1",
            "source_csv": str(src),
            "status": "NO_INCIDENTS",
        }
        out_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[ok] no incidents -> {out_csv}")
        return 0

    incidents["is_small_gap_for_ffill"] = incidents["gap_hours"] <= args.ffill_max_hours
    incidents["estimated_missing_rows"] = (incidents["gap_hours"] - 1.0).round(0).clip(lower=1).astype(int)

    # Policy simulation logic:
    # - FFILL: only resolves gaps <= ffill_max_hours
    # - SKIP: resolves all by dropping affected decision windows (coverage loss)
    # - FLAG_ONLY: resolves none, but all incidents are flagged
    ffill_resolved = int(incidents["is_small_gap_for_ffill"].sum())
    skip_resolved = total_incidents
    flag_resolved = 0

    policy_rows = [
        {
            "policy": "ffill",
            "total_incidents": total_incidents,
            "resolved_incidents": ffill_resolved,
            "unresolved_incidents": total_incidents - ffill_resolved,
            "resolution_rate": _safe_ratio(ffill_resolved, total_incidents),
            "estimated_rows_touched": int(incidents.loc[incidents["is_small_gap_for_ffill"], "estimated_missing_rows"].sum()),
            "coverage_loss_rows": 0,
            "notes": f"Resolve only incidents with gap_hours <= {args.ffill_max_hours}.",
        },
        {
            "policy": "skip",
            "total_incidents": total_incidents,
            "resolved_incidents": skip_resolved,
            "unresolved_incidents": 0,
            "resolution_rate": _safe_ratio(skip_resolved, total_incidents),
            "estimated_rows_touched": 0,
            "coverage_loss_rows": int(incidents["estimated_missing_rows"].sum()),
            "notes": "Treat all incidents as non-action windows; safest but loses coverage.",
        },
        {
            "policy": "flag_only",
            "total_incidents": total_incidents,
            "resolved_incidents": flag_resolved,
            "unresolved_incidents": total_incidents,
            "resolution_rate": _safe_ratio(flag_resolved, total_incidents),
            "estimated_rows_touched": 0,
            "coverage_loss_rows": 0,
            "notes": "No correction, only monitoring/escalation tags.",
        },
    ]
    out_df = pd.DataFrame(policy_rows)
    out_df.to_csv(out_csv, index=False, encoding="utf-8-sig")

    zone_incident = (
        incidents.groupby(["farm_id", "zone_id"], as_index=False)
        .agg(
            incident_count=("gap_hours", "count"),
            max_gap_hours=("gap_hours", "max"),
            avg_gap_hours=("gap_hours", "mean"),
        )
        .sort_values(["incident_count", "max_gap_hours"], ascending=[False, False])
    )

    summary = {
        "schema": "smartfarm_gap_recovery_policy_simulation_summary_v1",
        "source_csv": str(src),
        "parameters": {
            "gap_hours_threshold": args.gap_hours_threshold,
            "ffill_max_hours": args.ffill_max_hours,
        },
        "counts": {
            "total_rows": int(len(df)),
            "total_incidents": total_incidents,
        },
        "best_policy_by_resolution": out_df.sort_values(
            by=["resolution_rate", "coverage_loss_rows"],
            ascending=[False, True],
            na_position="last",
        ).head(1).to_dict(orient="records")[0],
        "per_zone_incident_top10": zone_incident.head(10).to_dict(orient="records"),
        "output_csv": str(out_csv),
    }
    out_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[ok] policy simulation rows: {len(out_df)} -> {out_csv}")
    print(f"[ok] summary: {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

