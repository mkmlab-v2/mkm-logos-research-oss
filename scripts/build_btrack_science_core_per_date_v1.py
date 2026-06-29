#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build per-date Science Core JSONL (price/macro/news causal) [HYPO][research_only]."""

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

from scripts.btrack_science_core_v1 import (  # noqa: E402
    build_daily_returns,
    build_macro_gate_by_day,
    build_news_by_published_day,
    compose_science_core,
    load_science_weights,
    macro_lens_at_date,
    news_lens_at_date,
    price_lens_causal_at_index,
)
from scripts.logos_shadow_eval_lib import load_kospi_yf_rows  # noqa: E402
from scripts.run_three_lens_horizon_empirical_eval_v1 import KOSPI_CSV, BTC_CSV  # noqa: E402
from scripts.run_three_lens_horizon_empirical_eval_v2 import _trailing_return_sign  # noqa: E402

DEFAULT_OUT = ROOT / "reports/btrack_science_core_per_date_v1.jsonl"
DEFAULT_ART = ROOT / "docs/final/artifacts/btrack_science_core_per_date_v1.jsonl"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_closes(csv_path: Path) -> dict[str, float]:
    rows = load_kospi_yf_rows(csv_path)
    return {str(r["date"])[:10]: float(r["close"]) for r in rows if r.get("date")}


def build_rows(
    *,
    instrument: str,
    csv_path: Path,
    date_from: str | None,
    date_to: str | None,
    lookback: int,
    apply_overnight: bool,
    exa_jsonl: Path,
) -> list[dict[str, Any]]:
    closes = _load_closes(csv_path)
    trading_days = sorted(closes.keys())
    if date_from:
        trading_days = [d for d in trading_days if d >= date_from]
    if date_to:
        trading_days = [d for d in trading_days if d <= date_to]

    daily_returns = build_daily_returns(closes, sorted(closes.keys()))
    gate_by_day = build_macro_gate_by_day()
    news_by_day = build_news_by_published_day(exa_jsonl)
    weights = load_science_weights()
    all_days = sorted(closes.keys())

    out: list[dict[str, Any]] = []
    for i, dk in enumerate(trading_days):
        try:
            full_idx = all_days.index(dk)
        except ValueError:
            continue
        trailing_dir = _trailing_return_sign(closes, all_days, full_idx, 21, 5.0)
        p_score, p_conf, p_meta = price_lens_causal_at_index(
            daily_returns, all_days, full_idx, lookback=lookback
        )
        m_score, m_conf, m_meta = macro_lens_at_date(
            gate_by_day, dk, trailing_dir=trailing_dir
        )
        n_score, n_conf, n_meta = news_lens_at_date(news_by_day, dk)
        row = compose_science_core(
            price_score=p_score,
            price_conf=p_conf,
            price_meta=p_meta,
            macro_score=m_score,
            macro_conf=m_conf,
            macro_meta=m_meta,
            news_score=n_score,
            news_conf=n_conf,
            news_meta=n_meta,
            weights=weights,
            instrument=instrument,
            session_date=dk,
            apply_overnight=apply_overnight and instrument == "kospi",
        )
        row["built_at_utc"] = _utc_now()
        out.append(row)
    return out


def write_jsonl(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--instrument", choices=("kospi", "btc"), default="kospi")
    ap.add_argument("--date-from", type=str, default="2026-01-01")
    ap.add_argument("--date-to", type=str, default=None)
    ap.add_argument("--lookback", type=int, default=5)
    ap.add_argument("--no-overnight", action="store_true", help="Skip KOSPI overnight overlay on price leg")
    ap.add_argument("--exa-jsonl", type=Path, default=ROOT / "reports/exa_macro_news_observation_staging_v1_latest.jsonl")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--artifact-output", type=Path, default=DEFAULT_ART)
    args = ap.parse_args(argv)

    csv_path = KOSPI_CSV if args.instrument == "kospi" else BTC_CSV
    if not csv_path.is_file():
        print(f"ERROR: missing csv {csv_path}", file=sys.stderr)
        return 1

    rows = build_rows(
        instrument=args.instrument,
        csv_path=csv_path,
        date_from=args.date_from,
        date_to=args.date_to,
        lookback=args.lookback,
        apply_overnight=not args.no_overnight,
        exa_jsonl=args.exa_jsonl,
    )
    write_jsonl(rows, args.output)
    write_jsonl(rows, args.artifact_output)
    print(f"WROTE: {args.output.resolve()} rows={len(rows)} instrument={args.instrument}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
