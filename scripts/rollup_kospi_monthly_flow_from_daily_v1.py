#!/usr/bin/env python3
"""Roll up kospi_daily_flow_external.csv into kospi_monthly_flow_external.csv [HYPO]."""
from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DAILY = ROOT / "research/market_data/kospi_daily_flow_external.csv"
DEFAULT_MONTHLY = ROOT / "research/market_data/kospi_monthly_flow_external.csv"
MONTHLY_FIELDS = (
    "ym",
    "foreign_net_buy",
    "institution_net_buy",
    "program_net_buy",
    "usdkrw_change_pct",
    "rates_front_end_change_bp",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--daily-csv", type=Path, default=DEFAULT_DAILY)
    ap.add_argument("--monthly-csv", type=Path, default=DEFAULT_MONTHLY)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    daily = args.daily_csv if args.daily_csv.is_absolute() else ROOT / args.daily_csv
    monthly = args.monthly_csv if args.monthly_csv.is_absolute() else ROOT / args.monthly_csv
    if not daily.is_file():
        print(f"missing daily: {daily}", file=sys.stderr)
        return 2

    sums: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    counts: dict[str, int] = defaultdict(int)
    with daily.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            d = str(row.get("date") or "")[:10]
            if len(d) != 10:
                continue
            ym = d[:7]
            counts[ym] += 1
            for col in ("foreign_net_buy", "institution_net_buy", "program_net_buy"):
                try:
                    sums[ym][col] += float(row.get(col) or 0.0)
                except (TypeError, ValueError):
                    pass

    existing: dict[str, dict[str, str]] = {}
    if monthly.is_file():
        with monthly.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                ym = str(row.get("ym") or "").strip()
                if ym:
                    existing[ym] = {k: str(row.get(k) or "") for k in MONTHLY_FIELDS}

    updated: list[str] = []
    for ym in sorted(sums):
        agg = sums[ym]
        n = counts[ym]
        note_suffix = f"daily_rollup_n={n}"
        prev = existing.get(ym, {})
        row = {
            "ym": ym,
            "foreign_net_buy": str(round(agg["foreign_net_buy"], 1)),
            "institution_net_buy": str(round(agg["institution_net_buy"], 1)),
            "program_net_buy": str(round(agg["program_net_buy"], 1)),
            "usdkrw_change_pct": prev.get("usdkrw_change_pct") or "0",
            "rates_front_end_change_bp": prev.get("rates_front_end_change_bp") or "0",
        }
        existing[ym] = row
        updated.append(f"{ym}({note_suffix})")

    rows_out = [existing[k] for k in sorted(existing)]
    if args.dry_run:
        print("dry-run rollup:", ", ".join(updated) or "none")
        return 0

    monthly.parent.mkdir(parents=True, exist_ok=True)
    with monthly.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=MONTHLY_FIELDS)
        w.writeheader()
        w.writerows(rows_out)
    print(f"WROTE: {monthly} updated={updated} at {_utc_now()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
