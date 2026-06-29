#!/usr/bin/env python3
"""[HYPO] KOSPI June 04/05: lookback × calibration × CBO × drawdown grid (wired price_lens_calibration)."""
from __future__ import annotations

import argparse
import copy
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.btrack_ensemble_per_date_core_v1 import compute_per_date_direction_rows  # noqa: E402
from scripts.run_kospi_june_early_miss_cbo_ablation_v1 import (  # noqa: E402
    DEFAULT_BTC,
    DEFAULT_BUNDLE,
    DEFAULT_KOSPI,
    MISS_DATES,
    _apply_spec_ext,
    _bad_dates,
    _eval_dates,
    _hit_metrics,
    _load,
    _miss_pair_metrics,
)
from scripts.logos_shadow_eval_lib import load_kospi_yf_rows  # noqa: E402

DEFAULT_BASE_CFG = ROOT / "reports/kospi_ensemble_hypo_price_lookback3_v1.json"
DEFAULT_OUT = ROOT / "reports/kospi_june_miss_drawdown_calibration_ablation_v1_latest.json"

_WHEN = {"price_score_min": 0.03, "weighted_min": 0.03}
_CBO = lambda **kw: {"enabled": True, "when": {**_WHEN, **kw}, "action": "negate_weighted"}  # noqa: E731

VARIANTS: list[dict[str, Any]] = [
    {"slug": "lb3_baseline"},
    {"slug": "lb1", "price_lookback_days": 1},
    {"slug": "lb2", "price_lookback_days": 2},
    {
        "slug": "lb3_flip_last",
        "price_lens_calibration": {"flip_to_bear_when_last_negative": True},
    },
    {
        "slug": "lb3_blend050_damp060",
        "price_lens_calibration": {"last_day_blend": 0.5, "bear_dampen_if_last_day_negative": 0.6},
    },
    {
        "slug": "lb3_pr_blend040",
        "price_lens_calibration": {"prior_range_blend": 0.4},
    },
    {"slug": "lb3_cbo_last_neg", "conditional_bear_override": _CBO()},
    {"slug": "lb3_cbo_ovn", "conditional_bear_override": _CBO(overnight_negative=True)},
    {
        "slug": "lb3_cbo_dd25",
        "conditional_bear_override": _CBO(drawdown_from_high_below=-0.025),
        "drawdown_lookback_days": 10,
    },
    {
        "slug": "lb3_cbo_dd35_ovn",
        "conditional_bear_override": _CBO(drawdown_from_high_below=-0.035, overnight_negative=True),
        "drawdown_lookback_days": 15,
    },
    {
        "slug": "lb3_news_w_down",
        "weights": {"price": 0.4, "macro": 0.22, "news": 0.08, "myeongni_sasang": 0.3},
    },
    {
        "slug": "lb3_news_flip_last",
        "weights": {"price": 0.4, "macro": 0.22, "news": 0.08, "myeongni_sasang": 0.3},
        "price_lens_calibration": {"flip_to_bear_when_last_negative": True},
    },
    {
        "slug": "lb3_flip_cbo_ovn",
        "price_lens_calibration": {"flip_to_bear_when_last_negative": True},
        "conditional_bear_override": _CBO(overnight_negative=True),
    },
]


def _apply_variant(base: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    cfg = _apply_spec_ext(base, spec)
    rules = dict(cfg.get("rules") or {})
    if "price_lens_calibration" in spec:
        rules["price_lens_calibration"] = copy.deepcopy(spec["price_lens_calibration"])
    if "drawdown_lookback_days" in spec:
        rules["drawdown_lookback_days"] = int(spec["drawdown_lookback_days"])
    cfg["rules"] = rules
    return cfg


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base-config", type=Path, default=DEFAULT_BASE_CFG)
    ap.add_argument("--recent-trading-days", type=int, default=30)
    ap.add_argument("--neutral-bps", type=float, default=6.0)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--write-best-config", type=Path, default=None)
    args = ap.parse_args(argv)

    bundle = _load(DEFAULT_BUNDLE)
    base_cfg = _load(args.base_config if args.base_config.is_absolute() else ROOT / args.base_config)
    eval_dates = _eval_dates(DEFAULT_KOSPI, DEFAULT_BTC, max(1, int(args.recent_trading_days)))
    kospi_rows = load_kospi_yf_rows(DEFAULT_KOSPI)
    exclude_bad = _bad_dates(kospi_rows, eval_dates)

    results: list[dict[str, Any]] = []
    for spec in VARIANTS:
        cfg = _apply_variant(base_cfg, spec)
        rows = compute_per_date_direction_rows(
            bundle=bundle,
            ensemble_cfg=cfg,
            eval_dates=eval_dates,
            ohlc_csv=DEFAULT_KOSPI,
            instrument="kospi",
        )
        june = _hit_metrics(
            rows,
            kospi_rows,
            neutral_bps=float(args.neutral_bps),
            exclude_dates=exclude_bad,
            date_prefix="2026-06",
        )
        panel = _hit_metrics(rows, kospi_rows, neutral_bps=float(args.neutral_bps), exclude_dates=exclude_bad)
        miss_pair = _miss_pair_metrics(june.get("days") or [])
        cbo_n = sum(1 for r in rows if r.get("conditional_bear_override_applied"))
        results.append(
            {
                "slug": spec["slug"],
                "panel_30d": {k: v for k, v in panel.items() if k != "days"},
                "june_tail": {k: v for k, v in june.items() if k != "days"},
                "june_04_05": miss_pair,
                "conditional_bear_applied_count": cbo_n,
            }
        )
        print(
            f"{spec['slug']}: panel={panel.get('hit_rate')} june={june.get('hit_rate')} "
            f"04-05={miss_pair.get('hits')}/2 cbo={cbo_n}"
        )

    def _rank_key(r: dict[str, Any]) -> tuple[float, float, float]:
        j = float(r.get("june_tail", {}).get("hit_rate") or 0)
        m = float(r.get("june_04_05", {}).get("hit_rate") or 0)
        p = float(r.get("panel_30d", {}).get("hit_rate") or 0)
        return (m, j, p)

    best_0405 = max((r for r in results), key=_rank_key, default=None)

    out_doc = {
        "schema": "kospi_june_miss_drawdown_calibration_ablation_v1",
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "miss_dates": list(MISS_DATES),
        "neutral_bps": float(args.neutral_bps),
        "variants": results,
        "best_by_june_04_05_then_june_then_panel": best_0405,
        "note": "price_lens_calibration wired in generate_btrack_hypothesis_prophecy_v1; CBO uses causal last_daily_return.",
    }
    out_path = args.output if args.output.is_absolute() else ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path.resolve()}")

    if args.write_best_config and best_0405:
        spec = next(s for s in VARIANTS if s["slug"] == best_0405["slug"])
        cfg_out = _apply_variant(base_cfg, spec)
        wpath = args.write_best_config if args.write_best_config.is_absolute() else ROOT / args.write_best_config
        wpath.parent.mkdir(parents=True, exist_ok=True)
        wpath.write_text(json.dumps(cfg_out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"WROTE best config: {wpath.resolve()}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
