#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate schema-valid Swarm sentiment JSONL for KRX weekdays ([HYPO], synthetic).

Metrics are **deterministic from calendar date SHA256** only — no OHLCV or market inputs
(tuning/leakage guard). For B-track pipeline volume (e.g. min_pairs=30), not production Swarm.

Output validates against ``SWARM_SENTIMENT_METRIC_SCHEMA_DRAFT.json``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA = ROOT / "docs" / "final" / "SWARM_SENTIMENT_METRIC_SCHEMA_DRAFT.json"


def _daterange(d0: date, d1: date) -> Iterator[date]:
    d = d0
    while d <= d1:
        yield d
        d += timedelta(days=1)


def _skip_day(d: date, mode: str) -> bool:
    if mode == "all":
        return False
    if mode == "krx_weekdays":
        return d.weekday() >= 5
    raise ValueError("calendar_mode must be 'all' or 'krx_weekdays'")


def _metrics_from_date(d: date) -> dict[str, float]:
    digest = hashlib.sha256(d.isoformat().encode("utf-8")).hexdigest()
    parts = [int(digest[i : i + 8], 16) / 0xFFFFFFFF for i in range(0, 24, 8)]
    return {
        "panic_ratio": round(parts[0], 6),
        "fomo_index": round(parts[1], 6),
        "consensus_strength": round(parts[2], 6),
    }


def _row_for_date(d: date, hour: int, minute: int) -> dict:
    local_cutoff = datetime(d.year, d.month, d.day, hour, minute, 0, tzinfo=timezone.utc)
    cutoff_s = local_cutoff.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    ts_s = datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return {
        "timestamp_utc": ts_s,
        "seed_event_id": f"synthetic_krx_{d.isoformat()}",
        "seed_cutoff_time": cutoff_s,
        "metrics": _metrics_from_date(d),
        "simulation_meta": {
            "engine_name": "synthetic_date_hash_v1",
            "agent_count": 0,
            "prompt_hash": f"sha256:{hashlib.sha256(d.isoformat().encode()).hexdigest()}",
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date-from", required=True)
    ap.add_argument("--date-to", required=True)
    ap.add_argument("--calendar-mode", choices=("all", "krx_weekdays"), default="krx_weekdays")
    ap.add_argument("--hour", type=int, default=9)
    ap.add_argument("--minute", type=int, default=0)
    ap.add_argument(
        "--out-jsonl",
        type=Path,
        default=ROOT / "data" / "btrack" / "swarm_sentiment_synthetic_krx_hypo_v1.jsonl",
    )
    ap.add_argument("--validate", action="store_true", default=True)
    ap.add_argument("--no-validate", action="store_false", dest="validate")
    args = ap.parse_args()

    d0 = date.fromisoformat(args.date_from)
    d1 = date.fromisoformat(args.date_to)
    if d1 < d0:
        print("date-to before date-from", file=sys.stderr)
        return 2

    rows: list[dict] = []
    for d in _daterange(d0, d1):
        if _skip_day(d, args.calendar_mode):
            continue
        rows.append(_row_for_date(d, args.hour, args.minute))

    if not rows:
        print("no rows in range", file=sys.stderr)
        return 2

    args.out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.out_jsonl.open("w", encoding="utf-8") as fp:
        for row in rows:
            fp.write(json.dumps(row, ensure_ascii=False) + "\n")

    if args.validate:
        try:
            from jsonschema import Draft7Validator
        except ImportError:
            print("jsonschema missing; skip validate", file=sys.stderr)
        else:
            schema = json.loads(DEFAULT_SCHEMA.read_text(encoding="utf-8"))
            v = Draft7Validator(schema)
            for i, row in enumerate(rows, start=1):
                errs = list(v.iter_errors(row))
                if errs:
                    print(f"line {i} schema fail: {errs[0].message}", file=sys.stderr)
                    return 1

    meta = {
        "schema": "swarm_sentiment_synthetic_krx_jsonl_v1",
        "synthetic": True,
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "metric_source": "sha256(calendar_date) — no OHLCV input",
        "n_rows": len(rows),
        "date_from": args.date_from,
        "date_to": args.date_to,
        "calendar_mode": args.calendar_mode,
        "out_jsonl": str(args.out_jsonl.resolve()),
    }
    meta_path = args.out_jsonl.with_suffix(".meta.json")
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE n={len(rows)} jsonl={args.out_jsonl.resolve()} meta={meta_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
