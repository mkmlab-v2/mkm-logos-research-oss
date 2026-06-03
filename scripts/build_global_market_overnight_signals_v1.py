#!/usr/bin/env python3
"""Build global_market_overnight_signals_v1 for KOSPI reroute Phase A [HYPO].

Merges yfinance NASDAQ last session with operator snapshot rows (e.g. Naver Pay 6/3).
research_only — not live trading.
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
DEFAULT_OUT = ROOT / "docs/final/artifacts/global_market_overnight_signals_v1_latest.json"
DEFAULT_NASDAQ_CSV = ROOT / "research/market_data/nasdaq_daily_external_yf.csv"
YF_INDEX_CSV: dict[str, tuple[Path, str]] = {
    "nikkei225": (ROOT / "research/market_data/nikkei225_daily_external_yf.csv", "니케이225(yfinance)"),
    "hang_seng": (ROOT / "research/market_data/hang_seng_daily_external_yf.csv", "항셍(yfinance)"),
    "shanghai": (ROOT / "research/market_data/shanghai_daily_external_yf.csv", "상해종합(yfinance)"),
}

# Naver Pay Securities overseas board snapshot (2026-06-03 local closes) — manual SSOT for Phase A.
NAVER_PAY_SNAPSHOT_20260603: list[dict[str, Any]] = [
    {"id": "dow", "label_ko": "다우", "session_date": "2026-06-03", "change_pct": -1.07},
    {"id": "nasdaq", "label_ko": "나스닥", "session_date": "2026-06-03", "change_pct": -0.87},
    {"id": "sp500", "label_ko": "S&P500", "session_date": "2026-06-03", "change_pct": -0.74},
    {"id": "nikkei225", "label_ko": "니케이225", "session_date": "2026-06-03", "change_pct": 2.50},
    {"id": "hang_seng", "label_ko": "항셍", "session_date": "2026-06-03", "change_pct": -1.56},
    {"id": "shanghai", "label_ko": "상해종합", "session_date": "2026-06-03", "change_pct": 0.22},
    {"id": "dax", "label_ko": "독일DAX", "session_date": "2026-06-03", "change_pct": -1.31},
    {"id": "ftse100", "label_ko": "FTSE100", "session_date": "2026-06-03", "change_pct": -0.40},
]

NEWS_HEADLINES_20260603: list[str] = [
    "[뉴욕증시] 유가와 채권 금리 상승에 일제히 selloff decline",
    "Fed inflation warning risk-off stress tightening",
    "US Treasury inflation surge temporary selloff fear",
    "Middle East tension oil surge market stress shock",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _index_from_csv(path: Path, *, row_id: str, label_ko: str, source: str) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    rows: list[dict[str, str]] = []
    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if row.get("Date"):
                rows.append(row)
    if len(rows) < 2:
        return None
    last: dict[str, str] | None = None
    prev: dict[str, str] | None = None
    for row in reversed(rows):
        try:
            close = float(row.get("Close") or "")
        except (TypeError, ValueError):
            continue
        if close == 0:
            continue
        if last is None:
            last = row
            continue
        prev = row
        break
    if not last or not prev:
        return None
    try:
        c0 = float(prev["Close"])
        c1 = float(last["Close"])
    except (KeyError, TypeError, ValueError):
        return None
    if c0 == 0:
        return None
    change_pct = (c1 / c0 - 1.0) * 100.0
    return {
        "id": row_id,
        "label_ko": label_ko,
        "session_date": str(last.get("Date", ""))[:10],
        "change_pct": round(change_pct, 4),
        "close": c1,
        "prev_close": c0,
        "source": source,
    }


def _nasdaq_from_csv(path: Path) -> dict[str, Any] | None:
    row = _index_from_csv(path, row_id="nasdaq_yf", label_ko="나스닥(yfinance)", source="yfinance_csv")
    return row


def _merge_or_replace_index(indices: list[dict[str, Any]], yf_row: dict[str, Any], target_id: str) -> None:
    for i, row in enumerate(indices):
        if str(row.get("id") or "") == target_id:
            merged = dict(yf_row)
            merged["id"] = target_id
            merged["overrides_snapshot"] = True
            indices[i] = merged
            return
    indices.append(dict(yf_row))


def build_doc(*, nasdaq_csv: Path) -> dict[str, Any]:
    indices: list[dict[str, Any]] = list(NAVER_PAY_SNAPSHOT_20260603)
    yf_nq = _nasdaq_from_csv(nasdaq_csv)
    sources = ["naver_pay_snapshot_20260603"]
    if yf_nq:
        indices.append(yf_nq)
        sources.append("nasdaq_yfinance_csv")
    for target_id, (csv_path, label_ko) in YF_INDEX_CSV.items():
        yf_row = _index_from_csv(csv_path, row_id=target_id, label_ko=label_ko, source="yfinance_csv")
        if yf_row:
            _merge_or_replace_index(indices, yf_row, target_id)
            sources.append(f"{target_id}_yfinance_csv")
    bear = sum(1 for x in indices if float(x.get("change_pct") or 0) < -0.3)
    bull = sum(1 for x in indices if float(x.get("change_pct") or 0) > 0.3)
    if bear > bull + 1:
        composite = "risk_off_overnight"
    elif bull > bear + 1:
        composite = "risk_on_overnight"
    else:
        composite = "mixed_overnight"
    return {
        "schema": "global_market_overnight_signals_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "boundary_ack": True,
        "session_anchor_date": "2026-06-03",
        "composite_tilt": composite,
        "indices": indices,
        "news_headlines": list(NEWS_HEADLINES_20260603),
        "provenance": {
            "sources": sources,
            "nasdaq_csv": str(nasdaq_csv.resolve()) if nasdaq_csv.is_file() else "",
            "note": "Phase A KOSPI reroute manual+CSV ingest; not Naver API scrape.",
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--nasdaq-csv", type=Path, default=DEFAULT_NASDAQ_CSV)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)
    doc = build_doc(nasdaq_csv=args.nasdaq_csv)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
