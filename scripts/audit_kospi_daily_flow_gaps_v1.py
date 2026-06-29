#!/usr/bin/env python3
"""[HYPO] List KRX trading days missing from kospi_daily_flow_external.csv."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DAILY = ROOT / "research" / "market_data" / "kospi_daily_flow_external.csv"
DEFAULT_OUT = ROOT / "reports/kospi_daily_flow_gaps_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_daily_dates(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    out: set[str] = set()
    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            d = str(row.get("date") or "")[:10]
            if len(d) == 10:
                out.add(d)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--from-date", default="2026-05-01", help="YYYY-MM-DD inclusive")
    ap.add_argument("--to-date", default="2026-05-31", help="YYYY-MM-DD inclusive")
    ap.add_argument("--daily-csv", type=Path, default=DEFAULT_DAILY)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.kospi_krx_calendar_v1 import krx_trading_days

    d0 = date.fromisoformat(str(args.from_date)[:10])
    d1 = date.fromisoformat(str(args.to_date)[:10])
    expected = krx_trading_days(d0, d1)
    daily_path = args.daily_csv if args.daily_csv.is_absolute() else ROOT / args.daily_csv
    present = _load_daily_dates(daily_path)
    missing = [d for d in expected if d not in present]
    extra = sorted(present - set(expected))

    doc = {
        "schema": "kospi_daily_flow_gaps_v1",
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "generated_at_utc": _utc_now(),
        "daily_csv": str(daily_path.relative_to(ROOT)).replace("\\", "/"),
        "range": {"from": d0.isoformat(), "to": d1.isoformat()},
        "krx_trading_days_n": len(expected),
        "present_n": len([d for d in expected if d in present]),
        "missing_dates": missing,
        "missing_n": len(missing),
        "present_in_range": sorted(d for d in expected if d in present),
        "extra_outside_range_sample": extra[:20],
        "operator_next": [
            "Set KRX_ID/KRX_PW then: py scripts/fetch_kospi_daily_flow_pykrx_v1.py --from-date ... --to-date ...",
            "Or drop research/market_data/kospi_daily_flow_pending_row_v1.json and run Invoke-KospiDailyFlowRollupRoutine_v1.ps1",
        ],
    }
    out = args.output if args.output.is_absolute() else ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out} missing={len(missing)}/{len(expected)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
