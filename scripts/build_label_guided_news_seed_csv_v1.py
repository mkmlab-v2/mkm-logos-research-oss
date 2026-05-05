#!/usr/bin/env python3
"""Build label-guided seed news CSV from direction_label_bar_v1 JSONL.

Research utility for quickly creating consistent backtest seeds.
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LABELS = ROOT / "docs" / "final" / "artifacts" / "direction_label_bar_v1_latest.jsonl"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "news_observation_seed_template_v1.csv"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--labels-jsonl", type=Path, default=DEFAULT_LABELS)
    ap.add_argument("--output-csv", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--max-rows", type=int, default=40)
    args = ap.parse_args()

    if not args.labels_jsonl.is_file():
        raise SystemExit(f"Missing labels JSONL: {args.labels_jsonl}")

    rows: list[list[str]] = []
    for ln in args.labels_jsonl.read_text(encoding="utf-8-sig").splitlines():
        if not ln.strip():
            continue
        row = json.loads(ln)
        direction = str(row.get("direction") or "").lower()
        if direction not in {"up", "down"}:
            continue
        label_date = datetime.strptime(str(row["label_date"]), "%Y-%m-%d").replace(tzinfo=timezone.utc)
        published = (label_date - timedelta(days=1)).strftime("%Y-%m-%dT06:00:00Z")
        if direction == "up":
            text = "Export orders accelerate while slower tightening supports risk appetite"
        else:
            text = "Credit spreads widen and geopolitical volatility rises with risk-off tone"
        rows.append(
            [
                published,
                "label_guided_seed",
                text,
                "train_holdout",
                f"https://example.invalid/news/{len(rows)+1}",
                "[HYPO]",
            ]
        )
        if len(rows) >= args.max_rows:
            break

    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.output_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "published_utc",
                "source_id",
                "canonical_text",
                "dataset_partition",
                "source_record_url",
                "hypothesis_tag",
            ]
        )
        w.writerows(rows)
    print(f"WROTE: {args.output_csv} rows={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

