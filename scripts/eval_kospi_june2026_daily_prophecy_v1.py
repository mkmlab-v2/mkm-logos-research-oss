#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Score June 2026 KOSPI daily prophecy vs realized OHLCV [HYPO][research_only]."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

KST = ZoneInfo("Asia/Seoul")
CALENDAR_DEFAULT = ROOT / "reports/kospi_june2026_daily_prophecy_calendar_v1.json"
KOSPI_CSV = ROOT / "research/market_data/kospi_daily_external_yf.csv"
EVOLUTION_RULES = ROOT / "data/commander/kospi_june2026_prophecy_evolution_v1.json"
BRIEFING_LOG = ROOT / "reports/briefing_log"
DEFAULT_OUT = ROOT / "reports/kospi_june2026_daily_prophecy_eval_latest.json"
SCORE_LOG = ROOT / "reports/kospi_june2026_daily_prophecy_score_log.jsonl"


def _paths_for_month(year_month: str) -> tuple[Path, Path, Path]:
    tag = str(year_month).strip().replace("-", "")
    report_out = ROOT / f"reports/kospi_{tag}_daily_prophecy_eval_latest.json"
    art_out = ROOT / f"docs/final/artifacts/kospi_{tag}_daily_prophecy_eval_latest.json"
    score_log = ROOT / f"reports/kospi_{tag}_daily_prophecy_score_log.jsonl"
    return report_out, art_out, score_log


def _resolve_outputs(calendar_path: Path, calendar: dict[str, Any]) -> tuple[Path, Path, Path]:
    ym = str(calendar.get("year_month") or "").strip()
    if ym:
        report_out, art_out, score_log = _paths_for_month(ym)
        if ym == "2026-06":
            return DEFAULT_OUT, ROOT / "docs/final/artifacts/kospi_june2026_daily_prophecy_eval_latest.json", SCORE_LOG
        return report_out, art_out, score_log
    if "june2026" in calendar_path.name.lower() or "202606" in calendar_path.name:
        return DEFAULT_OUT, ROOT / "docs/final/artifacts/kospi_june2026_daily_prophecy_eval_latest.json", SCORE_LOG
    return DEFAULT_OUT, ROOT / "docs/final/artifacts/kospi_june2026_daily_prophecy_eval_latest.json", SCORE_LOG


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _today_kst() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d")


def _default_as_of_kst() -> str:
    """Score through last KRX session, not wall-clock KST (weekend/holiday safe)."""
    from datetime import date

    from scripts.kospi_krx_calendar_v1 import last_krx_trading_day_on_or_before

    today = datetime.now(KST).date()
    last_sess = last_krx_trading_day_on_or_before(today)
    return last_sess or _today_kst()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _load_closes(csv_path: Path) -> dict[str, float]:
    closes, _vendor_incomplete = _load_ohlcv_state(csv_path)
    return closes


def _load_ohlcv_state(csv_path: Path) -> tuple[dict[str, float], set[str]]:
    closes: dict[str, float] = {}
    vendor_incomplete: set[str] = set()
    if not csv_path.is_file():
        return closes, vendor_incomplete
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            dk = str(row.get("Date", ""))[:10]
            if len(dk) != 10:
                continue
            raw_close = row.get("Close")
            if raw_close is None or str(raw_close).strip() == "":
                vendor_incomplete.add(dk)
                continue
            try:
                val = float(raw_close)
            except (ValueError, TypeError):
                vendor_incomplete.add(dk)
                continue
            if val <= 0:
                vendor_incomplete.add(dk)
                continue
            closes[dk] = val
    return closes, vendor_incomplete


def _direction_from_return(ret: float, neutral_bps: float) -> str:
    thr = neutral_bps / 10000.0
    if ret > thr:
        return "bull"
    if ret < -thr:
        return "bear"
    return "neutral"


def _outcome(pred: str, actual: str) -> str:
    if actual == "neutral" or pred == "neutral":
        return "NEUTRAL_DRAW"
    if pred == actual:
        return "HIT"
    return "FAIL"


def eval_calendar(
    calendar: dict[str, Any],
    *,
    calendar_path: Path | None = None,
    as_of_kst: str | None = None,
    neutral_bps: float = 5.0,
) -> dict[str, Any]:
    rules = _read_json(EVOLUTION_RULES)
    neutral_bps = float(rules.get("neutral_bps", neutral_bps))
    as_of = as_of_kst or _default_as_of_kst()
    from scripts.kospi_krx_calendar_v1 import exclude_krx_non_trading, load_krx_non_trading_days

    closes, vendor_incomplete_all = _load_ohlcv_state(KOSPI_CSV)
    raw_trading_days = list(calendar.get("trading_days") or [])
    trading_days, krx_non_trading_excluded = exclude_krx_non_trading(raw_trading_days)
    row_by_date = {str(r.get("session_date")): r for r in calendar.get("rows") or [] if r.get("session_date")}

    non_scoreable = rules.get("june_non_scoreable_sessions")
    if not isinstance(non_scoreable, dict):
        non_scoreable = {}

    missing_ohlcv: list[str] = []
    vendor_incomplete: list[str] = []
    for dk in trading_days:
        if dk > as_of:
            continue
        if dk in non_scoreable:
            continue
        if dk in vendor_incomplete_all:
            vendor_incomplete.append(dk)
            continue
        if dk not in closes:
            missing_ohlcv.append(dk)
            continue

    scored: list[dict[str, Any]] = []
    for dk in trading_days:
        if dk > as_of:
            continue
        if dk not in closes:
            continue
        prow = row_by_date.get(dk)
        if not prow:
            continue
        older = sorted(d for d in closes if d < dk)
        prior = closes[older[-1]] if older else None
        if prior is None or prior == 0:
            continue

        close = closes[dk]
        ret = (close - prior) / prior
        actual_dir = _direction_from_return(ret, neutral_bps)
        pred_dir = str(prow.get("predicted_direction") or "neutral")
        outcome = _outcome(pred_dir, actual_dir)

        band = prow.get("kospi_index_prophecy") if isinstance(prow.get("kospi_index_prophecy"), dict) else {}
        band_hit = None
        lo, hi = band.get("predicted_close_band") or [None, None]
        if lo is not None and hi is not None:
            band_hit = float(lo) <= close <= float(hi)

        scored.append(
            {
                "session_date": dk,
                "predicted_direction": pred_dir,
                "actual_direction": actual_dir,
                "outcome": outcome,
                "daily_return_pct": round(ret * 100.0, 4),
                "prior_close": round(prior, 2),
                "actual_close": round(close, 2),
                "predicted_close_mid": band.get("predicted_close_mid"),
                "band_hit": band_hit,
            }
        )

    hits = sum(1 for s in scored if s["outcome"] == "HIT")
    fails = sum(1 for s in scored if s["outcome"] == "FAIL")
    neutral = sum(1 for s in scored if s["outcome"] == "NEUTRAL_DRAW")
    n_dir = hits + fails
    hit_rate = hits / n_dir if n_dir else None
    soft = (hits + 0.5 * neutral) / len(scored) if scored else None

    return {
        "schema": "kospi_june2026_daily_prophecy_eval_v1",
        "generated_at_utc": _utc_now(),
        "as_of_kst": as_of,
        "hypothesis_tier": "B",
        "research_only": True,
        "year_month": calendar.get("year_month"),
        "calendar_path": str(
            (calendar_path or CALENDAR_DEFAULT).relative_to(ROOT)
        ).replace("\\", "/"),
        "neutral_bps": neutral_bps,
        "krx_non_trading_days_excluded": [
            {
                "date": dk,
                "reason_id": (load_krx_non_trading_days().get(dk) or {}).get("reason_id"),
                "reason_ko": (load_krx_non_trading_days().get(dk) or {}).get("reason_ko"),
            }
            for dk in krx_non_trading_excluded
        ],
        "missing_ohlcv_trading_days": missing_ohlcv,
        "vendor_incomplete_trading_days": vendor_incomplete,
        "vendor_incomplete_note_ko": (
            "Yahoo CSV 행은 있으나 Close/Adj Close 무효(NaN·0·공백) — 수동 보정 금지·다음 fetch 대기."
            if vendor_incomplete
            else None
        ),
        "n_scored": len(scored),
        "metrics": {
            "hit": hits,
            "fail": fails,
            "neutral_draw": neutral,
            "directional_hit_rate": round(hit_rate, 4) if hit_rate is not None else None,
            "soft_hit_rate": round(soft, 4) if soft is not None else None,
        },
        "rows": scored,
    }


def _append_log(row: dict[str, Any], score_log: Path) -> None:
    score_log.parent.mkdir(parents=True, exist_ok=True)
    with score_log.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--calendar-json", type=Path, default=CALENDAR_DEFAULT)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--as-of-kst", type=str, default=None)
    ap.add_argument("--write-briefing-log", action="store_true", default=True)
    ap.add_argument("--no-briefing-log", action="store_true")
    args = ap.parse_args(argv)

    calendar_path = args.calendar_json if args.calendar_json.is_absolute() else (ROOT / args.calendar_json)
    cal = _read_json(calendar_path)
    if cal.get("schema") not in (
        "kospi_june2026_daily_prophecy_calendar_v1",
        "kospi_june2026_daily_prophecy_calendar_v2",
        "kospi_monthly_daily_prophecy_calendar_v1",
        "kospi_monthly_daily_prophecy_calendar_v2",
    ):
        print(f"Invalid calendar schema: {calendar_path}", file=sys.stderr)
        return 2

    default_out, default_art, default_log = _resolve_outputs(calendar_path, cal)
    out_path = args.output if args.output != DEFAULT_OUT else default_out
    doc = eval_calendar(cal, calendar_path=calendar_path, as_of_kst=args.as_of_kst)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    default_art.parent.mkdir(parents=True, exist_ok=True)
    default_art.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    log_row = {
        "ts_utc": _utc_now(),
        "as_of_kst": doc["as_of_kst"],
        "year_month": doc.get("year_month"),
        "n_scored": doc["n_scored"],
        "metrics": doc["metrics"],
    }
    _append_log(log_row, default_log)

    if args.write_briefing_log and not args.no_briefing_log:
        BRIEFING_LOG.mkdir(parents=True, exist_ok=True)
        ym_tag = str(doc.get("year_month") or "june").replace("-", "")
        day_path = BRIEFING_LOG / f"{doc['as_of_kst']}_kospi_{ym_tag}_score_v1.json"
        day_doc = {
            "schema": "kospi_monthly_daily_prophecy_score_v1",
            "calendar_kst": doc["as_of_kst"],
            "hypothesis_tier": "B",
            "research_only": True,
            "summary": doc["metrics"],
            "latest_scored_rows": doc["rows"][-5:],
            "eval_path": str(out_path.relative_to(ROOT)).replace("\\", "/"),
        }
        day_path.write_text(json.dumps(day_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        f"WROTE: {out_path.resolve()} n_scored={doc['n_scored']} "
        f"dir_hr={doc['metrics'].get('directional_hit_rate')} soft={doc['metrics'].get('soft_hit_rate')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
