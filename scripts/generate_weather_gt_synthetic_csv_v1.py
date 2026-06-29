#!/usr/bin/env python3
"""Generate synthetic weather CSV for pipeline stress (not real KMA data)."""
from __future__ import annotations

import argparse
import csv
import math
import sys
from datetime import datetime, timedelta
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--days", type=int, default=120)
    ap.add_argument("--start-date", default="2015-06-01")
    ns = ap.parse_args()
    start = datetime.strptime(ns.start_date, "%Y-%m-%d")
    ns.output.parent.mkdir(parents=True, exist_ok=True)
    with ns.output.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["observation_date", "precip_mm_day"])
        for i in range(ns.days):
            d = start + timedelta(days=i)
            precip = max(0.0, 6.0 + 7.0 * math.sin(i / 12.0) - i * 0.03)
            writer.writerow([d.strftime("%Y-%m-%d"), f"{precip:.2f}"])
    print(f"WROTE: {ns.output} rows={ns.days}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
