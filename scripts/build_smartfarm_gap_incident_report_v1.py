#!/usr/bin/env python3
"""Extract time-gap incidents from zone weather features."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build gap incident report for smartfarm zone weather timeline.")
    parser.add_argument(
        "--zone-weather-csv",
        default="data/smartfarm_rda_extract_v1/out/zone_weather_features_v1.csv",
        help="Zone weather feature CSV path.",
    )
    parser.add_argument(
        "--gap-hours-threshold",
        type=float,
        default=3.0,
        help="Gap threshold in hours.",
    )
    parser.add_argument(
        "--output-csv",
        default="data/smartfarm_rda_extract_v1/out/gap_incident_report_v1.csv",
        help="Gap incident report CSV path.",
    )
    parser.add_argument(
        "--output-json",
        default="data/smartfarm_rda_extract_v1/out/gap_incident_report_summary_v1.json",
        help="Gap incident summary JSON path.",
    )
    return parser.parse_args()


def _expect_exists(path: Path) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")
    return path


def main() -> int:
    args = _parse_args()
    source_path = _expect_exists(Path(args.zone_weather_csv))
    out_csv = Path(args.output_csv)
    out_json = Path(args.output_json)
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(source_path)
    df["agmet_ts_local"] = pd.to_datetime(df["agmet_ts_local"], errors="coerce")
    df = df.dropna(subset=["agmet_ts_local"]).sort_values(["farm_id", "zone_id", "agmet_ts_local"]).reset_index(drop=True)

    df["prev_ts_local"] = df.groupby(["farm_id", "zone_id"])["agmet_ts_local"].shift(1)
    df["gap_hours"] = (df["agmet_ts_local"] - df["prev_ts_local"]).dt.total_seconds() / 3600.0
    incidents = df[df["gap_hours"] > args.gap_hours_threshold].copy()

    incidents["incident_id"] = (
        incidents["farm_id"].astype(str)
        + "__"
        + incidents["zone_id"].astype(str)
        + "__"
        + incidents["agmet_ts_local"].dt.strftime("%Y%m%d%H")
    )
    incidents["missing_hours_est"] = (incidents["gap_hours"] - 1.0).round(0).clip(lower=1).astype("Int64")

    out_cols = [
        "incident_id",
        "farm_id",
        "zone_id",
        "agmet_station_name",
        "prev_ts_local",
        "agmet_ts_local",
        "gap_hours",
        "missing_hours_est",
        "rain_mm_1h",
        "rain_mm_12h",
        "source_sheet",
    ]
    incidents[out_cols].to_csv(out_csv, index=False, encoding="utf-8-sig")

    by_zone = (
        incidents.groupby(["farm_id", "zone_id"], as_index=False)
        .agg(
            incident_count=("incident_id", "count"),
            max_gap_hours=("gap_hours", "max"),
            avg_gap_hours=("gap_hours", "mean"),
        )
        .sort_values(["incident_count", "max_gap_hours"], ascending=[False, False])
    )
    top_zones = by_zone.head(10).to_dict(orient="records")

    summary = {
        "schema": "smartfarm_gap_incident_report_summary_v1",
        "source_csv": str(source_path),
        "output_csv": str(out_csv),
        "gap_hours_threshold": args.gap_hours_threshold,
        "counts": {
            "total_rows": int(len(df)),
            "incident_rows": int(len(incidents)),
            "zone_count_with_incidents": int(by_zone.shape[0]),
        },
        "max_gap_hours_overall": float(incidents["gap_hours"].max()) if not incidents.empty else 0.0,
        "top_zones": top_zones,
    }
    out_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[ok] incidents: {len(incidents):,} -> {out_csv}")
    print(f"[ok] summary: {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

