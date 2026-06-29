#!/usr/bin/env python3
"""[HYPO] KOSPI price lookback × vol/macro dampen grid — 30d + June 2026 tail."""
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
DEFAULT_KOSPI_CFG = ROOT / "docs/final/artifacts/btrack_lens_ensemble_kospi_per_date_v1.json"
DEFAULT_BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
DEFAULT_KOSPI = ROOT / "research/market_data/kospi_daily_external_yf.csv"
DEFAULT_OUT = ROOT / "reports/kospi_price_vol_dampen_lookback_ablation_v1_latest.json"
JUNE_PREFIX = "2026-06"

_VOL_STD = {
    "enabled": True,
    "dampen_when_vol_regime_high": True,
    "vol_high_realized_5d": 0.03,
    "vol_high_price_mult": 0.6,
    "dampen_when_macro_bear": False,
    "dampen_when_overnight_negative": False,
}
_VOL_STRONG = {
    **_VOL_STD,
    "vol_high_realized_5d": 0.025,
    "vol_high_price_mult": 0.45,
}
_VOL_MACRO = {
    **_VOL_STD,
    "dampen_when_macro_bear": True,
    "macro_bear_threshold": 0.0,
    "macro_bear_price_mult": 0.55,
}
_VOL_ALL = {
    **_VOL_MACRO,
    "dampen_when_overnight_negative": True,
    "overnight_neg_price_mult": 0.5,
}

VARIANTS: list[dict[str, Any]] = [
    {"slug": "baseline_lb5"},
    {"slug": "vol_dampen_std", "regime_conditional_price_dampen": _VOL_STD},
    {"slug": "vol_dampen_strong", "regime_conditional_price_dampen": _VOL_STRONG},
    {"slug": "vol_macro_bear", "regime_conditional_price_dampen": _VOL_MACRO},
    {"slug": "vol_all_triggers", "regime_conditional_price_dampen": _VOL_ALL},
    {"slug": "lookback_3", "price_lookback_days": 3},
    {"slug": "lookback_10", "price_lookback_days": 10},
    {"slug": "lb3_vol_strong", "price_lookback_days": 3, "regime_conditional_price_dampen": _VOL_STRONG},
    {"slug": "lb3_vol_all", "price_lookback_days": 3, "regime_conditional_price_dampen": _VOL_ALL},
    {"slug": "price_w055", "weights": {"price": 0.55, "macro": 0.2, "news": 0.1, "myeongni_sasang": 0.15}},
    {"slug": "price_w045_vol_strong", "weights": {"price": 0.45, "macro": 0.22, "news": 0.12, "myeongni_sasang": 0.21}, "regime_conditional_price_dampen": _VOL_STRONG},
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _eval_dates(kospi_csv: Path, btc_csv: Path, n: int) -> list[str]:
    kospi_rows = load_kospi_yf_rows(kospi_csv)
    btc_rows = load_kospi_yf_rows(btc_csv)
    return _last_n_intersection_trading_dates(kospi_rows, btc_rows, n)


def _bad_dates(kospi_rows: list[dict[str, Any]], dates: list[str]) -> set[str]:
    out: set[str] = set()
    for ed in dates:
        pair = _row_pair_for_eval_date(kospi_rows, ed)
        if pair is None:
            continue
        prev_r, cur_r = pair
        ret = abs((float(cur_r["close"]) - float(prev_r["close"])) / float(prev_r["close"]))
        if ret > 0.15:
            out.add(ed)
    return out


def _hit_metrics(
    per_date_rows: list[dict[str, Any]],
    kospi_rows: list[dict[str, Any]],
    *,
    neutral_bps: float,
    exclude_dates: set[str],
    date_prefix: str | None = None,
) -> dict[str, Any]:
    hits = 0
    n = 0
    dampen_applied = 0
    dist: Counter[str] = Counter()
    day_detail: list[dict[str, Any]] = []
    for r in per_date_rows:
        ed = str(r.get("eval_date") or "")[:10]
        if not ed or ed in exclude_dates:
            continue
        if date_prefix and not ed.startswith(date_prefix):
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
        if r.get("regime_price_dampen_applied"):
            dampen_applied += 1
        hit = pred == act
        if hit:
            hits += 1
        price_lens = (r.get("lens_values") or {}).get("price") if isinstance(r.get("lens_values"), dict) else {}
        day_detail.append(
            {
                "eval_date": ed,
                "pred": pred,
                "actual": act,
                "hit": hit,
                "ret_pct": round(ret * 100, 4),
                "regime_price_dampen_applied": bool(r.get("regime_price_dampen_applied")),
                "vol_regime_high": r.get("vol_regime_high"),
                "price_lens_score": price_lens.get("score") if isinstance(price_lens, dict) else None,
            }
        )
    return {
        "hits": hits,
        "n": n,
        "hit_rate": round(hits / n, 4) if n else None,
        "pred_distribution": dict(dist),
        "regime_price_dampen_applied_count": dampen_applied,
        "days": day_detail,
    }


def _apply_spec(cfg: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(cfg)
    rules = dict(out.get("rules") or {})
    rules["price_instrument"] = "kospi"
    rules["enforce_btc_only_guard"] = False
    rules["kospi_overnight_overlay_enabled"] = False
    if "price_lookback_days" in spec:
        rules["price_lookback_days"] = int(spec["price_lookback_days"])
    if "regime_conditional_price_dampen" in spec:
        rules["regime_conditional_price_dampen"] = copy.deepcopy(spec["regime_conditional_price_dampen"])
        rv = rules["regime_conditional_price_dampen"].get("vol_high_realized_5d")
        if rv is not None:
            rules["vol_high_realized_5d"] = rv
    if "weights" in spec:
        out["weights"] = copy.deepcopy(spec["weights"])
    out["rules"] = rules
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--recent-trading-days", type=int, default=30)
    ap.add_argument("--neutral-bps", type=float, default=6.0)
    ap.add_argument("--june-prefix", default=JUNE_PREFIX)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--write-best-config", type=Path, default=None, help="Optional path to write best-June config JSON")
    args = ap.parse_args(argv)

    bundle = _load(DEFAULT_BUNDLE)
    base_cfg = _load(DEFAULT_KOSPI_CFG)
    eval_dates = _eval_dates(DEFAULT_KOSPI, DEFAULT_BTC, max(1, int(args.recent_trading_days)))
    kospi_rows = load_kospi_yf_rows(DEFAULT_KOSPI)
    exclude_bad = _bad_dates(kospi_rows, eval_dates)

    results: list[dict[str, Any]] = []
    for spec in VARIANTS:
        cfg = _apply_spec(base_cfg, spec)
        rows = compute_per_date_direction_rows(
            bundle=bundle,
            ensemble_cfg=cfg,
            eval_dates=eval_dates,
            ohlc_csv=DEFAULT_KOSPI,
            instrument="kospi",
        )
        panel = _hit_metrics(
            rows,
            kospi_rows,
            neutral_bps=float(args.neutral_bps),
            exclude_dates=exclude_bad,
        )
        june = _hit_metrics(
            rows,
            kospi_rows,
            neutral_bps=float(args.neutral_bps),
            exclude_dates=exclude_bad,
            date_prefix=str(args.june_prefix),
        )
        results.append(
            {
                "slug": spec["slug"],
                "overrides": {k: v for k, v in spec.items() if k != "slug"},
                "panel_30d": {k: v for k, v in panel.items() if k != "days"},
                "june_tail": june,
            }
        )
        print(
            f"{spec['slug']}: panel={panel.get('hit_rate')} june={june.get('hit_rate')} "
            f"june_hits={june.get('hits')}/{june.get('n')}"
        )

    best_june = max(
        (r for r in results if r.get("june_tail", {}).get("hit_rate") is not None),
        key=lambda x: (float(x["june_tail"]["hit_rate"]), float(x["panel_30d"].get("hit_rate") or 0)),
        default=None,
    )
    best_panel = max(
        (r for r in results if r.get("panel_30d", {}).get("hit_rate") is not None),
        key=lambda x: float(x["panel_30d"]["hit_rate"]),
        default=None,
    )
    baseline = next((r for r in results if r["slug"] == "baseline_lb5"), {})

    out_doc = {
        "schema": "kospi_price_vol_dampen_lookback_ablation_v1",
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "generated_at_utc": _utc_now(),
        "eval_dates_n": len(eval_dates),
        "excluded_bad_ohlcv_dates": sorted(exclude_bad),
        "neutral_bps": float(args.neutral_bps),
        "june_prefix": str(args.june_prefix),
        "variants": results,
        "best_by_june_hit_rate": best_june,
        "best_by_panel_30d_hit_rate": best_panel,
        "baseline_panel_hit_rate": baseline.get("panel_30d", {}).get("hit_rate"),
        "baseline_june_hit_rate": baseline.get("june_tail", {}).get("hit_rate"),
        "note": "Per-date KOSPI ensemble only; not dual-leg WF. June tail is primary target for crash-week misses.",
    }
    out_path = args.output if args.output.is_absolute() else ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path.resolve()}")

    if args.write_best_config and best_june:
        spec = next(s for s in VARIANTS if s["slug"] == best_june["slug"])
        cfg_out = _apply_spec(base_cfg, spec)
        cfg_out["note"] = f"[HYPO] best june from ablation {best_june['slug']} — not Track A promotion."
        wpath = args.write_best_config if args.write_best_config.is_absolute() else ROOT / args.write_best_config
        wpath.parent.mkdir(parents=True, exist_ok=True)
        wpath.write_text(json.dumps(cfg_out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"WROTE best-june config: {wpath.resolve()}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
