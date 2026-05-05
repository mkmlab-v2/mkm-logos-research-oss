#!/usr/bin/env python3
"""Build review-priority list for station mapping activation."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create mapping review priority ranked by data density/freshness/gaps.")
    parser.add_argument(
        "--weather-csv",
        default="data/smartfarm_rda_extract_v1/out/agmet_hourly_canonical.csv",
    )
    parser.add_argument(
        "--mapping-csv",
        default="data/smartfarm_rda_extract_v1/out/station_zone_mapping_draft_v1.csv",
    )
    parser.add_argument(
        "--output-csv",
        default="data/smartfarm_rda_extract_v1/out/station_mapping_review_priority_v1.csv",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    weather_path = Path(args.weather_csv)
    mapping_path = Path(args.mapping_csv)
    if not weather_path.exists():
        raise FileNotFoundError(f"Missing weather csv: {weather_path}")
    if not mapping_path.exists():
        raise FileNotFoundError(f"Missing mapping csv: {mapping_path}")

    weather = pd.read_csv(weather_path, usecols=["agmet_station_name", "agmet_ts_utc"])
    weather["agmet_ts_utc"] = pd.to_datetime(weather["agmet_ts_utc"], errors="coerce", utc=True)
    weather = weather.dropna(subset=["agmet_station_name", "agmet_ts_utc"]).sort_values(
        ["agmet_station_name", "agmet_ts_utc"]
    )
    weather["prev_ts"] = weather.groupby("agmet_station_name")["agmet_ts_utc"].shift(1)
    weather["gap_hours"] = (weather["agmet_ts_utc"] - weather["prev_ts"]).dt.total_seconds() / 3600.0

    agg = (
        weather.groupby("agmet_station_name", as_index=False)
        .agg(
            row_count=("agmet_ts_utc", "count"),
            latest_ts_utc=("agmet_ts_utc", "max"),
            max_gap_hours=("gap_hours", "max"),
            large_gap_count=("gap_hours", lambda s: int((s > 3).sum())),
        )
        .fillna({"max_gap_hours": 0.0, "large_gap_count": 0})
    )

    now = pd.Timestamp.now(tz="UTC")
    agg["freshness_hours"] = (now - agg["latest_ts_utc"]).dt.total_seconds() / 3600.0
    agg["data_density_score"] = agg["row_count"].rank(method="dense", ascending=False)
    agg["freshness_score"] = agg["freshness_hours"].rank(method="dense", ascending=True)
    agg["gap_penalty_score"] = agg["large_gap_count"].rank(method="dense", ascending=False)
    agg["priority_score"] = (
        0.5 * agg["data_density_score"]
        + 0.3 * agg["freshness_score"]
        - 0.2 * agg["gap_penalty_score"]
    )

    mapping = pd.read_csv(mapping_path)
    out = mapping.merge(agg, on="agmet_station_name", how="left")
    out["is_active"] = out.get("is_active", False)
    out["review_recommendation"] = "REVIEW_FIRST"
    out.loc[out["large_gap_count"].fillna(0) <= 2, "review_recommendation"] = "CANDIDATE_EARLY"
    out = out.sort_values(
        ["review_recommendation", "priority_score", "row_count"],
        ascending=[True, False, False],
    )
    out.insert(0, "review_rank", range(1, len(out) + 1))

    output_path = Path(args.output_csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"[ok] review priority rows: {len(out)} -> {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

