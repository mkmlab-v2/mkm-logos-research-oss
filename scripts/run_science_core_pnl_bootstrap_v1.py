#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Holdout PnL bootstrap CI for science core combos [HYPO][research_only]."""
from __future__ import annotations

import argparse
import json
import random
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
)
from scripts.run_science_core_horizon_empirical_eval_v1 import DEFAULT_SCIENCE_JSONL_KOSPI  # noqa: E402
from scripts.run_science_core_kospi_combo_backtest_v1 import (  # noqa: E402
    STRATEGY_IDS,
    _predictions_extended,
    _dir_to_sign,
)
from scripts.logos_shadow_eval_lib import load_kospi_yf_rows  # noqa: E402
from scripts.btrack_multilens_per_date_core_v1 import (  # noqa: E402
    logos_global,
    read_jsonl,
    rows_by_calendar_day,
)

DEFAULT_OUT = ROOT / "reports/science_core_pnl_bootstrap_v1_latest.json"
ART_OUT = ROOT / "docs/final/artifacts/science_core_pnl_bootstrap_v1_latest.json"
DEFAULT_MARKET_SASANG = ROOT / "reports/btrack_market_sasang_per_date_v1.jsonl"
DEFAULT_MYEONGNI_PER_DATE = ROOT / "reports/btrack_myeongni_per_date_v1.jsonl"

DEFAULT_HOLDOUT_FROM = "2026-05-01"
DEFAULT_HOLDOUT_TO = "2026-06-08"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _collect_daily_pnls(
    *,
    csv_path: Path,
    science_jsonl: Path,
    myeongni_jsonl: Path,
    sasang_jsonl: Path,
    date_from: str,
    date_to: str,
    fee_bps: float,
    neutral_bps: float,
) -> dict[str, list[float]]:
    rows = sorted(load_kospi_yf_rows(csv_path), key=lambda r: str(r.get("date", "")))
    daily: list[tuple[str, float]] = []
    for i in range(1, len(rows)):
        d = str(rows[i].get("date", ""))[:10]
        try:
            c0 = float(rows[i - 1]["close"])
            c1 = float(rows[i]["close"])
        except (TypeError, ValueError, KeyError):
            continue
        if c0 <= 0:
            continue
        daily.append((d, (c1 - c0) / c0))
    daily = [x for x in daily if date_from <= x[0] <= date_to]

    science_by: dict[str, dict[str, Any]] = {}
    for row in read_jsonl(science_jsonl):
        dk = str(row.get("session_date") or "")[:10]
        if dk:
            science_by[dk] = row
    my_by = rows_by_calendar_day(read_jsonl(myeongni_jsonl))
    sa_by = rows_by_calendar_day(read_jsonl(sasang_jsonl))
    logos_block = logos_global(DEFAULT_LOGOS_LENS)
    fee_rate = fee_bps / 10000.0

    series: dict[str, list[float]] = {sid: [] for sid in STRATEGY_IDS}
    prev_pos: dict[str, int] = {sid: 0 for sid in STRATEGY_IDS}

    for dk, ret in daily:
        preds = _predictions_extended(
            dk,
            science_row=science_by.get(dk),
            myeongni_by_day=my_by,
            sasang_by_day=sa_by,
            logos_block=logos_block,
            myeongni_momentum_window=5,
        )
        for sid in STRATEGY_IDS:
            pos = _dir_to_sign(preds.get(sid, "neutral"))
            turnover = abs(pos - prev_pos[sid])
            pnl = (pos * ret) - (turnover * fee_rate)
            series[sid].append(pnl)
            prev_pos[sid] = pos
    return series


def _bootstrap_total_return(pnls: list[float], *, trials: int, seed: int) -> dict[str, Any]:
    if not pnls:
        return {"n_days": 0, "total_return": None, "ci_95": None}
    rng = random.Random(seed)
    totals: list[float] = []
    n = len(pnls)
    for _ in range(trials):
        eq = 1.0
        for _j in range(n):
            eq *= 1.0 + pnls[rng.randrange(n)]
        totals.append(eq - 1.0)
    totals.sort()
    lo = totals[int(0.025 * trials)]
    hi = totals[int(0.975 * trials)]
    eq0 = 1.0
    for p in pnls:
        eq0 *= 1.0 + p
    return {
        "n_days": n,
        "total_return": round(eq0 - 1.0, 6),
        "ci_95": [round(lo, 6), round(hi, 6)],
    }


def run_bootstrap(
    *,
    science_jsonl: Path,
    myeongni_jsonl: Path,
    sasang_jsonl: Path,
    holdout_from: str,
    holdout_to: str,
    fee_bps: float,
    neutral_bps: float,
    trials: int,
    seed: int,
) -> dict[str, Any]:
    from scripts.run_three_lens_horizon_empirical_eval_v1 import KOSPI_CSV

    series = _collect_daily_pnls(
        csv_path=KOSPI_CSV,
        science_jsonl=science_jsonl,
        myeongni_jsonl=myeongni_jsonl,
        sasang_jsonl=sasang_jsonl,
        date_from=holdout_from,
        date_to=holdout_to,
        fee_bps=fee_bps,
        neutral_bps=neutral_bps,
    )
    strategies = {sid: _bootstrap_total_return(series[sid], trials=trials, seed=seed + i) for i, sid in enumerate(STRATEGY_IDS)}
    science_tr = strategies["science_core"].get("total_return")
    deltas: dict[str, Any] = {}
    for sid in STRATEGY_IDS:
        if sid == "science_core":
            continue
        combo = strategies[sid]
        tr = combo.get("total_return")
        deltas[sid] = {
            "delta_total_return_vs_science": (
                round(float(tr) - float(science_tr), 6) if tr is not None and science_tr is not None else None
            ),
            "ci_95_delta_vs_science": None,
        }
        if tr is not None and science_tr is not None and series[sid] and series["science_core"]:
            rng = random.Random(seed + 99)
            n = min(len(series[sid]), len(series["science_core"]))
            delta_samples: list[float] = []
            for _ in range(trials):
                eq_s = 1.0
                eq_c = 1.0
                for _j in range(n):
                    idx = rng.randrange(n)
                    eq_s *= 1.0 + series["science_core"][idx]
                    eq_c *= 1.0 + series[sid][idx]
                delta_samples.append((eq_c - 1.0) - (eq_s - 1.0))
            delta_samples.sort()
            deltas[sid]["ci_95_delta_vs_science"] = [
                round(delta_samples[int(0.025 * trials)], 6),
                round(delta_samples[int(0.975 * trials)], 6),
            ]

    sasang_delta = (deltas.get("science_plus_sasang") or {}).get("delta_total_return_vs_science")
    ci = (deltas.get("science_plus_sasang") or {}).get("ci_95_delta_vs_science") or [None, None]
    sasang_ci_positive = bool(ci[0] is not None and float(ci[0]) > 0)

    return {
        "schema": "science_core_pnl_bootstrap_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "window": {"from": holdout_from, "to": holdout_to},
        "fee_bps": fee_bps,
        "bootstrap_trials": trials,
        "seed": seed,
        "strategies": strategies,
        "delta_vs_science": deltas,
        "economic_edge_claim_allowed": False,
        "sasang_combo_ci_excludes_zero": sasang_ci_positive,
        "note_ko": (
            "일별 PnL 부트스트랩(페어 resample). research_only — Track A·실매매 승격 근거 아님."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--holdout-from", default=DEFAULT_HOLDOUT_FROM)
    ap.add_argument("--holdout-to", default=DEFAULT_HOLDOUT_TO)
    ap.add_argument("--fee-bps", type=float, default=5.0)
    ap.add_argument("--neutral-bps", type=float, default=5.0)
    ap.add_argument("--trials", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--science-jsonl", type=Path, default=DEFAULT_SCIENCE_JSONL_KOSPI)
    ap.add_argument("--sasang-jsonl", type=Path, default=DEFAULT_MARKET_SASANG)
    ap.add_argument("--myeongni-jsonl", type=Path, default=None)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--artifact-output", type=Path, default=ART_OUT)
    args = ap.parse_args(argv)

    myeongni = args.myeongni_jsonl
    if myeongni is None:
        myeongni = DEFAULT_MYEONGNI_PER_DATE if DEFAULT_MYEONGNI_PER_DATE.is_file() else DEFAULT_MYEONGNI_JSONL

    doc = run_bootstrap(
        science_jsonl=args.science_jsonl,
        myeongni_jsonl=myeongni,
        sasang_jsonl=args.sasang_jsonl,
        holdout_from=args.holdout_from,
        holdout_to=args.holdout_to,
        fee_bps=args.fee_bps,
        neutral_bps=args.neutral_bps,
        trials=max(200, int(args.trials)),
        seed=int(args.seed),
    )
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.artifact_output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(payload, encoding="utf-8")
    args.artifact_output.write_text(payload, encoding="utf-8")
    sasang = doc["strategies"].get("science_plus_sasang") or {}
    print(f"WROTE: {args.output.resolve()} sasang_tr={sasang.get('total_return')} ci={sasang.get('ci_95')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
