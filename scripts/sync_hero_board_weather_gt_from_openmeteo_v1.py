#!/usr/bin/env python3
"""Sync hero-board weather GT JSONL from Open-Meteo Korea daily CSV [HYPO]."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = ROOT / "reports/korea_daily_weather_openmeteo_v1.csv"
DEFAULT_JSONL = ROOT / "research/market_data/seoul_weather_ground_truth_hero_board.jsonl"
THRESHOLD_MM = 5.0


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_jsonl(path: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        dk = str(row.get("observation_date_local") or "")[:10]
        if len(dk) == 10:
            out[dk] = row
    return out


def rows_from_csv(csv_path: Path, *, threshold_mm: float) -> dict[str, dict[str, Any]]:
    import csv

    out: dict[str, dict[str, Any]] = {}
    if not csv_path.is_file():
        return out
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            dk = str(row.get("date") or "")[:10]
            if len(dk) != 10:
                continue
            raw = row.get("seoul_precip_mm") or row.get("seoul_precipitation_sum")
            if raw in (None, ""):
                continue
            try:
                precip = float(raw)
            except (ValueError, TypeError):
                continue
            src = str(row.get("seoul_weather_source") or "open_meteo_hero_board")
            out[dk] = {
                "schema": "weather_ground_truth_row_v1",
                "observation_date_local": dk,
                "timezone": "Asia/Seoul",
                "station_or_region_id": "seoul_openmeteo_hero_board",
                "precip_mm_day": precip,
                "precip_binary_gt_0_1mm": precip > 0.1,
                "precip_binary_ge_threshold": precip >= threshold_mm,
                "source": {
                    "retrieved_at_utc": _utc_now(),
                    "dataset_name": src,
                    "hero_board_threshold_mm": threshold_mm,
                },
            }
    return out


def sync_jsonl(
    *,
    csv_path: Path,
    jsonl_path: Path,
    threshold_mm: float,
    merge: bool,
) -> dict[str, Any]:
    existing = _read_jsonl(jsonl_path) if merge else {}
    from_csv = rows_from_csv(csv_path, threshold_mm=threshold_mm)
    for dk, row in from_csv.items():
        existing[dk] = row

    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    with jsonl_path.open("w", encoding="utf-8") as f:
        for dk in sorted(existing):
            f.write(json.dumps(existing[dk], ensure_ascii=False) + "\n")

    june_2026 = [dk for dk in existing if dk.startswith("2026-06")]
    return {
        "ok": True,
        "jsonl": str(jsonl_path),
        "total_rows": len(existing),
        "june_2026_rows": len(june_2026),
        "threshold_mm": threshold_mm,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    ap.add_argument("--jsonl", type=Path, default=DEFAULT_JSONL)
    ap.add_argument("--threshold-mm", type=float, default=THRESHOLD_MM)
    ap.add_argument("--no-merge", action="store_true")
    args = ap.parse_args()

    csv_p = args.csv if args.csv.is_absolute() else ROOT / args.csv
    jsonl_p = args.jsonl if args.jsonl.is_absolute() else ROOT / args.jsonl
    if not csv_p.is_file():
        print(f"missing csv: {csv_p}", file=sys.stderr)
        return 2

    doc = sync_jsonl(csv_path=csv_p, jsonl_path=jsonl_p, threshold_mm=args.threshold_mm, merge=not args.no_merge)
    print(json.dumps(doc, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
