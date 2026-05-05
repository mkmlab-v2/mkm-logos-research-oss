#!/usr/bin/env python3
"""Apply human review decisions to produce operational mapping file.

Decision priority:
1) approved_active column (if present)
2) is_active column fallback
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def _as_bool_series(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.lower().isin(("true", "1", "yes", "y"))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply reviewed mapping decisions and emit operational mapping CSV.")
    parser.add_argument(
        "--review-csv",
        default="data/smartfarm_rda_extract_v1/out/station_zone_mapping_stage_top10_v1.csv",
        help="Review input CSV (priority/review table).",
    )
    parser.add_argument(
        "--output-csv",
        default="data/smartfarm_rda_extract_v1/out/station_zone_mapping_operational_v1.csv",
        help="Operational mapping CSV output path.",
    )
    parser.add_argument(
        "--require-min-active",
        type=int,
        default=1,
        help="Fail if active rows less than this count.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    src = Path(args.review_csv)
    if not src.exists():
        raise FileNotFoundError(f"Missing review csv: {src}")

    df = pd.read_csv(src)
    required = {"farm_id", "zone_id", "agmet_station_name"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Review CSV missing required columns: {sorted(missing)}")

    if "approved_active" in df.columns:
        active = _as_bool_series(df["approved_active"])
        active_source = "approved_active"
    elif "is_active" in df.columns:
        active = _as_bool_series(df["is_active"])
        active_source = "is_active"
    else:
        raise ValueError("Review CSV must contain either approved_active or is_active column")

    out = df.copy()
    out["is_active"] = active
    active_count = int(out["is_active"].sum())
    if active_count < args.require_min_active:
        raise ValueError(
            f"Active rows too few: {active_count} < require_min_active={args.require_min_active}"
        )

    keep_cols = ["farm_id", "zone_id", "agmet_station_name", "is_active"]
    for optional in ("priority", "review_rank", "review_recommendation", "notes"):
        if optional in out.columns:
            keep_cols.append(optional)
    out = out[keep_cols].sort_values(["is_active", "farm_id", "zone_id"], ascending=[False, True, True])

    dst = Path(args.output_csv)
    dst.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(dst, index=False, encoding="utf-8-sig")

    print(f"[ok] active source: {active_source}")
    print(f"[ok] active rows: {active_count}")
    print(f"[ok] operational mapping -> {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

