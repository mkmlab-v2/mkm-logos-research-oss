#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KOSPI Science Core + humanist combo PnL backtest [HYPO][research_only]."""

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

from scripts.btrack_multilens_per_date_core_v1 import (  # noqa: E402
    DEFAULT_LOGOS_LENS,
    DEFAULT_MYEONGNI_JSONL,
    DEFAULT_SASANG_JSONL,
    causal_rows_through,
    logos_global,
    read_jsonl,
    row_asof,
    rows_by_calendar_day,
    score_myeongni_at_date,
    score_sasang_at_date,
)
from scripts.btrack_science_core_v1 import triple_sasang_myeongni_direction  # noqa: E402
from scripts.logos_shadow_eval_lib import load_kospi_yf_rows  # noqa: E402
from scripts.run_science_core_horizon_empirical_eval_v1 import (  # noqa: E402
    DEFAULT_SCIENCE_JSONL_KOSPI,
    _predictions_for_date,
)

DEFAULT_OUT = ROOT / "reports/science_core_kospi_combo_backtest_v1_latest.json"
ART_OUT = ROOT / "docs/final/artifacts/science_core_kospi_combo_backtest_v1_latest.json"

STRATEGY_IDS = (
    "science_core",
    "science_plus_sasang",
    "science_plus_myeongni",
    "science_plus_logos",
    "science_plus_sasang_myeongni",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _dir_to_sign(direction: str) -> int:
    d = (direction or "").strip().lower()
    if d == "bull":
        return 1
    if d == "bear":
        return -1
    return 0


def _load_science_by_date(path: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in read_jsonl(path):
        dk = str(row.get("session_date") or "")[:10]
        if dk:
            out[dk] = row
    return out


def _predictions_extended(
    dk: str,
    *,
    science_row: dict[str, Any] | None,
    myeongni_by_day: dict[str, dict[str, Any]],
    sasang_by_day: dict[str, dict[str, Any]],
    logos_block: dict[str, Any],
    myeongni_momentum_window: int,
) -> dict[str, str]:
    preds = _predictions_for_date(
        dk,
        science_row=science_row,
        myeongni_by_day=myeongni_by_day,
        sasang_by_day=sasang_by_day,
        logos_block=logos_block,
        myeongni_momentum_window=myeongni_momentum_window,
    )
    if not science_row:
        preds["science_plus_sasang_myeongni"] = "neutral"
        return preds

    my_day, _ = row_asof(myeongni_by_day, dk)
    sa_day, sa_asof = row_asof(sasang_by_day, dk)
    my_hist = causal_rows_through(myeongni_by_day, dk)
    my = score_myeongni_at_date(
        my_hist, eval_date=dk, matched_day=my_day, momentum_window=myeongni_momentum_window
    )
    sa = score_sasang_at_date(sa_asof, matched_day=sa_day, eval_date=dk)
    science_score = float((science_row.get("scores") or {}).get("direction_score") or 0.0)
    preds["science_plus_sasang_myeongni"] = triple_sasang_myeongni_direction(
        science_score, float(sa.get("direction_score") or 0.0), float(my.get("direction_score") or 0.0)
    )
    return preds


def _actual_dir_from_return(ret: float, neutral_bps: float) -> str:
    thr = neutral_bps / 10000.0
    if ret > thr:
        return "bull"
    if ret < -thr:
        return "bear"
    return "neutral"


def run_backtest(
    *,
    csv_path: Path,
    science_jsonl: Path,
    date_from: str | None,
    date_to: str | None,
    neutral_bps: float,
    myeongni_jsonl: Path,
    sasang_jsonl: Path,
    logos_lens: Path,
    myeongni_momentum_window: int,
    fee_bps: float,
) -> dict[str, Any]:
    rows = sorted(load_kospi_yf_rows(csv_path), key=lambda r: str(r.get("date", "")))
    daily: list[tuple[str, float, float]] = []
    for i in range(1, len(rows)):
        d = str(rows[i].get("date", ""))[:10]
        try:
            c0 = float(rows[i - 1]["close"])
            c1 = float(rows[i]["close"])
        except (TypeError, ValueError, KeyError):
            continue
        if c0 <= 0:
            continue
        daily.append((d, (c1 - c0) / c0, c1))
    if date_from:
        daily = [x for x in daily if x[0] >= date_from]
    if date_to:
        daily = [x for x in daily if x[0] <= date_to]

    science_by = _load_science_by_date(science_jsonl)
    my_by = rows_by_calendar_day(read_jsonl(myeongni_jsonl))
    sa_by = rows_by_calendar_day(read_jsonl(sasang_jsonl))
    logos_block = logos_global(logos_lens)
    fee_rate = fee_bps / 10000.0

    results: dict[str, Any] = {}
    for sid in STRATEGY_IDS:
        prev_pos = 0
        equity = 1.0
        hits = 0
        active = 0
        n = 0
        for dk, ret, _ in daily:
            preds = _predictions_extended(
                dk,
                science_row=science_by.get(dk),
                myeongni_by_day=my_by,
                sasang_by_day=sa_by,
                logos_block=logos_block,
                myeongni_momentum_window=myeongni_momentum_window,
            )
            pred = preds.get(sid, "neutral")
            pos = _dir_to_sign(pred)
            turnover = abs(pos - prev_pos)
            pnl = (pos * ret) - (turnover * fee_rate)
            equity *= 1.0 + pnl
            prev_pos = pos
            actual = _actual_dir_from_return(ret, neutral_bps)
            n += 1
            if pos != 0 and actual in {"bull", "bear"}:
                active += 1
                if _dir_to_sign(actual) == pos:
                    hits += 1
        results[sid] = {
            "n_days": n,
            "n_active_days": active,
            "directional_hit_rate_active": round(hits / active, 4) if active else None,
            "total_return": round(equity - 1.0, 6),
            "final_equity": round(equity, 6),
        }

    ranked = sorted(
        [{"strategy_id": k, **v} for k, v in results.items()],
        key=lambda x: float(x.get("total_return") or -999.0),
        reverse=True,
    )
    for i, row in enumerate(ranked, start=1):
        row["rank_by_total_return"] = i

    return {
        "schema": "science_core_kospi_combo_backtest_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "date_from": date_from,
        "date_to": date_to,
        "neutral_bps": neutral_bps,
        "fee_bps": fee_bps,
        "n_trading_days": len(daily),
        "strategies": results,
        "ranked_by_total_return": ranked,
    }


def main(argv: list[str] | None = None) -> int:
    from scripts.run_three_lens_horizon_empirical_eval_v1 import KOSPI_CSV

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date-from", type=str, default="2026-01-01")
    ap.add_argument("--date-to", type=str, default="2026-06-08")
    ap.add_argument("--neutral-bps", type=float, default=5.0)
    ap.add_argument("--fee-bps", type=float, default=5.0)
    ap.add_argument("--science-jsonl", type=Path, default=DEFAULT_SCIENCE_JSONL_KOSPI)
    ap.add_argument("--myeongni-jsonl", type=Path, default=DEFAULT_MYEONGNI_JSONL)
    ap.add_argument("--sasang-jsonl", type=Path, default=DEFAULT_SASANG_JSONL)
    ap.add_argument("--logos-lens", type=Path, default=DEFAULT_LOGOS_LENS)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--artifact-output", type=Path, default=ART_OUT)
    args = ap.parse_args(argv)

    if not KOSPI_CSV.is_file():
        print(f"ERROR: missing {KOSPI_CSV}", file=sys.stderr)
        return 1
    if not args.science_jsonl.is_file():
        print(f"ERROR: missing science jsonl {args.science_jsonl}", file=sys.stderr)
        return 1

    doc = run_backtest(
        csv_path=KOSPI_CSV,
        science_jsonl=args.science_jsonl,
        date_from=args.date_from,
        date_to=args.date_to,
        neutral_bps=args.neutral_bps,
        myeongni_jsonl=args.myeongni_jsonl,
        sasang_jsonl=args.sasang_jsonl,
        logos_lens=args.logos_lens,
        myeongni_momentum_window=5,
        fee_bps=args.fee_bps,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.artifact_output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.artifact_output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    top = (doc.get("ranked_by_total_return") or [{}])[0]
    print(f"WROTE: {args.output.resolve()} top={top.get('strategy_id')} ret={top.get('total_return')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
