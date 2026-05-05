#!/usr/bin/env python3
"""Build zone-level weather features from canonical agmet hourly data.

Required inputs:
  1) Canonical weather table from etl_smartfarm_rda_xlsx_to_canonical_v1.py
  2) Station-to-zone mapping CSV

This script computes rolling precipitation windows and emits a zone-hour table
that can be used for replay inputs such as forecast_rain_mm_12h.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


MAPPING_REQUIRED_COLUMNS = ("farm_id", "zone_id", "agmet_station_name")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build zone weather features (rolling rain) from canonical weather.")
    parser.add_argument(
        "--weather-csv",
        default="data/smartfarm_rda_extract_v1/out/agmet_hourly_canonical.csv",
        help="Canonical weather CSV path.",
    )
    parser.add_argument(
        "--mapping-csv",
        default="data/smartfarm_rda_extract_v1/out/station_zone_mapping_v1.csv",
        help="Station to farm/zone mapping CSV path.",
    )
    parser.add_argument(
        "--output-dir",
        default="data/smartfarm_rda_extract_v1/out",
        help="Output directory for feature table and summary.",
    )
    parser.add_argument(
        "--max-weather-rows",
        type=int,
        default=None,
        help="Optional read cap for weather rows (smoke/dev).",
    )
    parser.add_argument(
        "--recent-hours-from-latest",
        type=int,
        default=None,
        help="Optional filter window anchored at latest weather timestamp (e.g. 96).",
    )
    return parser.parse_args()


def _expect_exists(path: Path) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")
    return path


def _validate_mapping_columns(df: pd.DataFrame) -> None:
    missing = [c for c in MAPPING_REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Mapping CSV missing required columns: {missing}")
    if "is_active" not in df.columns:
        raise ValueError("Mapping CSV missing required column: is_active")


def _coerce_weather_types(df: pd.DataFrame) -> pd.DataFrame:
    for col in ("air_temp_c", "relative_humidity_pct", "solar_radiation", "precip_mm_hourly"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df["agmet_ts_local"] = pd.to_datetime(df["agmet_ts_local"], errors="coerce")
    return df


def main() -> int:
    args = _parse_args()
    weather_path = _expect_exists(Path(args.weather_csv))
    mapping_path = _expect_exists(Path(args.mapping_csv))
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    weather = pd.read_csv(weather_path, nrows=args.max_weather_rows)
    mapping = pd.read_csv(mapping_path)
    _validate_mapping_columns(mapping)
    mapping["is_active"] = mapping["is_active"].astype(str).str.lower().isin(("true", "1", "yes", "y"))
    active_mapping = mapping[mapping["is_active"]].copy()
    inactive_rows = int(len(mapping) - len(active_mapping))
    if active_mapping.empty:
        raise ValueError("No active mapping rows found. Set at least one row with is_active=True.")

    weather = _coerce_weather_types(weather)
    weather = weather.dropna(subset=["agmet_station_name", "agmet_ts_local"])
    if args.recent_hours_from_latest is not None:
        latest_ts = weather["agmet_ts_local"].max()
        if pd.notna(latest_ts):
            cutoff_ts = latest_ts - pd.Timedelta(hours=args.recent_hours_from_latest)
            weather = weather[weather["agmet_ts_local"] >= cutoff_ts].copy()
    weather = weather.sort_values(["agmet_station_name", "agmet_ts_local"]).reset_index(drop=True)

    weather["rain_mm_1h"] = weather["precip_mm_hourly"].fillna(0.0)
    weather["rain_mm_6h"] = (
        weather.groupby("agmet_station_name")["rain_mm_1h"].rolling(window=6, min_periods=1).sum().reset_index(level=0, drop=True)
    )
    weather["rain_mm_12h"] = (
        weather.groupby("agmet_station_name")["rain_mm_1h"].rolling(window=12, min_periods=1).sum().reset_index(level=0, drop=True)
    )
    weather["rain_mm_24h"] = (
        weather.groupby("agmet_station_name")["rain_mm_1h"].rolling(window=24, min_periods=1).sum().reset_index(level=0, drop=True)
    )

    zone_weather = weather.merge(
        active_mapping[list(MAPPING_REQUIRED_COLUMNS)],
        on="agmet_station_name",
        how="inner",
    )

    zone_weather = zone_weather[
        [
            "farm_id",
            "zone_id",
            "agmet_station_name",
            "agmet_ts_local",
            "agmet_ts_utc",
            "air_temp_c",
            "relative_humidity_pct",
            "solar_radiation",
            "rain_mm_1h",
            "rain_mm_6h",
            "rain_mm_12h",
            "rain_mm_24h",
            "source_sheet",
        ]
    ].sort_values(["farm_id", "zone_id", "agmet_ts_local"])

    zone_out = output_dir / "zone_weather_features_v1.csv"
    zone_weather.to_csv(zone_out, index=False, encoding="utf-8-sig")

    replay_out = output_dir / "zone_weather_replay_inputs_v1.csv"
    replay = zone_weather[
        ["farm_id", "zone_id", "agmet_ts_utc", "rain_mm_12h", "agmet_station_name"]
    ].rename(columns={"rain_mm_12h": "forecast_rain_mm_12h"})
    replay.to_csv(replay_out, index=False, encoding="utf-8-sig")

    summary = {
        "schema": "smartfarm_zone_weather_features_summary_v1",
        "weather_input": str(weather_path),
        "mapping_input": str(mapping_path),
        "zone_output": str(zone_out),
        "replay_output": str(replay_out),
        "rows": {
            "weather_input": int(len(weather)),
            "mapping": int(len(mapping)),
            "mapping_active": int(len(active_mapping)),
            "mapping_inactive_ignored": inactive_rows,
            "zone_output": int(len(zone_weather)),
            "replay_output": int(len(replay)),
        },
        "windowing": {
            "recent_hours_from_latest": args.recent_hours_from_latest,
        },
        "mapping_coverage": {
            "mapped_station_count": int(zone_weather["agmet_station_name"].nunique()) if not zone_weather.empty else 0,
            "mapping_station_count_active": int(active_mapping["agmet_station_name"].nunique()),
            "mapping_station_count_total": int(mapping["agmet_station_name"].nunique()),
        },
        "notes": [
            "forecast_rain_mm_12h here is historical rolling observed precipitation, not a forecast model output.",
            "Use for replay/analysis lane; keep live control pipeline on explicit forecast feed plus telemetry gates.",
        ],
    }
    summary_path = output_dir / "zone_weather_features_summary_v1.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[ok] zone weather rows: {len(zone_weather):,} -> {zone_out}")
    print(f"[ok] replay rows: {len(replay):,} -> {replay_out}")
    print(f"[ok] summary: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

