#!/usr/bin/env python3
"""Promote top-N rows from review priority into active mapping."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Activate top-N station mappings from review priority table.")
    parser.add_argument(
        "--priority-csv",
        default="data/smartfarm_rda_extract_v1/out/station_mapping_review_priority_v1.csv",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=10,
        help="Number of top-ranked rows to activate.",
    )
    parser.add_argument(
        "--output-csv",
        default="data/smartfarm_rda_extract_v1/out/station_zone_mapping_stage_top10_v1.csv",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    src = Path(args.priority_csv)
    if not src.exists():
        raise FileNotFoundError(f"Missing priority csv: {src}")

    df = pd.read_csv(src)
    required = {"review_rank", "farm_id", "zone_id", "agmet_station_name"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Priority CSV missing required columns: {sorted(missing)}")

    df = df.sort_values("review_rank").copy()
    df["is_active"] = False
    if args.top_n > 0:
        top_idx = df.head(args.top_n).index
        df.loc[top_idx, "is_active"] = True

    keep_cols = [
        "farm_id",
        "zone_id",
        "agmet_station_name",
        "is_active",
        "priority",
        "review_rank",
        "review_recommendation",
        "notes",
    ]
    for col in keep_cols:
        if col not in df.columns:
            df[col] = ""
    out_df = df[keep_cols]

    out = Path(args.output_csv)
    out.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"[ok] stage mapping rows: {len(out_df)} -> {out}")
    print(f"[ok] activated rows: {int(out_df['is_active'].sum())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

