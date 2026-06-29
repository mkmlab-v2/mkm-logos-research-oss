#!/usr/bin/env python3
"""Merge multi-month KOSPI prophecy eval + calendar panels [HYPO][research_only]."""
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

from scripts.eval_kospi_june2026_daily_prophecy_v1 import (  # noqa: E402
    KOSPI_CSV,
    _direction_from_return,
    _load_ohlcv_state,
    _outcome,
)

DEFAULT_EVAL_OUT = ROOT / "reports/kospi_multi_month_prophecy_eval_v1_latest.json"
DEFAULT_CAL_OUT = ROOT / "reports/kospi_multi_month_prophecy_calendar_v1_latest.json"
ART_EVAL = ROOT / "docs/final/artifacts/kospi_multi_month_prophecy_eval_v1_latest.json"
ART_CAL = ROOT / "docs/final/artifacts/kospi_multi_month_prophecy_calendar_v1_latest.json"
DEFAULT_SCIENCE_JSONL = ROOT / "reports/btrack_science_core_per_date_kospi_v1.jsonl"
DEFAULT_BAND_PCT = (-2.0, 2.0)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def merge_eval_docs(docs: list[dict[str, Any]], *, label: str) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    months: list[str] = []
    for doc in docs:
        ym = str(doc.get("year_month") or "")
        if ym and ym not in months:
            months.append(ym)
        for row in doc.get("rows") or []:
            if not isinstance(row, dict):
                continue
            dk = str(row.get("session_date") or "")
            if not dk or dk in seen:
                continue
            seen.add(dk)
            rows.append(dict(row))
    rows.sort(key=lambda r: str(r.get("session_date") or ""))
    return {
        "schema": "kospi_multi_month_prophecy_eval_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "panel_label": label,
        "source_months": months,
        "n_scored": len(rows),
        "rows": rows,
    }


def merge_calendar_docs(docs: list[dict[str, Any]], *, label: str) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    months: list[str] = []
    trading_days: list[str] = []
    for doc in docs:
        ym = str(doc.get("year_month") or "")
        if ym and ym not in months:
            months.append(ym)
        for dk in doc.get("trading_days") or []:
            ds = str(dk)
            if ds not in trading_days:
                trading_days.append(ds)
        for row in doc.get("rows") or []:
            if not isinstance(row, dict):
                continue
            dk = str(row.get("session_date") or "")
            if not dk or dk in seen:
                continue
            seen.add(dk)
            rows.append(dict(row))
    rows.sort(key=lambda r: str(r.get("session_date") or ""))
    trading_days = sorted(set(trading_days) | {str(r.get("session_date")) for r in rows if r.get("session_date")})
    return {
        "schema": "kospi_multi_month_prophecy_calendar_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "panel_label": label,
        "source_months": months,
        "year_month": "+".join(months) if months else None,
        "n_trading_days": len(trading_days),
        "trading_days": trading_days,
        "rows": rows,
    }


def _read_science_jsonl(path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            out.append(obj)
    out.sort(key=lambda r: str(r.get("session_date") or ""))
    return out


def build_science_core_backfill(
    *,
    jsonl_path: Path,
    exclude_dates: set[str],
    date_from: str | None = None,
    date_to: str | None = None,
    band_pct: tuple[float, float] = DEFAULT_BAND_PCT,
    neutral_bps: float = 5.0,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    closes, _vendor = _load_ohlcv_state(KOSPI_CSV)
    eval_rows: list[dict[str, Any]] = []
    cal_rows: list[dict[str, Any]] = []
    for rec in _read_science_jsonl(jsonl_path):
        dk = str(rec.get("session_date") or "")[:10]
        if not dk or dk in exclude_dates:
            continue
        if date_from and dk < date_from:
            continue
        if date_to and dk > date_to:
            continue
        if dk not in closes:
            continue
        older = sorted(d for d in closes if d < dk)
        if not older:
            continue
        prior = closes[older[-1]]
        close = closes[dk]
        if prior <= 0:
            continue
        ret = (close - prior) / prior
        actual_dir = _direction_from_return(ret, neutral_bps)
        pred_dir = str(rec.get("direction") or "neutral")
        lo_pct, hi_pct = band_pct
        eval_rows.append(
            {
                "session_date": dk,
                "predicted_direction": pred_dir,
                "actual_direction": actual_dir,
                "outcome": _outcome(pred_dir, actual_dir),
                "daily_return_pct": round(ret * 100.0, 4),
                "prior_close": round(prior, 2),
                "actual_close": round(close, 2),
                "predicted_close_mid": round(prior * (1.0 + (lo_pct + hi_pct) / 200.0), 2),
                "band_hit": None,
                "backfill_source": "science_core_uniform_band",
            }
        )
        cal_rows.append(
            {
                "session_date": dk,
                "predicted_direction": pred_dir,
                "kospi_index_prophecy": {
                    "predicted_return_band_pct": [lo_pct, hi_pct],
                    "predicted_close_band": [None, None],
                },
                "backfill_source": "science_core_uniform_band",
            }
        )
    return eval_rows, cal_rows


def build_multi_month_panel(
    *,
    eval_paths: list[Path],
    calendar_paths: list[Path],
    science_jsonl: Path | None = None,
    science_date_from: str | None = "2026-01-02",
    science_date_to: str | None = "2026-04-30",
    include_science_backfill: bool = True,
    panel_label: str = "prophecy_may_june_plus_science_backfill",
) -> tuple[dict[str, Any], dict[str, Any]]:
    eval_docs = [d for p in eval_paths if (d := _read(p))]
    cal_docs = [d for p in calendar_paths if (d := _read(p))]
    if not eval_docs or not cal_docs:
        raise ValueError("missing eval or calendar inputs")

    prophecy_eval = merge_eval_docs(eval_docs, label=panel_label)
    prophecy_cal = merge_calendar_docs(cal_docs, label=panel_label)

    sci_path = science_jsonl or DEFAULT_SCIENCE_JSONL
    if include_science_backfill and sci_path.is_file():
        exclude = {str(r.get("session_date")) for r in prophecy_eval.get("rows") or []}
        bf_eval, bf_cal = build_science_core_backfill(
            jsonl_path=sci_path,
            exclude_dates=exclude,
            date_from=science_date_from,
            date_to=science_date_to,
        )
        if bf_eval:
            prophecy_eval["rows"].extend(bf_eval)
            prophecy_eval["rows"].sort(key=lambda r: str(r.get("session_date") or ""))
            prophecy_eval["n_scored"] = len(prophecy_eval["rows"])
            prophecy_eval["science_backfill_rows"] = len(bf_eval)
            prophecy_cal["rows"].extend(bf_cal)
            prophecy_cal["rows"].sort(key=lambda r: str(r.get("session_date") or ""))
            prophecy_cal["trading_days"] = sorted(
                {str(r.get("session_date")) for r in prophecy_cal["rows"] if r.get("session_date")}
            )
            prophecy_cal["n_trading_days"] = len(prophecy_cal["trading_days"])
            prophecy_cal["science_backfill_rows"] = len(bf_cal)

    months = sorted(
        {str(r.get("session_date") or "")[:7] for r in prophecy_eval.get("rows") or [] if r.get("session_date")}
    )
    prophecy_eval["span_months"] = months
    prophecy_eval["n_months"] = len(months)
    prophecy_cal["span_months"] = months
    prophecy_cal["n_months"] = len(months)
    return prophecy_eval, prophecy_cal


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--eval-json",
        action="append",
        dest="eval_jsons",
        type=Path,
        default=[
            ROOT / "reports/kospi_202605_daily_prophecy_eval_latest.json",
            ROOT / "reports/kospi_june2026_daily_prophecy_eval_latest.json",
        ],
    )
    ap.add_argument(
        "--calendar-json",
        action="append",
        dest="calendar_jsons",
        type=Path,
        default=[
            ROOT / "reports/kospi_202605_daily_prophecy_calendar_research.json",
            ROOT / "reports/kospi_202606_daily_prophecy_calendar_v1.json",
        ],
    )
    ap.add_argument("--science-jsonl", type=Path, default=DEFAULT_SCIENCE_JSONL)
    ap.add_argument("--no-science-backfill", action="store_true")
    ap.add_argument("--eval-out", type=Path, default=DEFAULT_EVAL_OUT)
    ap.add_argument("--calendar-out", type=Path, default=DEFAULT_CAL_OUT)
    args = ap.parse_args()

    try:
        ev, cal = build_multi_month_panel(
            eval_paths=args.eval_jsons,
            calendar_paths=args.calendar_jsons,
            science_jsonl=args.science_jsonl,
            include_science_backfill=not args.no_science_backfill,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    for path, doc, art in (
        (args.eval_out, ev, ART_EVAL),
        (args.calendar_out, cal, ART_CAL),
    ):
        payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload, encoding="utf-8")
        art.parent.mkdir(parents=True, exist_ok=True)
        art.write_text(payload, encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "n_scored": ev["n_scored"],
                "n_months": ev.get("n_months"),
                "science_backfill_rows": ev.get("science_backfill_rows", 0),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
