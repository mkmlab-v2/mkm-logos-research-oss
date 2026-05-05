#!/usr/bin/env python3
"""Pair-wise temporal guard: aligned news_observation + direction_label_bar rows (same line order).

Research helper — does not prove causal modeling correctness; only catches obvious lookahead
when rows are pre-aligned (same count, matching indices).

Rules:
  --strict-as-of-date-before-label-date:
    date(as_of_utc) < label_date (calendar date of forward-return bar).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path


def _parse_js(line: str) -> dict:
    return json.loads(line.strip())


def _as_of_date(row: dict) -> date:
    s = str(row["as_of_utc"]).strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).date()


def _label_date(row: dict) -> date:
    s = str(row["label_date"]).strip()
    y, m, d = (int(x) for x in s.split("-"))
    return date(y, m, d)


def main() -> int:
    ap = argparse.ArgumentParser(description="Temporal join guard for paired JSONL rows.")
    ap.add_argument("--news-jsonl", type=Path, required=True)
    ap.add_argument("--labels-jsonl", type=Path, required=True)
    ap.add_argument(
        "--strict-as-of-date-before-label-date",
        action="store_true",
        help="Require date(as_of_utc) < label_date for each aligned pair.",
    )
    args = ap.parse_args()

    n_lines = [
        ln for ln in Path(args.news_jsonl).read_text(encoding="utf-8-sig").splitlines() if ln.strip()
    ]
    l_lines = [
        ln for ln in Path(args.labels_jsonl).read_text(encoding="utf-8-sig").splitlines() if ln.strip()
    ]
    if len(n_lines) != len(l_lines):
        print(
            f"ERROR: row count mismatch news={len(n_lines)} labels={len(l_lines)}",
            file=sys.stderr,
        )
        return 1

    for i, (a, b) in enumerate(zip(n_lines, l_lines), start=1):
        nr = _parse_js(a)
        lr = _parse_js(b)
        if args.strict_as_of_date_before_label_date:
            da = _as_of_date(nr)
            dl = _label_date(lr)
            if not (da < dl):
                print(
                    f"ERROR: pair line {i}: as_of_date {da} not strictly before label_date {dl}",
                    file=sys.stderr,
                )
                return 1

    print("check_news_label_join_temporal_v1: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
