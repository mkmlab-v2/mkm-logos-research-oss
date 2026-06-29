#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hybrid B-track score: KOSPI = session per-date directions, BTC = frozen bear ([HYPO])."""

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

from scripts.build_btrack_prophecy_score_from_ohlcv import (  # noqa: E402
    DEFAULT_HYPOTHESIS,
    DEFAULT_KOSPI_CSV,
    SCHEMA,
    _build_rows,
    _last_n_intersection_trading_dates,
    _load_hypothesis,
    _load_per_date_direction_map,
    _predicted_direction,
    _sanitize_ohlcv_rows,
    _utc_now,
)
from scripts.logos_shadow_eval_lib import load_kospi_yf_rows  # noqa: E402


def _rel(p: Path) -> str:
    try:
        return str(p.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--hypothesis-json", type=Path, default=DEFAULT_HYPOTHESIS)
    ap.add_argument(
        "--session-per-date-json",
        type=Path,
        default=ROOT / "reports/btrack_per_date_directions_session_myeongni_30d_v1.json",
    )
    ap.add_argument("--btc-frozen-direction", type=str, default="bear")
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI_CSV)
    ap.add_argument("--btc-csv", type=Path, default=ROOT / "research/market_data/btc_daily_external_yf.csv")
    ap.add_argument("--recent-trading-days", type=int, default=30)
    ap.add_argument("--neutral-bps", type=float, default=5.0)
    ap.add_argument("--output", type=Path, default=ROOT / "reports/btrack_prophecy_score_hybrid_session_kospi_30d_v1.json")
    args = ap.parse_args()

    hyp = _load_hypothesis(args.hypothesis_json)
    if not hyp:
        print("missing hypothesis json", file=sys.stderr)
        return 2

    session_map = _load_per_date_direction_map(args.session_per_date_json)
    if not session_map:
        print("empty session per-date map", file=sys.stderr)
        return 2

    btc_frozen = str(args.btc_frozen_direction).strip().lower()
    if btc_frozen not in ("bull", "bear", "neutral"):
        print("invalid --btc-frozen-direction", file=sys.stderr)
        return 2

    kospi_rows = load_kospi_yf_rows(args.kospi_csv)
    kospi_rows, excluded_kospi = _sanitize_ohlcv_rows(kospi_rows)
    btc_rows = load_kospi_yf_rows(args.btc_csv) if args.btc_csv.is_file() else None
    if btc_rows:
        btc_rows, excluded_btc = _sanitize_ohlcv_rows(btc_rows, bad_dates=frozenset())
        excluded_kospi = sorted(set(excluded_kospi) | set(excluded_btc))
    if not btc_rows:
        print("missing btc csv", file=sys.stderr)
        return 2

    n = max(1, int(args.recent_trading_days))
    dates = _last_n_intersection_trading_dates(kospi_rows, btc_rows, n)
    if not dates:
        print("no intersection trading dates", file=sys.stderr)
        return 2

    rows_out: list[dict[str, Any]] = []
    warnings: list[str] = []
    for ed in dates:
        pred_k = session_map.get(ed)
        if pred_k is None:
            pred_k = _predicted_direction(hyp) or btc_frozen
            warnings.append(f"kospi: no session direction for {ed}; fallback {pred_k}")
        chunk_k, wk = _build_rows(
            hypothesis=hyp,
            eval_date=ed,
            neutral_bps=float(args.neutral_bps),
            kospi_rows=kospi_rows,
            btc_rows=btc_rows,
            inst="kospi",
            predicted=pred_k,
        )
        chunk_b, wb = _build_rows(
            hypothesis=hyp,
            eval_date=ed,
            neutral_bps=float(args.neutral_bps),
            kospi_rows=kospi_rows,
            btc_rows=btc_rows,
            inst="btc",
            predicted=btc_frozen,
        )
        rows_out.extend(chunk_k)
        rows_out.extend(chunk_b)
        warnings.extend(wk.get("warnings", []))
        warnings.extend(wb.get("warnings", []))

    payload = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "eval_date": dates[-1],
        "neutral_bps": float(args.neutral_bps),
        "hypothesis_path": _rel(args.hypothesis_json),
        "inputs": {
            "hybrid_mode": "session_kospi_btc_frozen_bear",
            "session_per_date_direction_json": _rel(args.session_per_date_json),
            "btc_frozen_direction": btc_frozen,
            "kospi_csv": _rel(args.kospi_csv),
            "btc_csv": _rel(args.btc_csv),
            "excluded_bad_ohlcv_dates": excluded_kospi,
            "recent_trading_days": n,
        },
        "meta": {
            "warnings": warnings,
            "batch_eval_dates": dates,
            "hybrid_note": "KOSPI leg uses session 四柱 per-date; BTC leg uses frozen direction only.",
        },
        "rows": rows_out,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE rows={len(rows_out)} dates={len(dates)} path={args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
