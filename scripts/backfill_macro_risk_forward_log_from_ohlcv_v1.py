#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Research backfill for macro_risk forward log from OHLCV [HYPO][research_only].

Fills causal-as-of gaps before operational Track C logs exist. Does not overwrite
the operational append-only log — writes a separate research JSONL consumed by v2 eval.
"""

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

import scripts.run_three_lens_horizon_empirical_eval_v1 as v1  # noqa: E402
from scripts.logos_shadow_eval_lib import load_kospi_yf_rows  # noqa: E402

DEFAULT_CSV = v1.KOSPI_CSV
DEFAULT_OUT = ROOT / "reports/macro_risk/forward/macro_risk_forward_log_research_backfill_v1.jsonl"
VOL_LOOKBACK = 120
VOL_WINDOW = 20


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_closes(csv_path: Path) -> tuple[list[str], dict[str, float]]:
    rows = load_kospi_yf_rows(csv_path)
    closes = {str(r["date"])[:10]: float(r["close"]) for r in rows if r.get("date")}
    return sorted(closes.keys()), closes


def _realized_vol(closes: dict[str, float], days: list[str], end_idx: int, window: int) -> float | None:
    if end_idx < window:
        return None
    rets: list[float] = []
    for j in range(end_idx - window + 1, end_idx + 1):
        if j <= 0:
            return None
        c0 = closes.get(days[j - 1])
        c1 = closes.get(days[j])
        if c0 is None or c1 is None or c0 == 0:
            return None
        rets.append(abs((c1 - c0) / c0))
    return sum(rets) / len(rets) if rets else None


def _percentile_rank(value: float, history: list[float]) -> float:
    if not history:
        return 50.0
    xs = sorted(history)
    below = sum(1 for x in xs if x < value)
    return 100.0 * below / len(xs)


def _decision_from_ohlcv(
    *,
    ret21: float | None,
    vol_pct: float | None,
    neutral_bps: float,
    vol_stress_pct: float,
    watch_mode: str = "neutral",
    vol_only_stress: bool = True,
) -> tuple[str, str]:
    thr = neutral_bps / 10000.0
    elevated = vol_pct is not None and vol_pct >= vol_stress_pct
    watch_mode = (watch_mode or "neutral").strip().lower()

    if ret21 is None:
        if vol_only_stress and elevated:
            return "WATCH", "elevated"
        return ("CALM", "low") if watch_mode == "neutral" else ("WATCH", "medium")

    in_band = abs(ret21) <= thr

    if vol_only_stress:
        if elevated:
            return "WATCH", "elevated"
        if ret21 > thr:
            return "GO", "medium"
        if ret21 < -thr:
            return "REDUCE", "elevated"
        return "CALM", "low"

    if elevated and in_band:
        return "WATCH", "elevated"
    if ret21 > thr:
        return "GO", "medium"
    if ret21 < -thr:
        return "REDUCE", "elevated"
    return ("CALM", "low") if watch_mode == "neutral" else ("WATCH", "medium")


def build_backfill_rows(
    *,
    csv_path: Path,
    date_from: str | None,
    date_to: str | None,
    neutral_bps: float,
    vol_stress_pct: float,
    watch_mode: str = "neutral",
    vol_only_stress: bool = True,
    heuristic_version: str = "ohlcv_research_backfill_v2",
) -> list[dict[str, Any]]:
    trading_days, closes = _load_closes(csv_path)
    if date_from:
        trading_days = [d for d in trading_days if d >= date_from]
    if date_to:
        trading_days = [d for d in trading_days if d <= date_to]

    all_days, all_closes = _load_closes(csv_path)
    day_to_idx = {d: i for i, d in enumerate(all_days)}

    rows: list[dict[str, Any]] = []
    for dk in trading_days:
        idx = day_to_idx.get(dk)
        if idx is None:
            continue
        ret21 = v1._forward_return(all_closes, all_days, idx, 21)
        vol20 = _realized_vol(all_closes, all_days, idx, VOL_WINDOW)
        vol_hist: list[float] = []
        if vol20 is not None:
            for k in range(max(VOL_WINDOW, idx - VOL_LOOKBACK), idx):
                v = _realized_vol(all_closes, all_days, k, VOL_WINDOW)
                if v is not None:
                    vol_hist.append(v)
        vol_pct = _percentile_rank(vol20, vol_hist) if vol20 is not None and vol_hist else None
        decision, risk_level = _decision_from_ohlcv(
            ret21=ret21,
            vol_pct=vol_pct,
            neutral_bps=neutral_bps,
            vol_stress_pct=vol_stress_pct,
            watch_mode=watch_mode,
            vol_only_stress=vol_only_stress,
        )
        rows.append(
            {
                "schema": "macro_risk_forward_log_row_v1_research_backfill",
                "session_date": dk,
                "logged_at_utc": f"{dk}T09:00:00Z",
                "source_label": heuristic_version,
                "heuristic_version": heuristic_version,
                "watch_mode": watch_mode,
                "vol_only_stress": vol_only_stress,
                "decision_state": decision,
                "risk_warning_level": risk_level,
                "features": {
                    "ret21": round(ret21, 6) if ret21 is not None else None,
                    "vol20": round(vol20, 6) if vol20 is not None else None,
                    "vol_percentile_120d": round(vol_pct, 2) if vol_pct is not None else None,
                },
                "hypothesis_tier": "B",
                "research_only": True,
                "note_ko": "운영 macro_risk 로그 이전 구간 OHLCV 프록시 — Track C 인과 로그 대체 아님.",
            }
        )
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    ap.add_argument("--date-from", type=str, default="2026-01-01")
    ap.add_argument("--date-to", type=str, default="2026-04-30")
    ap.add_argument("--neutral-bps", type=float, default=5.0)
    ap.add_argument("--vol-stress-pct", type=float, default=75.0)
    ap.add_argument("--watch-mode", choices=("neutral", "bear"), default="neutral")
    ap.add_argument("--vol-only-stress", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--heuristic-version", type=str, default="ohlcv_research_backfill_v2")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    rows = build_backfill_rows(
        csv_path=args.csv,
        date_from=args.date_from,
        date_to=args.date_to,
        neutral_bps=args.neutral_bps,
        vol_stress_pct=args.vol_stress_pct,
        watch_mode=args.watch_mode,
        vol_only_stress=args.vol_only_stress,
        heuristic_version=args.heuristic_version,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"WROTE: {args.output.resolve()} rows={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
