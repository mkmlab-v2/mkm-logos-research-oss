#!/usr/bin/env python3
"""Prophecy market OHLCV freshness gate (B-track, research_only).

After fetch_kospi/btc, verifies SSOT CSV max dates are not stale vs local calendar.
Does not call yfinance. Not a live-trading or Track A gate.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DEFAULT_KOSPI = ROOT / "research" / "market_data" / "kospi_daily_external_yf.csv"
DEFAULT_BTC = ROOT / "research" / "market_data" / "btc_daily_external_yf.csv"
DEFAULT_OUT = ROOT / "reports" / "prophecy_market_data_freshness_v1_latest.json"
SCHEMA = "prophecy_market_data_freshness_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _max_row_date(csv_path: Path) -> tuple[str | None, int, str | None]:
    if not csv_path.is_file():
        return None, 0, "missing_file"
    try:
        from scripts.logos_shadow_eval_lib import load_kospi_yf_rows
    except ImportError:
        return None, 0, "import_load_kospi_yf_rows_failed"
    try:
        rows = load_kospi_yf_rows(csv_path)
    except Exception as exc:  # noqa: BLE001 — triage artifact
        return None, 0, f"parse_error:{type(exc).__name__}"
    if not rows:
        return None, 0, "empty_rows"
    dates = sorted(str(r.get("date") or "")[:10] for r in rows if r.get("date"))
    if not dates:
        return None, 0, "no_dates"
    return dates[-1], len(rows), None


def _age_calendar_days(max_date: str, ref: date) -> int | None:
    try:
        md = date.fromisoformat(max_date[:10])
    except ValueError:
        return None
    return (ref - md).days


def _leg_status(
    csv_path: Path,
    *,
    required: bool,
    max_stale_days: int,
    ref: date,
) -> dict[str, Any]:
    max_date, row_count, err = _max_row_date(csv_path)
    rel = str(csv_path.relative_to(ROOT)).replace("\\", "/") if csv_path.is_relative_to(ROOT) else str(csv_path)
    out: dict[str, Any] = {
        "path": rel,
        "required": required,
        "row_count": row_count,
        "max_date": max_date,
        "error": err,
    }
    if max_date is None:
        out["ok"] = not required
        out["stale"] = required
        out["age_calendar_days"] = None
        return out
    age = _age_calendar_days(max_date, ref)
    out["age_calendar_days"] = age
    if age is None:
        out["ok"] = False
        out["stale"] = True
        return out
    stale = age > max_stale_days
    out["stale"] = stale
    out["ok"] = not stale
    return out


def build_report(
    *,
    kospi_csv: Path,
    btc_csv: Path,
    max_stale_days: int,
    ref: date | None = None,
) -> dict[str, Any]:
    ref = ref or date.today()
    kospi = _leg_status(kospi_csv, required=True, max_stale_days=max_stale_days, ref=ref)
    btc = _leg_status(btc_csv, required=False, max_stale_days=max_stale_days, ref=ref)
    all_ok = kospi.get("ok") is True and btc.get("ok") is True
    return {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "reference_local_date": ref.isoformat(),
        "max_stale_calendar_days": max_stale_days,
        "legs": {"kospi": kospi, "btc": btc},
        "all_ok": all_ok,
        "note": "B-track data hygiene only; not prophecy quality or live-trading GO.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Prophecy OHLCV CSV freshness gate (B-track).")
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC)
    ap.add_argument("--max-stale-days", type=int, default=7, help="Calendar days behind local today.")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--stdout-only", action="store_true")
    ap.add_argument("--strict", action="store_true", help="Exit 1 when all_ok is false.")
    args = ap.parse_args()

    report = build_report(
        kospi_csv=args.kospi_csv,
        btc_csv=args.btc_csv,
        max_stale_days=args.max_stale_days,
    )
    payload = json.dumps(report, ensure_ascii=False, indent=2)

    if args.stdout_only:
        print(payload)
    else:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(payload + "\n", encoding="utf-8")
        print(f"wrote {args.out_json}")

    if args.strict and not report.get("all_ok"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
