#!/usr/bin/env python3
"""Build station->farm/zone mapping template from canonical weather stations."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create mapping template for multi-station smartfarm setup.")
    parser.add_argument(
        "--weather-csv",
        default="data/smartfarm_rda_extract_v1/out/agmet_hourly_canonical.csv",
    )
    parser.add_argument(
        "--output-csv",
        default="data/smartfarm_rda_extract_v1/out/station_zone_mapping_template_v1.csv",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    weather_path = Path(args.weather_csv)
    if not weather_path.exists():
        raise FileNotFoundError(f"Missing weather csv: {weather_path}")

    df = pd.read_csv(weather_path, usecols=["agmet_station_name"])
    stations = sorted(df["agmet_station_name"].dropna().unique().tolist())

    template = pd.DataFrame(
        {
            "farm_id": ["" for _ in stations],
            "zone_id": ["" for _ in stations],
            "agmet_station_name": stations,
            "priority": [1 for _ in stations],
            "is_active": [True for _ in stations],
            "notes": ["" for _ in stations],
        }
    )
    out_path = Path(args.output_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    template.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"[ok] stations: {len(stations)} -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

