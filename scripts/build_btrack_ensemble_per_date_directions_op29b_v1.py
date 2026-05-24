#!/usr/bin/env python3
"""Build per-eval_date ensemble directions with O-P29b dynamic lens + news as-of injection.

Output default: reports/op29b_shadow/btrack_ensemble_per_date_directions_180d_op29b_v1.json
research_only — does not overwrite prophecy headline SSOT.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.btrack_ensemble_per_date_core_v1 import (
    _causal_price_score_rows,
    _load_btc_closes,
    _load_gen_module,
    _pick_builder,
)
from scripts.btrack_op29b_dynamic_lens_v1 import patch_bundle_for_eval_date

DEFAULT_BUNDLE = ROOT / "docs/final/artifacts/btrack_llm_input_bundle_latest.json"
DEFAULT_CFG = ROOT / "docs/final/artifacts/btrack_lens_ensemble_v1.json"
DEFAULT_BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
DEFAULT_KOSPI = ROOT / "research/market_data/kospi_daily_external_yf.csv"
DEFAULT_OUT = ROOT / "reports/op29b_shadow/btrack_ensemble_per_date_directions_180d_op29b_v1.json"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _eval_dates_recent(n: int, kospi: Path, btc: Path) -> list[str]:
    from scripts.build_btrack_ensemble_per_date_directions_v1 import (
        _eval_dates_from_recent_trading_days,
    )

    return _eval_dates_from_recent_trading_days(kospi_csv=kospi, btc_csv=btc, n=n)


def compute_op29b_per_date_rows(
    *,
    base_bundle: dict,
    ensemble_cfg: dict,
    eval_dates: list[str],
    btc_csv: Path,
    instrument: str = "btc",
    ensemble_mode: str = "v2_confidence_fusion",
) -> list[dict]:
    gen = _load_gen_module()
    rules = ensemble_cfg.get("rules") if isinstance(ensemble_cfg.get("rules"), dict) else {}
    rules = dict(rules)
    rules["ensemble_mode"] = ensemble_mode
    ensemble_cfg = dict(ensemble_cfg)
    ensemble_cfg["rules"] = rules
    lookback = int(rules.get("price_lookback_days", 5))
    builder, mode_label = _pick_builder(gen, ensemble_mode)

    from scripts.btrack_causal_ohlc_features_v1 import (
        load_btc_ohlc_by_date,
        overnight_return_at_eval,
        prior_range_position_at_eval,
        realized_vol_5d_at_eval,
        vol_regime_high,
    )

    ohlc = load_btc_ohlc_by_date(btc_csv)
    closes = {d: v["close"] for d, v in ohlc.items()}
    try:
        vol_thresh = float(rules.get("vol_high_realized_5d", 0.03))
    except (TypeError, ValueError):
        vol_thresh = 0.03

    out: list[dict] = []
    previous_doc: dict | None = None
    for ed in sorted({str(d)[:10] for d in eval_dates if d}):
        bundle_ed = patch_bundle_for_eval_date(base_bundle, ed)
        price_rows = _causal_price_score_rows(closes, ed, lookback=lookback, instrument=instrument)
        score_doc: dict = {"rows": price_rows}
        ovn = overnight_return_at_eval(ohlc, ed)
        if ovn is not None:
            score_doc["overnight_return"] = ovn
        prp = prior_range_position_at_eval(ohlc, ed)
        if prp is not None:
            score_doc["prior_range_position"] = prp
        rv = realized_vol_5d_at_eval(closes, ed)
        if rv is not None:
            score_doc["realized_vol_5d"] = rv
            score_doc["vol_regime_high"] = vol_regime_high(rv, threshold=vol_thresh)

        doc = builder(
            bundle_ed,
            score_doc=score_doc,
            ensemble_cfg=ensemble_cfg,
            previous_doc=previous_doc,
        )
        previous_doc = doc
        pred = doc.get("prediction") if isinstance(doc.get("prediction"), dict) else {}
        meta = doc.get("runtime_meta") if isinstance(doc.get("runtime_meta"), dict) else {}
        direction = str(pred.get("direction") or "neutral").strip().lower()
        if direction not in ("bull", "bear", "neutral"):
            direction = "neutral"
        gate = (
            meta.get("low_confidence_direction_gate")
            if isinstance(meta.get("low_confidence_direction_gate"), dict)
            else {}
        )
        out.append(
            {
                "eval_date": ed,
                "instrument": instrument,
                "predicted_direction": direction,
                "confidence": pred.get("confidence"),
                "ensemble_mode": meta.get("ensemble_mode") or mode_label,
                "weighted_score": meta.get("weighted_score"),
                "preliminary_direction": meta.get("preliminary_direction"),
                "low_confidence_direction_gate": gate,
                "lens_values": meta.get("lens_values"),
                "weights_v2_effective": meta.get("weights_v2_effective"),
                "op29b_dynamic_lens": True,
                "conditional_bear_override_applied": bool(
                    (meta.get("conditional_bear_override") or {}).get("applied")
                ),
                "regime_price_dampen_applied": bool(
                    (meta.get("regime_conditional_price_dampen") or {}).get("applied")
                ),
                "overnight_return": meta.get("overnight_return"),
                "prior_range_position": meta.get("prior_range_position"),
                "realized_vol_5d": meta.get("realized_vol_5d"),
                "vol_regime_high": meta.get("vol_regime_high"),
                "price_lookback_rows": len(price_rows),
            }
        )
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bundle-json", type=Path, default=DEFAULT_BUNDLE)
    ap.add_argument("--ensemble-config", type=Path, default=DEFAULT_CFG)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI)
    ap.add_argument("--recent-trading-days", type=int, default=180)
    ap.add_argument("--ensemble-mode", default="v2_confidence_fusion")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    cfg = _load_json(args.ensemble_config) if args.ensemble_config.is_file() else {}
    rules = cfg.get("rules") if isinstance(cfg.get("rules"), dict) else {}
    rules = dict(rules)
    rules["ensemble_mode"] = str(args.ensemble_mode)
    cfg = dict(cfg)
    cfg["rules"] = rules

    bundle = _load_json(args.bundle_json)
    eval_dates = _eval_dates_recent(args.recent_trading_days, args.kospi_csv, args.btc_csv)
    rows = compute_op29b_per_date_rows(
        base_bundle=bundle,
        ensemble_cfg=cfg,
        eval_dates=eval_dates,
        btc_csv=args.btc_csv,
        ensemble_mode=str(args.ensemble_mode),
    )

    from datetime import datetime, timezone

    doc = {
        "schema": "btrack_ensemble_per_date_directions_v1",
        "version": "1.0.0",
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "ts_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ensemble_mode": str(args.ensemble_mode),
        "research_only": True,
        "op29b_dynamic_feed_v1": True,
        "inputs": {
            "bundle_json": str(args.bundle_json),
            "ensemble_config_json": str(args.ensemble_config),
            "btc_csv": str(args.btc_csv),
            "n_eval_dates": len(eval_dates),
        },
        "note": (
            "O-P29b: causal BTC price per eval_date; myeongni/sasang/news/macro patched per-day "
            "(calendar JSONL as-of + pre_news timestamp as-of). research_only."
        ),
        "rows": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()} rows={len(rows)} mode={args.ensemble_mode}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
