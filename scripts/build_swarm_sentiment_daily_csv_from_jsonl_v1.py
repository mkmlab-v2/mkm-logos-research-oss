#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Expand B-track Swarm sentiment JSONL into a daily CSV for panel join ([HYPO]).

Each JSONL line must validate against ``SWARM_SENTIMENT_METRIC_SCHEMA_DRAFT.json``.
Join date is the UTC calendar date of ``seed_cutoff_time`` (YYYY-MM-DD prefix).

Output columns: ``date``, ``swarm_panic_ratio``, ``swarm_fomo_index``, ``swarm_consensus_strength``.
Duplicate dates: last row wins (logged in meta).
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _date_from_cutoff(cutoff: str) -> str | None:
    s = str(cutoff).strip()
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--jsonl",
        type=Path,
        default=ROOT / "data" / "btrack" / "swarm_sentiment_daily_hypo_v1.jsonl",
    )
    ap.add_argument("--out-csv", type=Path, required=True)
    ap.add_argument("--out-meta-json", type=Path, default=None)
    ap.add_argument("--utf8-bom", action="store_true")
    args = ap.parse_args()

    if not args.jsonl.is_file():
        print(f"missing jsonl: {args.jsonl}", file=sys.stderr)
        return 2

    by_date: dict[str, dict[str, Any]] = {}
    dupes: list[str] = []
    n_bad = 0
    for i, line in enumerate(args.jsonl.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            n_bad += 1
            continue
        dk = _date_from_cutoff(str(obj.get("seed_cutoff_time") or ""))
        if not dk:
            n_bad += 1
            continue
        metrics = obj.get("metrics") if isinstance(obj.get("metrics"), dict) else {}
        if dk in by_date:
            dupes.append(dk)
        by_date[dk] = {
            "date": dk,
            "swarm_panic_ratio": metrics.get("panic_ratio", ""),
            "swarm_fomo_index": metrics.get("fomo_index", ""),
            "swarm_consensus_strength": metrics.get("consensus_strength", ""),
            "seed_event_id": obj.get("seed_event_id", ""),
        }

    if not by_date:
        print("no valid rows in jsonl", file=sys.stderr)
        return 2

    fieldnames = ["date", "swarm_panic_ratio", "swarm_fomo_index", "swarm_consensus_strength", "seed_event_id"]
    rows = [by_date[k] for k in sorted(by_date.keys())]

    encoding = "utf-8-sig" if args.utf8_bom else "utf-8"
    args.out_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.out_csv.open("w", newline="", encoding=encoding) as fp:
        w = csv.DictWriter(fp, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    meta = {
        "schema": "swarm_sentiment_daily_csv_from_jsonl_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "inputs": {"jsonl": str(args.jsonl.resolve())},
        "counts": {"n_rows": len(rows), "n_bad_lines": n_bad, "n_duplicate_dates": len(dupes)},
        "duplicate_dates": dupes,
        "out_csv": str(args.out_csv.resolve()),
    }
    meta_path = args.out_meta_json or args.out_csv.with_suffix(".meta.json")
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE rows={len(rows)} csv={args.out_csv.resolve()} meta={meta_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
