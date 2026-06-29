#!/usr/bin/env python3
"""[HYPO] KOSPI 06-04 miss: overnight_blend × prior_range_low flip on pr_blend040 base."""
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
    _bad_dates,
    _eval_dates,
    _hit_metrics,
    _load,
    _miss_pair_metrics,
)
from scripts.logos_shadow_eval_lib import load_kospi_yf_rows  # noqa: E402

DEFAULT_BASE = ROOT / "reports/kospi_ensemble_hypo_lb3_pr_blend040_v1.json"
DEFAULT_OUT = ROOT / "reports/kospi_june04_overnight_pr_low_ablation_v1_latest.json"
TARGET_DATE = "2026-06-04"

_PR = {"prior_range_blend": 0.4}

VARIANTS: list[dict[str, Any]] = [
    {"slug": "pr_blend040"},
    {"slug": "ovn030", "price_lens_calibration": {**_PR, "overnight_blend": 0.3}},
    {"slug": "ovn040", "price_lens_calibration": {**_PR, "overnight_blend": 0.4}},
    {"slug": "ovn050", "price_lens_calibration": {**_PR, "overnight_blend": 0.5}},
    {"slug": "prlow035", "price_lens_calibration": {**_PR, "flip_to_bear_when_prior_range_low": True, "prior_range_low_threshold": 0.35}},
    {"slug": "prlow030", "price_lens_calibration": {**_PR, "flip_to_bear_when_prior_range_low": True, "prior_range_low_threshold": 0.3}},
    {"slug": "ovn040_prlow035", "price_lens_calibration": {**_PR, "overnight_blend": 0.4, "flip_to_bear_when_prior_range_low": True, "prior_range_low_threshold": 0.35}},
    {"slug": "ovn050_prlow035", "price_lens_calibration": {**_PR, "overnight_blend": 0.5, "flip_to_bear_when_prior_range_low": True, "prior_range_low_threshold": 0.35}},
    {"slug": "lb2_pr_blend", "price_lookback_days": 2, "price_lens_calibration": dict(_PR)},
    {"slug": "lb2_ovn040", "price_lookback_days": 2, "price_lens_calibration": {**_PR, "overnight_blend": 0.4}},
    {"slug": "lb2_ovn040_prlow035", "price_lookback_days": 2, "price_lens_calibration": {**_PR, "overnight_blend": 0.4, "flip_to_bear_when_prior_range_low": True, "prior_range_low_threshold": 0.35}},
    {"slug": "blend_last050_ovn040", "price_lens_calibration": {**_PR, "last_day_blend": 0.5, "overnight_blend": 0.4}},
]


def _apply(base: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    cfg = copy.deepcopy(base)
    rules = dict(cfg.get("rules") or {})
    rules["price_instrument"] = "kospi"
    rules["enforce_btc_only_guard"] = False
    rules["kospi_overnight_overlay_enabled"] = False
    if "price_lookback_days" in spec:
        rules["price_lookback_days"] = int(spec["price_lookback_days"])
    if "price_lens_calibration" in spec:
        rules["price_lens_calibration"] = copy.deepcopy(spec["price_lens_calibration"])
    cfg["rules"] = rules
    return cfg


def _day_hit(days: list[dict[str, Any]], ed: str) -> dict[str, Any] | None:
    for d in days:
        if d.get("eval_date") == ed:
            return d
    return None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base-config", type=Path, default=DEFAULT_BASE)
    ap.add_argument("--recent-trading-days", type=int, default=30)
    ap.add_argument("--neutral-bps", type=float, default=6.0)
    ap.add_argument("--target-date", default=TARGET_DATE)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--write-leading-config", type=Path, default=None)
    args = ap.parse_args(argv)

    bundle = _load(DEFAULT_BUNDLE)
    base_cfg = _load(args.base_config if args.base_config.is_absolute() else ROOT / args.base_config)
    eval_dates = _eval_dates(DEFAULT_KOSPI, DEFAULT_BTC, max(1, int(args.recent_trading_days)))
    kospi_rows = load_kospi_yf_rows(DEFAULT_KOSPI)
    exclude_bad = _bad_dates(kospi_rows, eval_dates)
    target = str(args.target_date)[:10]

    results: list[dict[str, Any]] = []
    for spec in VARIANTS:
        cfg = _apply(base_cfg, spec)
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
        j04 = _day_hit(june.get("days") or [], target)
        results.append(
            {
                "slug": spec["slug"],
                "panel_30d": {k: v for k, v in panel.items() if k != "days"},
                "june_tail": {k: v for k, v in june.items() if k != "days"},
                "june_04_05": miss_pair,
                f"target_{target}": j04,
            }
        )
        j04_hit = j04.get("hit") if j04 else None
        print(
            f"{spec['slug']}: panel={panel.get('hit_rate')} june={june.get('hit_rate')} "
            f"04-05={miss_pair.get('hits')}/2 {target}_hit={j04_hit}"
        )

    def rank(r: dict[str, Any]) -> tuple:
        t = r.get(f"target_{target}") or {}
        j = float(r.get("june_tail", {}).get("hit_rate") or 0)
        p = float(r.get("panel_30d", {}).get("hit_rate") or 0)
        m = float(r.get("june_04_05", {}).get("hit_rate") or 0)
        return (1 if t.get("hit") else 0, m, j, p)

    best = max(results, key=rank)

    out_doc = {
        "schema": "kospi_june04_overnight_pr_low_ablation_v1",
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "target_date": target,
        "causal_probe_2026_06_04": {
            "overnight_return": -0.02019,
            "prior_range_position": 0.2804,
            "note": "Gap-down open; pr_blend040 alone still bull without overnight_blend.",
        },
        "variants": results,
        "best_by_target_then_june_then_panel": best,
    }
    out_path = args.output if args.output.is_absolute() else ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path.resolve()} best={best.get('slug')}")

    if args.write_leading_config:
        spec = next(s for s in VARIANTS if s["slug"] == best["slug"])
        cfg_out = _apply(base_cfg, spec)
        cfg_out["note"] = "[HYPO] leading candidate from june04 overnight/pr_low ablation — not Track A."
        wpath = args.write_leading_config if args.write_leading_config.is_absolute() else ROOT / args.write_leading_config
        wpath.parent.mkdir(parents=True, exist_ok=True)
        wpath.write_text(json.dumps(cfg_out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"WROTE leading: {wpath.resolve()}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
