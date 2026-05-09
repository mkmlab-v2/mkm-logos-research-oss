#!/usr/bin/env python3
"""Update NEXT_DAY_RET and VOL_EXPAND fields in KOSPI daily log lines."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Update outcome fields for a specific date in daily log file."
    )
    parser.add_argument(
        "--log-path",
        required=True,
        help="Path to daily log file.",
    )
    parser.add_argument(
        "--date",
        required=True,
        help="Target DATE value in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--next-day-ret",
        required=True,
        choices=["+", "-", "0"],
        help="Outcome sign for next day return.",
    )
    parser.add_argument(
        "--vol-expand",
        required=True,
        choices=["Y", "N"],
        help="Whether volatility expanded.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show updated line preview without writing file.",
    )
    return parser.parse_args()


def update_line(
    line: str, target_date: str, next_day_ret: str, vol_expand: str
) -> tuple[str, bool]:
    date_tag = f"[DATE={target_date}]"
    if date_tag not in line:
        return line, False

    updated = re.sub(r"\[NEXT_DAY_RET=[^\]]+\]", f"[NEXT_DAY_RET={next_day_ret}]", line)
    updated = re.sub(r"\[VOL_EXPAND=[^\]]+\]", f"[VOL_EXPAND={vol_expand}]", updated)
    return updated, updated != line


def main() -> int:
    args = parse_args()
    path = Path(args.log_path)
    if not path.exists():
        raise FileNotFoundError(f"Log file not found: {path}")

    lines = path.read_text(encoding="utf-8").splitlines()
    changed = 0
    new_lines: list[str] = []

    for line in lines:
        updated, did_change = update_line(
            line=line,
            target_date=args.date,
            next_day_ret=args.next_day_ret,
            vol_expand=args.vol_expand,
        )
        if did_change:
            changed += 1
            print(f"UPDATED: {updated}")
        new_lines.append(updated)

    if changed == 0:
        print(f"No matching line found for DATE={args.date}")
        return 1

    if changed > 1:
        print(f"Warning: multiple lines updated for DATE={args.date}: {changed}")

    if args.dry_run:
        print("Dry run mode: file not written.")
        return 0

    path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    print(f"Updated file: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

