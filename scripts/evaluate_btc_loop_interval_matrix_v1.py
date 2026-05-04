#!/usr/bin/env python3
"""Evaluate BTC loop intervals (1/4/6/12/24h) with a simple unified rule.

Fact-Lock intent:
- Compare cadence sensitivity with the same execution model
- Produce reproducible JSON artifact for decision support
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen


def _parse_close_from_csv(path: Path) -> list[float]:
    closes: list[float] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw = (row.get("close") or "").strip()
            if not raw:
                continue
            try:
                closes.append(float(raw))
            except ValueError:
                continue
    if len(closes) < 200:
        raise SystemExit(f"insufficient close rows in csv: {path}")
    return closes


def _fetch_binance_1m_closes(symbol: str, limit: int) -> list[float]:
    want = max(200, int(limit))
    all_rows: list[list[Any]] = []
    end_time_ms: int | None = None

    while len(all_rows) < want:
        page = min(1000, want - len(all_rows))
        params: dict[str, Any] = {"symbol": symbol.upper(), "interval": "1m", "limit": page}
        if end_time_ms is not None:
            params["endTime"] = end_time_ms
        qs = urlencode(params)
        url = f"https://api.binance.com/api/v3/klines?{qs}"
        with urlopen(url, timeout=10) as resp:  # nosec B310
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
        if not isinstance(payload, list) or not payload:
            break
        payload_rows = [r for r in payload if isinstance(r, list) and len(r) >= 6]
        if not payload_rows:
            break
        all_rows = payload_rows + all_rows
        first_open_time = int(payload_rows[0][0])
        end_time_ms = first_open_time - 1
        if len(payload_rows) < page:
            break

    if not all_rows:
        raise SystemExit("failed to fetch klines from binance")
    closes: list[float] = []
    for row in all_rows[-want:]:
        try:
            closes.append(float(row[4]))
        except Exception:
            continue
    if len(closes) < 200:
        raise SystemExit("insufficient klines from binance")
    return closes


@dataclass
class IntervalResult:
    loop_hours: int
    total_return: float
    max_drawdown: float
    sharpe_like: float
    trades: int
    win_rate: float
    fee_paid_ratio: float
    train_score: float
    test_score: float
    stability: float
    score: float


def _max_drawdown(equity: list[float]) -> float:
    peak = equity[0]
    worst = 0.0
    for v in equity:
        if v > peak:
            peak = v
        dd = (peak - v) / peak if peak > 0 else 0.0
        if dd > worst:
            worst = dd
    return worst


def _evaluate_interval(
    closes: list[float],
    *,
    loop_hours: int,
    initial_capital: float,
    position_size: float,
    commission_rate: float,
    entry_threshold: float,
) -> IntervalResult:
    bars = loop_hours * 60
    if len(closes) <= bars * 3:
        return IntervalResult(loop_hours, 0.0, 1.0, -10.0, 0, 0.0, 0.0, -10.0)

    capital = initial_capital
    equity = [capital]
    step_returns: list[float] = []
    trades = 0
    wins = 0
    fee_paid = 0.0

    i = bars
    while i + bars < len(closes):
        prev_close = closes[i - 1]
        lookback_close = closes[i - bars]
        next_close = closes[i + bars - 1]
        if lookback_close <= 0 or prev_close <= 0:
            i += bars
            equity.append(capital)
            step_returns.append(0.0)
            continue

        momentum = (prev_close / lookback_close) - 1.0
        long_on = momentum > entry_threshold

        if long_on:
            r_next = (next_close / prev_close) - 1.0
            notional = capital * position_size
            fee = abs(notional) * commission_rate
            pnl = (notional * r_next) - fee
            trades += 1
            fee_paid += fee
            if pnl > 0:
                wins += 1
            new_capital = capital + pnl
        else:
            new_capital = capital

        step_ret = (new_capital - capital) / capital if capital > 0 else 0.0
        capital = new_capital
        equity.append(capital)
        step_returns.append(step_ret)
        i += bars

    total_return = (capital - initial_capital) / initial_capital
    mdd = _max_drawdown(equity)
    if len(step_returns) >= 2:
        mean_r = statistics.mean(step_returns)
        stdev_r = statistics.pstdev(step_returns)
        sharpe_like = (mean_r / stdev_r) if stdev_r > 0 else 0.0
    else:
        sharpe_like = 0.0
    win_rate = (wins / trades) if trades > 0 else 0.0
    fee_paid_ratio = fee_paid / initial_capital
    # Conservative objective: reward return + stability, penalize DD and fee drag.
    base_score = total_return + (0.1 * sharpe_like) - (0.8 * mdd) - (0.3 * fee_paid_ratio)
    # Walk-forward: first 70% steps as train, last 30% as test
    n_steps = len(step_returns)
    split_idx = max(1, int(n_steps * 0.7))
    train_returns = step_returns[:split_idx]
    test_returns = step_returns[split_idx:] if split_idx < n_steps else step_returns[-1:]

    def _segment_score(seg: list[float]) -> float:
        if not seg:
            return -10.0
        seg_total = 1.0
        for r in seg:
            seg_total *= (1.0 + r)
        seg_ret = seg_total - 1.0
        seg_mu = statistics.mean(seg)
        seg_sd = statistics.pstdev(seg) if len(seg) >= 2 else 0.0
        seg_sharpe = (seg_mu / seg_sd) if seg_sd > 0 else 0.0
        return seg_ret + (0.1 * seg_sharpe)

    train_score = _segment_score(train_returns)
    test_score = _segment_score(test_returns)
    stability = 1.0 / (1.0 + abs(train_score - test_score))
    # Final score emphasizes test segment and consistency.
    score = (0.35 * train_score) + (0.55 * test_score) + (0.10 * stability) - (0.8 * mdd) - (0.3 * fee_paid_ratio)

    return IntervalResult(
        loop_hours=loop_hours,
        total_return=round(total_return, 6),
        max_drawdown=round(mdd, 6),
        sharpe_like=round(sharpe_like, 6),
        trades=trades,
        win_rate=round(win_rate, 6),
        fee_paid_ratio=round(fee_paid_ratio, 6),
        train_score=round(train_score, 6),
        test_score=round(test_score, 6),
        stability=round(stability, 6),
        score=round(score, 6),
    )


def _parse_intervals(raw: str) -> list[int]:
    vals: list[int] = []
    for tok in raw.split(","):
        t = tok.strip()
        if not t:
            continue
        vals.append(int(t))
    uniq = sorted(set(v for v in vals if v > 0))
    if not uniq:
        raise SystemExit("intervals must include at least one positive hour value")
    return uniq


def main() -> int:
    ap = argparse.ArgumentParser(description="Evaluate BTC loop-interval matrix.")
    ap.add_argument("--symbol", default="BTCUSDT")
    ap.add_argument("--input-csv", default="", help="Optional CSV with `close` column.")
    ap.add_argument("--binance-limit", type=int, default=5000, help="Used when --input-csv omitted.")
    ap.add_argument("--intervals", default="1,4,6,12,24")
    ap.add_argument("--initial-capital", type=float, default=10000.0)
    ap.add_argument("--position-size", type=float, default=0.25)
    ap.add_argument("--commission-rate", type=float, default=0.001)
    ap.add_argument("--entry-threshold", type=float, default=0.0)
    ap.add_argument(
        "--out",
        default="docs/final/artifacts/btc_loop_interval_matrix_latest.json",
    )
    args = ap.parse_args()

    if args.input_csv:
        closes = _parse_close_from_csv(Path(args.input_csv))
        data_source = {"type": "csv", "path": str(Path(args.input_csv))}
    else:
        closes = _fetch_binance_1m_closes(args.symbol, args.binance_limit)
        data_source = {"type": "binance_api", "symbol": args.symbol.upper(), "limit": int(args.binance_limit)}

    intervals = _parse_intervals(args.intervals)
    results = [
        _evaluate_interval(
            closes,
            loop_hours=h,
            initial_capital=float(args.initial_capital),
            position_size=float(args.position_size),
            commission_rate=float(args.commission_rate),
            entry_threshold=float(args.entry_threshold),
        )
        for h in intervals
    ]
    results_sorted = sorted(results, key=lambda x: x.score, reverse=True)
    best = results_sorted[0]

    out_doc = {
        "schema": "btc_loop_interval_matrix_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "data_source": data_source,
        "params": {
            "intervals_hours": intervals,
            "initial_capital": float(args.initial_capital),
            "position_size": float(args.position_size),
            "commission_rate": float(args.commission_rate),
            "entry_threshold": float(args.entry_threshold),
            "close_rows": len(closes),
        },
        "results": [asdict(r) for r in results_sorted],
        "recommended": {
            "best_loop_hours": best.loop_hours,
            "best_score": best.score,
            "decision": "adopt_as_primary_loop_candidate",
        },
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

