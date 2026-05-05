#!/usr/bin/env python3
"""Week4 guard checks for smartfarm weather replay artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate week4 data guards for smartfarm replay tables.")
    parser.add_argument(
        "--zone-weather-csv",
        default="data/smartfarm_rda_extract_v1/out/zone_weather_features_v1.csv",
        help="Zone weather feature CSV path.",
    )
    parser.add_argument(
        "--mapping-csv",
        default="data/smartfarm_rda_extract_v1/out/station_zone_mapping_v1.csv",
        help="Station-zone mapping CSV path.",
    )
    parser.add_argument(
        "--max-gap-hours",
        type=float,
        default=3.0,
        help="Warn threshold for time gap between adjacent rows per farm/zone.",
    )
    parser.add_argument(
        "--max-null-rate",
        type=float,
        default=0.1,
        help="Warn threshold for null ratio in key feature columns.",
    )
    parser.add_argument(
        "--output-json",
        default="data/smartfarm_rda_extract_v1/out/week4_data_guard_summary_v1.json",
        help="Output JSON summary path.",
    )
    return parser.parse_args()


def _expect_exists(path: Path) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")
    return path


def main() -> int:
    args = _parse_args()
    zone_path = _expect_exists(Path(args.zone_weather_csv))
    mapping_path = _expect_exists(Path(args.mapping_csv))
    out_path = Path(args.output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    zone = pd.read_csv(zone_path)
    mapping = pd.read_csv(mapping_path)

    zone["agmet_ts_local"] = pd.to_datetime(zone["agmet_ts_local"], errors="coerce")
    zone = zone.sort_values(["farm_id", "zone_id", "agmet_ts_local"]).reset_index(drop=True)

    checks: dict[str, dict[str, object]] = {}

    # 1) Mapping coverage
    mapped_pairs = set(zip(mapping["farm_id"], mapping["zone_id"]))
    data_pairs = set(zip(zone["farm_id"], zone["zone_id"]))
    uncovered_pairs = sorted(list(data_pairs - mapped_pairs))
    mapping_ok = len(uncovered_pairs) == 0 and len(data_pairs) > 0
    checks["mapping_coverage"] = {
        "ok": mapping_ok,
        "data_zone_pairs": len(data_pairs),
        "mapping_zone_pairs": len(mapped_pairs),
        "uncovered_pairs_count": len(uncovered_pairs),
        "uncovered_pairs": uncovered_pairs[:20],
    }

    # 2) Timestamp validity and ordering
    ts_null_count = int(zone["agmet_ts_local"].isna().sum())
    checks["timestamp_parse"] = {
        "ok": ts_null_count == 0,
        "null_count": ts_null_count,
    }

    # 3) Duplicate key rows
    dup_count = int(zone.duplicated(subset=["farm_id", "zone_id", "agmet_ts_local"]).sum())
    checks["duplicate_zone_timestamp"] = {
        "ok": dup_count == 0,
        "duplicate_count": dup_count,
    }

    # 4) Gap check
    zone["prev_ts"] = zone.groupby(["farm_id", "zone_id"])["agmet_ts_local"].shift(1)
    zone["gap_hours"] = (zone["agmet_ts_local"] - zone["prev_ts"]).dt.total_seconds() / 3600.0
    large_gaps = zone[zone["gap_hours"] > args.max_gap_hours]
    max_gap = float(zone["gap_hours"].max()) if zone["gap_hours"].notna().any() else 0.0
    checks["time_gap"] = {
        "ok": large_gaps.empty,
        "max_gap_hours": max_gap,
        "threshold_hours": args.max_gap_hours,
        "large_gap_count": int(len(large_gaps)),
    }

    # 5) Null rate in key columns
    key_cols = ["rain_mm_1h", "rain_mm_12h", "air_temp_c", "relative_humidity_pct"]
    null_rates: dict[str, float] = {}
    null_fail_cols: list[str] = []
    for col in key_cols:
        if col in zone.columns:
            rate = float(zone[col].isna().mean())
            null_rates[col] = rate
            if rate > args.max_null_rate:
                null_fail_cols.append(col)
    checks["null_rate"] = {
        "ok": len(null_fail_cols) == 0,
        "max_null_rate": args.max_null_rate,
        "null_rates": null_rates,
        "failing_columns": null_fail_cols,
    }

    overall_ok = all(item.get("ok", False) for item in checks.values())
    report = {
        "schema": "smartfarm_week4_data_guard_summary_v1",
        "inputs": {"zone_weather_csv": str(zone_path), "mapping_csv": str(mapping_path)},
        "counts": {"rows": int(len(zone))},
        "checks": checks,
        "overall_ok": overall_ok,
        "status": "PASS" if overall_ok else "WARN_OR_FAIL",
    }
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[ok] guard summary -> {out_path}")
    print(f"[ok] status={report['status']}")
    return 0 if overall_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())

