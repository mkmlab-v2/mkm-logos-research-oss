#!/usr/bin/env python3
"""Build global_market_overnight_signals_v1 for KOSPI premarket [HYPO].

Prefers fresh yfinance CSV rows over stale manual snapshot when available.
Optional pre_news headline inject for macro/news lens adapters.
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
DEFAULT_PRE_NEWS = ROOT / "docs/final/artifacts/pre_news_shadow_input_latest.json"
DATA_DIR = ROOT / "research/market_data"

YF_INDEX_SPECS: dict[str, tuple[Path, str, str]] = {
    "dow": (DATA_DIR / "dow_daily_external_yf.csv", "다우(yfinance)", "dow_yfinance_csv"),
    "nasdaq": (DEFAULT_NASDAQ_CSV, "나스닥(yfinance)", "nasdaq_yfinance_csv"),
    "sp500": (DATA_DIR / "sp500_daily_external_yf.csv", "S&P500(yfinance)", "sp500_yfinance_csv"),
    "nikkei225": (DATA_DIR / "nikkei225_daily_external_yf.csv", "니케이225(yfinance)", "nikkei225_yfinance_csv"),
    "hang_seng": (DATA_DIR / "hang_seng_daily_external_yf.csv", "항셍(yfinance)", "hang_seng_yfinance_csv"),
    "shanghai": (DATA_DIR / "shanghai_daily_external_yf.csv", "상해종합(yfinance)", "shanghai_yfinance_csv"),
}

SNAPSHOT_FALLBACK: list[dict[str, Any]] = [
    {"id": "dow", "label_ko": "다우", "session_date": "2026-06-03", "change_pct": -1.07, "source": "naver_pay_snapshot_20260603"},
    {"id": "nasdaq", "label_ko": "나스닥", "session_date": "2026-06-03", "change_pct": -0.87, "source": "naver_pay_snapshot_20260603"},
    {"id": "sp500", "label_ko": "S&P500", "session_date": "2026-06-03", "change_pct": -0.74, "source": "naver_pay_snapshot_20260603"},
    {"id": "nikkei225", "label_ko": "니케이225", "session_date": "2026-06-03", "change_pct": 2.50, "source": "naver_pay_snapshot_20260603"},
    {"id": "hang_seng", "label_ko": "항셍", "session_date": "2026-06-03", "change_pct": -1.56, "source": "naver_pay_snapshot_20260603"},
    {"id": "shanghai", "label_ko": "상해종합", "session_date": "2026-06-03", "change_pct": 0.22, "source": "naver_pay_snapshot_20260603"},
    {"id": "dax", "label_ko": "독일DAX", "session_date": "2026-06-03", "change_pct": -1.31, "source": "naver_pay_snapshot_20260603"},
    {"id": "ftse100", "label_ko": "FTSE100", "session_date": "2026-06-03", "change_pct": -0.40, "source": "naver_pay_snapshot_20260603"},
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


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


def _session_date_key(row: dict[str, Any]) -> str:
    return str(row.get("session_date") or "")[:10]


def _pick_fresher_index(yf_row: dict[str, Any] | None, snap_row: dict[str, Any] | None) -> dict[str, Any] | None:
    if yf_row and snap_row:
        if _session_date_key(yf_row) >= _session_date_key(snap_row):
            out = dict(yf_row)
            out["overrides_snapshot"] = True
            return out
        return dict(snap_row)
    if yf_row:
        out = dict(yf_row)
        out["overrides_snapshot"] = True
        return out
    return dict(snap_row) if snap_row else None


def _headlines_from_pre_news(path: Path, *, max_items: int = 12) -> list[str]:
    doc = _read_json(path)
    if not doc:
        return []
    rows = doc.get("rows") if isinstance(doc.get("rows"), list) else []
    out: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        h = str(row.get("headline") or "").strip()
        if h:
            out.append(h)
        if len(out) >= max_items:
            break
    return out


def build_doc(*, nasdaq_csv: Path, pre_news_path: Path | None = None) -> dict[str, Any]:
    snap_by_id = {str(r.get("id")): r for r in SNAPSHOT_FALLBACK if r.get("id")}
    indices: list[dict[str, Any]] = []
    sources: list[str] = []

    for row_id, (csv_path, label_ko, source_tag) in YF_INDEX_SPECS.items():
        csv_use = nasdaq_csv if row_id == "nasdaq" else csv_path
        yf_row = _index_from_csv(csv_use, row_id=row_id, label_ko=label_ko, source=source_tag)
        picked = _pick_fresher_index(yf_row, snap_by_id.get(row_id))
        if picked:
            indices.append(picked)
            if yf_row and picked.get("overrides_snapshot"):
                sources.append(source_tag)
            elif snap_by_id.get(row_id) and picked is snap_by_id.get(row_id):
                sources.append("naver_pay_snapshot_20260603")

    for row_id, snap in snap_by_id.items():
        if row_id in YF_INDEX_SPECS:
            continue
        indices.append(dict(snap))
        sources.append(str(snap.get("source") or "naver_pay_snapshot_20260603"))

    session_dates = [_session_date_key(x) for x in indices if _session_date_key(x)]
    session_anchor = max(session_dates) if session_dates else "2026-06-03"

    bear = sum(1 for x in indices if float(x.get("change_pct") or 0) < -0.3)
    bull = sum(1 for x in indices if float(x.get("change_pct") or 0) > 0.3)
    if bear > bull + 1:
        composite = "risk_off_overnight"
    elif bull > bear + 1:
        composite = "risk_on_overnight"
    else:
        composite = "mixed_overnight"

    headlines = _headlines_from_pre_news(pre_news_path or DEFAULT_PRE_NEWS)
    if not headlines:
        headlines = [
            "[뉴욕증시] 유가와 채권 금리 상승에 일제히 selloff decline",
            "Fed inflation warning risk-off stress tightening",
        ]

    return {
        "schema": "global_market_overnight_signals_v1",
        "version": "1.1.0",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "boundary_ack": True,
        "session_anchor_date": session_anchor,
        "composite_tilt": composite,
        "indices": indices,
        "news_headlines": headlines,
        "provenance": {
            "sources": sorted(set(sources)),
            "nasdaq_csv": str(nasdaq_csv.resolve()) if nasdaq_csv.is_file() else "",
            "pre_news_input": str((pre_news_path or DEFAULT_PRE_NEWS).resolve())
            if (pre_news_path or DEFAULT_PRE_NEWS).is_file()
            else "",
            "note": "yfinance CSV preferred when fresher than snapshot; headlines from pre_news when present.",
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--nasdaq-csv", type=Path, default=DEFAULT_NASDAQ_CSV)
    ap.add_argument("--pre-news-input", type=Path, default=DEFAULT_PRE_NEWS)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)
    doc = build_doc(nasdaq_csv=args.nasdaq_csv, pre_news_path=args.pre_news_input)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
