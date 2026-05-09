# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.8, K:0.5, M:0.6}
# Balance: 88
# Purpose: Autofill actual returns in MKM Hanwha eval CSV by ticker/date.
# Keywords: csv, evaluation, returns, backfill, automation
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path


DATE_FMT = "%Y-%m-%d"


def _parse_date(v: str) -> datetime:
    return datetime.strptime(v.strip(), DATE_FMT)


def _parse_float(v: str) -> float | None:
    t = (v or "").strip()
    if not t:
        return None
    try:
        return float(t)
    except ValueError:
        return None


def _pct_ret(from_px: float, to_px: float) -> float:
    if from_px == 0:
        return 0.0
    return ((to_px / from_px) - 1.0) * 100.0


def main() -> int:
    ap = argparse.ArgumentParser(description="Autofill actual_next_day_return_pct and actual_3d_return_pct")
    ap.add_argument(
        "--csv-path",
        default="reports/mkm_hanwha_prediction_eval_records_v1.csv",
        help="Target records CSV path",
    )
    ap.add_argument(
        "--overwrite-existing",
        action="store_true",
        help="Overwrite existing actual return fields",
    )
    args = ap.parse_args()

    csv_path = Path(args.csv_path)
    if not csv_path.exists():
        raise SystemExit(f"CSV not found: {csv_path}")

    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames

    if not fieldnames:
        raise SystemExit("CSV header missing.")

    by_ticker: dict[str, list[dict[str, str]]] = defaultdict(list)
    for r in rows:
        by_ticker[(r.get("ticker") or "").strip()].append(r)

    for ticker, items in by_ticker.items():
        if not ticker:
            continue
        items.sort(key=lambda x: _parse_date(x.get("date") or "1970-01-01"))
        closes = [_parse_float(x.get("close_t") or "") for x in items]

        for i, row in enumerate(items):
            cur = closes[i]
            if cur is None:
                continue

            n1 = row.get("actual_next_day_return_pct", "")
            n3 = row.get("actual_3d_return_pct", "")

            if i + 1 < len(items) and closes[i + 1] is not None:
                if args.overwrite_existing or not (n1 or "").strip():
                    row["actual_next_day_return_pct"] = f"{_pct_ret(cur, closes[i + 1]):.6f}"

            if i + 3 < len(items) and closes[i + 3] is not None:
                if args.overwrite_existing or not (n3 or "").strip():
                    row["actual_3d_return_pct"] = f"{_pct_ret(cur, closes[i + 3]):.6f}"

    # Keep stable output ordering: sort by date then ticker
    rows.sort(key=lambda x: (_parse_date(x.get("date") or "1970-01-01"), (x.get("ticker") or "")))

    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"WROTE: {csv_path.resolve()}")
    print("Auto-fill complete (next-day / 3-day returns where possible).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
