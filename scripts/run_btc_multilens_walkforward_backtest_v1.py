#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BTC multilens rolling walk-forward (candidate prefilter) [HYPO][research_only].

Calendar axis = KRX session dates present in panel AND BTC OHLCV (weekdays with panel row).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_kospi_june2026_daily_prophecy_calendar_v1 import _read_json  # noqa: E402
from scripts.run_kospi_multilens_blend_backtest_v1 import (  # noqa: E402
    EVOLUTION_RULES,
    _load_closes,
    _load_panel,
    run_backtest,
)

BTC_CSV = ROOT / "research/market_data/btc_daily_external_yf.csv"
DEFAULT_PANEL = ROOT / "reports/btrack_session_myeongni_panel_full_window_v1.csv"
DEFAULT_OUT = ROOT / "reports/btc_multilens_walkforward_backtest_latest.json"
ART_OUT = ROOT / "docs/final/artifacts/btc_multilens_walkforward_backtest_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _eval_dates(panel_by_date: dict[str, dict[str, str]], closes: dict[str, float]) -> list[str]:
    return sorted(d for d in panel_by_date if d in closes)


def _metrics_tuple(v: dict[str, Any]) -> tuple[float, float, int]:
    m = v.get("metrics") if isinstance(v.get("metrics"), dict) else {}
    return (
        float(m.get("soft_hit_rate") or -1.0),
        float(m.get("directional_hit_rate") or -1.0),
        int(m.get("n_scored") or 0),
    )


def run_walkforward(
    *,
    panel_by_date: dict[str, dict[str, str]],
    closes: dict[str, float],
    train_days: int,
    test_days: int,
    step_days: int,
    max_window_days: int | None,
    rules: dict[str, Any],
    neutral_bps: float,
) -> dict[str, Any]:
    dates = _eval_dates(panel_by_date, closes)
    if not dates:
        raise RuntimeError("No overlapping panel/BTC dates")
    if max_window_days and max_window_days > 0 and len(dates) > max_window_days:
        dates = dates[-max_window_days:]

    folds: list[dict[str, Any]] = []
    pos = train_days
    while pos + test_days <= len(dates):
        train_from = dates[pos - train_days]
        train_to = dates[pos - 1]
        test_from = dates[pos]
        test_to = dates[pos + test_days - 1]

        train_doc = run_backtest(
            panel_by_date=panel_by_date,
            closes=closes,
            date_from=train_from,
            date_to=train_to,
            rules=rules,
            neutral_bps=neutral_bps,
        )
        best = train_doc.get("best_variant") or {}
        best_id = str(best.get("variant_id") or "")
        if best_id:
            test_doc = run_backtest(
                panel_by_date=panel_by_date,
                closes=closes,
                date_from=test_from,
                date_to=test_to,
                rules=rules,
                neutral_bps=neutral_bps,
            )
            match = next(
                (r for r in (test_doc.get("variants") or []) if str(r.get("variant_id")) == best_id),
                None,
            )
            top_test = sorted((test_doc.get("variants") or []), key=_metrics_tuple, reverse=True)
            folds.append(
                {
                    "train_window": {"date_from": train_from, "date_to": train_to},
                    "test_window": {"date_from": test_from, "date_to": test_to},
                    "selected_from_train": best_id,
                    "selected_test_metrics": (match or {}).get("metrics"),
                    "test_best_variant": (top_test[0] if top_test else {}).get("variant_id"),
                    "test_best_metrics": (top_test[0] if top_test else {}).get("metrics"),
                    "selection_hits_test_top1": bool(top_test and str(top_test[0].get("variant_id")) == best_id),
                }
            )
        pos += step_days

    by_variant: dict[str, list[float]] = {}
    top1_hits = 0
    lens3_softs: list[float] = []
    for f in folds:
        vid = str(f.get("selected_from_train") or "")
        soft = ((f.get("selected_test_metrics") or {}).get("soft_hit_rate"))
        if vid and soft is not None:
            by_variant.setdefault(vid, []).append(float(soft))
        if f.get("selection_hits_test_top1"):
            top1_hits += 1
        if vid == "v2_lens3_heavy" and soft is not None:
            lens3_softs.append(float(soft))

    variant_rank = sorted(
        (
            {
                "variant_id": vid,
                "n_folds": len(vals),
                "mean_soft_hit_rate_test": round(mean(vals), 4),
            }
            for vid, vals in by_variant.items()
        ),
        key=lambda x: (float(x["mean_soft_hit_rate_test"]), int(x["n_folds"])),
        reverse=True,
    )

    top2 = [v["variant_id"] for v in variant_rank[:2]]
    lens3_in_top2 = any(str(v).startswith("v2_lens3_heavy") for v in top2)

    return {
        "schema": "btc_multilens_walkforward_backtest_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "track_wall": "no_track_a_live_auto_merge",
        "instrument": "btc",
        "available_calendar_days": len(_eval_dates(panel_by_date, closes)),
        "effective_window_days": len(dates),
        "config": {
            "train_days": train_days,
            "test_days": test_days,
            "step_days": step_days,
            "max_window_days": max_window_days,
        },
        "folds": folds,
        "summary": {
            "n_folds": len(folds),
            "selection_top1_hit_rate": round(top1_hits / len(folds), 4) if folds else None,
            "variant_rank_by_test_mean_soft": variant_rank,
            "recommended_prefilter_variants_top2": top2,
            "v2_lens3_heavy_in_top2": lens3_in_top2,
            "v2_lens3_heavy_mean_test_soft": round(mean(lens3_softs), 4) if lens3_softs else None,
            "note_ko": "BTC-USD 수익률·KRX 세션 패널 교차 검증. June apply 판정 대체 아님.",
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--panel-csv", type=Path, default=DEFAULT_PANEL)
    ap.add_argument("--btc-csv", type=Path, default=BTC_CSV)
    ap.add_argument("--train-days", type=int, default=756)
    ap.add_argument("--test-days", type=int, default=252)
    ap.add_argument("--step-days", type=int, default=126)
    ap.add_argument("--max-window-days", type=int, default=0, help="0=all overlapping dates")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    if not args.btc_csv.is_file():
        print(f"Missing BTC CSV: {args.btc_csv}", file=sys.stderr)
        return 2
    if not args.panel_csv.is_file():
        print(f"Missing panel CSV: {args.panel_csv}", file=sys.stderr)
        return 2

    panel_by_date = _load_panel(args.panel_csv)
    closes = _load_closes(args.btc_csv)
    dates = _eval_dates(panel_by_date, closes)
    if len(dates) < (args.train_days + args.test_days):
        print(
            f"Not enough overlapping dates ({len(dates)}) for train={args.train_days} test={args.test_days}",
            file=sys.stderr,
        )
        return 2

    rules = _read_json(EVOLUTION_RULES)
    neutral_bps = float(rules.get("neutral_bps", 5.0))
    max_days = args.max_window_days if args.max_window_days > 0 else None
    doc = run_walkforward(
        panel_by_date=panel_by_date,
        closes=closes,
        train_days=args.train_days,
        test_days=args.test_days,
        step_days=args.step_days,
        max_window_days=max_days,
        rules=rules,
        neutral_bps=neutral_bps,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.output.write_text(payload, encoding="utf-8")
    ART_OUT.parent.mkdir(parents=True, exist_ok=True)
    ART_OUT.write_text(payload, encoding="utf-8")
    s = doc.get("summary") or {}
    print(
        f"WROTE: {args.output.resolve()} folds={s.get('n_folds')} "
        f"top1_hit={s.get('selection_top1_hit_rate')} top2={s.get('recommended_prefilter_variants_top2')} "
        f"lens3_top2={s.get('v2_lens3_heavy_in_top2')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
