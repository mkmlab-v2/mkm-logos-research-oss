#!/usr/bin/env python3
"""Validate station-zone mapping quality against canonical weather table."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


REQUIRED_COLS = ["farm_id", "zone_id", "agmet_station_name"]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate mapping csv for multi-station weather joins.")
    parser.add_argument(
        "--mapping-csv",
        default="data/smartfarm_rda_extract_v1/out/station_zone_mapping_v1.csv",
    )
    parser.add_argument(
        "--weather-csv",
        default="data/smartfarm_rda_extract_v1/out/agmet_hourly_canonical.csv",
    )
    parser.add_argument(
        "--output-json",
        default="data/smartfarm_rda_extract_v1/out/station_zone_mapping_validation_v1.json",
    )
    parser.add_argument(
        "--min-coverage-ratio",
        type=float,
        default=0.05,
        help="Minimum mapped_station_ratio_vs_weather to consider PASS (default 5%%).",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    mapping_path = Path(args.mapping_csv)
    weather_path = Path(args.weather_csv)
    if not mapping_path.exists():
        raise FileNotFoundError(f"Missing mapping csv: {mapping_path}")
    if not weather_path.exists():
        raise FileNotFoundError(f"Missing weather csv: {weather_path}")

    mapping = pd.read_csv(mapping_path)
    weather = pd.read_csv(weather_path, usecols=["agmet_station_name"])

    missing_cols = [c for c in REQUIRED_COLS if c not in mapping.columns]
    if missing_cols:
        raise ValueError(f"Mapping missing required columns: {missing_cols}")

    mapping["farm_id"] = mapping["farm_id"].astype(str).str.strip()
    mapping["zone_id"] = mapping["zone_id"].astype(str).str.strip()
    mapping["agmet_station_name"] = mapping["agmet_station_name"].astype(str).str.strip()

    weather_stations = set(weather["agmet_station_name"].dropna().astype(str).str.strip().tolist())
    map_stations = set(mapping["agmet_station_name"].dropna().tolist())

    empty_keys = mapping[(mapping["farm_id"] == "") | (mapping["zone_id"] == "")]
    unknown_stations = sorted([s for s in map_stations if s and s not in weather_stations])
    duplicate_rows = mapping.duplicated(subset=["farm_id", "zone_id", "agmet_station_name"]).sum()

    mapped_ratio = (len(map_stations) / len(weather_stations)) if weather_stations else None
    summary = {
        "schema": "smartfarm_station_mapping_validation_v1",
        "counts": {
            "mapping_rows": int(len(mapping)),
            "weather_station_count": int(len(weather_stations)),
            "mapped_station_count": int(len(map_stations)),
            "empty_key_rows": int(len(empty_keys)),
            "unknown_station_count": int(len(unknown_stations)),
            "duplicate_triplet_rows": int(duplicate_rows),
        },
        "coverage": {
            "mapped_station_ratio_vs_weather": mapped_ratio,
            "min_coverage_ratio": args.min_coverage_ratio,
        },
        "unknown_stations_top20": unknown_stations[:20],
        "status": "PASS",
    }

    coverage_fail = mapped_ratio is not None and mapped_ratio < args.min_coverage_ratio
    summary["coverage"]["coverage_below_min"] = bool(coverage_fail)

    if len(empty_keys) > 0 or len(unknown_stations) > 0 or int(duplicate_rows) > 0 or coverage_fail:
        summary["status"] = "WARN_OR_FAIL"

    out_path = Path(args.output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[ok] mapping validation -> {out_path}")
    print(f"[ok] status={summary['status']}")
    return 0 if summary["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

