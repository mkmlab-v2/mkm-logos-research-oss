#!/usr/bin/env python3
"""[HYPO] KOSPI per-date ensemble min_conf / margin grid (clean panel hit-rate)."""
from __future__ import annotations

import argparse
import copy
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.btrack_ensemble_per_date_core_v1 import compute_per_date_direction_rows  # noqa: E402
from scripts.build_btrack_prophecy_score_from_ohlcv import (  # noqa: E402
    _actual_direction,
    _last_n_intersection_trading_dates,
    _row_pair_for_eval_date,
)
from scripts.logos_shadow_eval_lib import load_kospi_yf_rows  # noqa: E402

DEFAULT_BUNDLE = ROOT / "docs/final/artifacts/btrack_llm_input_bundle_latest.json"
DEFAULT_CFG = ROOT / "docs/final/artifacts/btrack_lens_ensemble_v1.json"
DEFAULT_BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
DEFAULT_KOSPI = ROOT / "research/market_data/kospi_daily_external_yf.csv"
DEFAULT_OUT = ROOT / "reports/kospi_per_date_ensemble_ablation_v1_latest.json"

GRID: list[dict[str, Any]] = [
    {"slug": "baseline"},
    {"slug": "min_conf_020", "min_direction_confidence": 0.20},
    {"slug": "min_conf_022", "min_direction_confidence": 0.22},
    {"slug": "min_conf_025", "min_direction_confidence": 0.25},
    {"slug": "margin_040", "tie_break_min_margin": 0.04},
    {"slug": "margin_050", "tie_break_min_margin": 0.05},
    {"slug": "margin040_min022", "tie_break_min_margin": 0.04, "min_direction_confidence": 0.22},
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _eval_dates(kospi_csv: Path, btc_csv: Path, n: int) -> list[str]:
    kospi_rows = load_kospi_yf_rows(kospi_csv)
    btc_rows = load_kospi_yf_rows(btc_csv)
    return _last_n_intersection_trading_dates(kospi_rows, btc_rows, n)


def _kospi_hit_rate(
    per_date_rows: list[dict[str, Any]],
    kospi_rows: list[dict[str, Any]],
    *,
    neutral_bps: float,
    exclude_dates: set[str],
) -> dict[str, Any]:
    hits = 0
    n = 0
    gate_applied = 0
    dist: Counter[str] = Counter()
    for r in per_date_rows:
        ed = str(r.get("eval_date") or "")[:10]
        if not ed or ed in exclude_dates:
            continue
        pred = str(r.get("predicted_direction") or "neutral")
        pair = _row_pair_for_eval_date(kospi_rows, ed)
        if pair is None:
            continue
        prev_r, cur_r = pair
        ret = (float(cur_r["close"]) - float(prev_r["close"])) / float(prev_r["close"])
        if abs(ret) > 0.15:
            continue
        act = _actual_direction(ret, neutral_bps)
        n += 1
        dist[pred] += 1
        if (r.get("low_confidence_direction_gate") or {}).get("applied"):
            gate_applied += 1
        if pred == act:
            hits += 1
    return {
        "hits": hits,
        "n": n,
        "hit_rate": round(hits / n, 4) if n else None,
        "pred_distribution": dict(dist),
        "low_confidence_gate_applied_count": gate_applied,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--recent-trading-days", type=int, default=30)
    ap.add_argument("--neutral-bps", type=float, default=5.0)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    bundle = _load(DEFAULT_BUNDLE)
    base_cfg = _load(DEFAULT_CFG)
    eval_dates = _eval_dates(DEFAULT_KOSPI, DEFAULT_BTC, max(1, int(args.recent_trading_days)))
    kospi_rows = load_kospi_yf_rows(DEFAULT_KOSPI)
    exclude_bad = {
        ed
        for ed in eval_dates
        if (pair := _row_pair_for_eval_date(kospi_rows, ed))
        and abs((float(pair[1]["close"]) - float(pair[0]["close"])) / float(pair[0]["close"])) > 0.15
    }

    results: list[dict[str, Any]] = []
    for spec in GRID:
        cfg = copy.deepcopy(base_cfg)
        rules = dict(cfg.get("rules") or {})
        rules["price_instrument"] = "kospi"
        rules["enforce_btc_only_guard"] = False
        for k in ("min_direction_confidence", "tie_break_min_margin", "neutral_penalty"):
            if k in spec:
                rules[k] = spec[k]
        cfg["rules"] = rules
        rows = compute_per_date_direction_rows(
            bundle=bundle,
            ensemble_cfg=cfg,
            eval_dates=eval_dates,
            ohlc_csv=DEFAULT_KOSPI,
            instrument="kospi",
        )
        metrics = _kospi_hit_rate(
            rows,
            kospi_rows,
            neutral_bps=float(args.neutral_bps),
            exclude_dates=exclude_bad,
        )
        results.append({"slug": spec["slug"], "overrides": {k: spec[k] for k in spec if k != "slug"}, **metrics})

    best = max((r for r in results if r.get("hit_rate") is not None), key=lambda x: x["hit_rate"], default=None)
    out = {
        "schema": "kospi_per_date_ensemble_ablation_v1",
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "generated_at_utc": _utc_now(),
        "eval_dates_n": len(eval_dates),
        "excluded_bad_ohlcv_dates": sorted(exclude_bad),
        "neutral_bps": float(args.neutral_bps),
        "variants": results,
        "best_by_clean_kospi_hit_rate": best,
        "note": "KOSPI leg only; clean panel excludes |daily_return|>15%. Not WF holdout.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()} best={best.get('slug') if best else None} hr={best.get('hit_rate') if best else None}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
