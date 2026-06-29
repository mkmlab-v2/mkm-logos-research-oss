#!/usr/bin/env python3
"""[HYPO] KOSPI lookback=3 + conditional bear / macro dampen — June 04/05 miss focus."""
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

from scripts.run_kospi_price_vol_dampen_lookback_ablation_v1 import (  # noqa: E402
    DEFAULT_BTC,
    DEFAULT_BUNDLE,
    DEFAULT_KOSPI,
    DEFAULT_KOSPI_CFG,
    _apply_spec,
    _bad_dates,
    _eval_dates,
    _hit_metrics,
    _load,
)
from scripts.btrack_ensemble_per_date_core_v1 import compute_per_date_direction_rows  # noqa: E402
from scripts.logos_shadow_eval_lib import load_kospi_yf_rows  # noqa: E402

DEFAULT_BASE_CFG = ROOT / "reports/kospi_ensemble_hypo_price_lookback3_v1.json"
DEFAULT_OUT = ROOT / "reports/kospi_june_early_miss_cbo_ablation_v1_latest.json"
MISS_DATES = ("2026-06-04", "2026-06-05")

_WHEN_BASE = {"price_score_min": 0.03, "weighted_min": 0.03}
_CBO = lambda **kw: {  # noqa: E731
    "enabled": True,
    "when": {**_WHEN_BASE, **kw},
    "action": "negate_weighted",
}
_VOL_MACRO = {
    "enabled": True,
    "dampen_when_vol_regime_high": True,
    "vol_high_realized_5d": 0.02,
    "vol_high_price_mult": 0.45,
    "dampen_when_macro_bear": True,
    "macro_bear_threshold": 0.0,
    "macro_bear_price_mult": 0.5,
    "dampen_when_overnight_negative": True,
    "overnight_neg_price_mult": 0.55,
}

VARIANTS: list[dict[str, Any]] = [
    {"slug": "lb3_only", "price_lookback_days": 3},
    {"slug": "lb3_cbo_last_neg", "price_lookback_days": 3, "conditional_bear_override": _CBO()},
    {"slug": "lb3_cbo_ovn", "price_lookback_days": 3, "conditional_bear_override": _CBO(overnight_negative=True)},
    {
        "slug": "lb3_cbo_ovn_pr35",
        "price_lookback_days": 3,
        "conditional_bear_override": _CBO(overnight_negative=True, prior_range_low=True, prior_range_low_max=0.35),
    },
    {
        "slug": "lb3_cbo_macro_flip",
        "price_lookback_days": 3,
        "conditional_bear_override": _CBO(require_macro_bull=False, overnight_negative=True, prior_range_high=True, prior_range_high_min=0.7),
    },
    {"slug": "lb3_vol_macro_ovn", "price_lookback_days": 3, "regime_conditional_price_dampen": _VOL_MACRO},
    {
        "slug": "lb3_cbo_ovn_vol",
        "price_lookback_days": 3,
        "conditional_bear_override": _CBO(overnight_negative=True),
        "regime_conditional_price_dampen": _VOL_MACRO,
    },
    {"slug": "lb3_conflict_dampen02", "price_lookback_days": 3, "price_macro_conflict_dampen": 0.2},
    {"slug": "lb3_news_w_down", "price_lookback_days": 3, "weights": {"price": 0.4, "macro": 0.22, "news": 0.08, "myeongni_sasang": 0.3}},
]


def _apply_spec_ext(base: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    cfg = _apply_spec(base, spec)
    rules = dict(cfg.get("rules") or {})
    if "conditional_bear_override" in spec:
        rules["conditional_bear_override"] = copy.deepcopy(spec["conditional_bear_override"])
    if "price_macro_conflict_dampen" in spec:
        rules["price_macro_conflict_dampen"] = float(spec["price_macro_conflict_dampen"])
    cfg["rules"] = rules
    return cfg


def _miss_pair_metrics(days: list[dict[str, Any]]) -> dict[str, Any]:
    by_date = {d["eval_date"]: d for d in days if isinstance(d, dict) and d.get("eval_date")}
    rows = []
    hits = 0
    for ed in MISS_DATES:
        d = by_date.get(ed)
        if not d:
            rows.append({"eval_date": ed, "missing": True})
            continue
        if d.get("hit"):
            hits += 1
        rows.append(d)
    return {"hits": hits, "n": len(MISS_DATES), "hit_rate": round(hits / len(MISS_DATES), 4), "days": rows}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base-config", type=Path, default=DEFAULT_BASE_CFG)
    ap.add_argument("--recent-trading-days", type=int, default=30)
    ap.add_argument("--neutral-bps", type=float, default=6.0)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    bundle = _load(DEFAULT_BUNDLE)
    base_cfg = _load(args.base_config if args.base_config.is_absolute() else ROOT / args.base_config)
    eval_dates = _eval_dates(DEFAULT_KOSPI, DEFAULT_BTC, max(1, int(args.recent_trading_days)))
    kospi_rows = load_kospi_yf_rows(DEFAULT_KOSPI)
    exclude_bad = _bad_dates(kospi_rows, eval_dates)

    results: list[dict[str, Any]] = []
    for spec in VARIANTS:
        cfg = _apply_spec_ext(base_cfg, spec)
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
        panel = _hit_metrics(
            rows,
            kospi_rows,
            neutral_bps=float(args.neutral_bps),
            exclude_dates=exclude_bad,
        )
        miss_pair = _miss_pair_metrics(june.get("days") or [])
        cbo_n = sum(1 for r in rows if r.get("conditional_bear_override_applied"))
        damp_n = sum(1 for r in rows if r.get("regime_price_dampen_applied"))
        results.append(
            {
                "slug": spec["slug"],
                "panel_30d": {k: v for k, v in panel.items() if k != "days"},
                "june_tail": {k: v for k, v in june.items() if k != "days"},
                "june_04_05": miss_pair,
                "conditional_bear_applied_count": cbo_n,
                "regime_price_dampen_applied_count": damp_n,
            }
        )
        print(
            f"{spec['slug']}: panel={panel.get('hit_rate')} june={june.get('hit_rate')} "
            f"04-05={miss_pair.get('hits')}/2 cbo={cbo_n} damp={damp_n}"
        )

    best_june = max(
        (r for r in results if r.get("june_tail", {}).get("hit_rate") is not None),
        key=lambda x: (float(x["june_tail"]["hit_rate"]), float(x["june_04_05"].get("hit_rate") or 0)),
        default=None,
    )
    best_0405 = max(
        (r for r in results if r.get("june_04_05", {}).get("hit_rate") is not None),
        key=lambda x: (
            float(x["june_04_05"]["hit_rate"]),
            float(x["june_tail"].get("hit_rate") or 0),
            float(x["panel_30d"].get("hit_rate") or 0),
        ),
        default=None,
    )

    out_doc = {
        "schema": "kospi_june_early_miss_cbo_ablation_v1",
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "base_config": str(args.base_config),
        "miss_dates": list(MISS_DATES),
        "neutral_bps": float(args.neutral_bps),
        "variants": results,
        "best_by_june_hit_rate": best_june,
        "best_by_june_04_05_hit_rate": best_0405,
        "note": "Targets 06-04/05 bull-into-bear misses on lookback=3 base; not WF holdout.",
    }
    out_path = args.output if args.output.is_absolute() else ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
