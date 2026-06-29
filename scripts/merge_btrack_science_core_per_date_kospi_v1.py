#!/usr/bin/env python3
"""Merge recent KOSPI science_core rows into JSONL without full rebuild [HYPO]."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_btrack_science_core_per_date_v1 import build_rows  # noqa: E402
from scripts.run_three_lens_horizon_empirical_eval_v1 import KOSPI_CSV  # noqa: E402

DEFAULT_KOSPI_JSONL = ROOT / "reports/btrack_science_core_per_date_kospi_v1.jsonl"
DEFAULT_KOSPI_ART = ROOT / "docs/final/artifacts/btrack_science_core_per_date_kospi_v1.jsonl"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_jsonl(path: Path) -> dict[str, dict[str, Any]]:
    by_date: dict[str, dict[str, Any]] = {}
    if not path.is_file():
        return by_date
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            d = str(obj.get("session_date") or "")[:10]
            if d:
                by_date[d] = obj
    return by_date


def merge_recent(
    *,
    jsonl_path: Path,
    date_from: str,
    date_to: str,
    lookback: int,
) -> dict[str, Any]:
    existing = _read_jsonl(jsonl_path)
    new_rows = build_rows(
        instrument="kospi",
        csv_path=KOSPI_CSV,
        date_from=date_from,
        date_to=date_to,
        lookback=lookback,
        apply_overnight=True,
        exa_jsonl=ROOT / "reports/exa_macro_news_observation_staging_v1_latest.jsonl",
    )
    updated = 0
    for row in new_rows:
        d = str(row.get("session_date") or "")[:10]
        if d:
            existing[d] = row
            updated += 1
    merged = [existing[k] for k in sorted(existing.keys())]
    return {
        "merged_rows": len(merged),
        "window_updated": updated,
        "date_from": date_from,
        "date_to": date_to,
        "latest_session": merged[-1].get("session_date") if merged else None,
        "rows": merged,
    }


def write_jsonl(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date-from", default="2026-06-20")
    ap.add_argument("--date-to", default="2026-06-23")
    ap.add_argument("--lookback", type=int, default=5)
    ap.add_argument("--jsonl", type=Path, default=DEFAULT_KOSPI_JSONL)
    ap.add_argument("--artifact-jsonl", type=Path, default=DEFAULT_KOSPI_ART)
    args = ap.parse_args()

    if not KOSPI_CSV.is_file():
        print(f"Missing {KOSPI_CSV}", file=sys.stderr)
        return 2

    result = merge_recent(
        jsonl_path=args.jsonl,
        date_from=args.date_from,
        date_to=args.date_to,
        lookback=args.lookback,
    )
    write_jsonl(result["rows"], args.jsonl)
    write_jsonl(result["rows"], args.artifact_jsonl)
    summary = {
        "schema": "merge_btrack_science_core_per_date_v1",
        "generated_at_utc": _utc(),
        "ok": True,
        "merged_rows": result["merged_rows"],
        "window_updated": result["window_updated"],
        "latest_session": result["latest_session"],
        "out": str(args.jsonl),
    }
    out_report = ROOT / "reports/merge_btrack_science_core_per_date_v1_latest.json"
    out_report.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
