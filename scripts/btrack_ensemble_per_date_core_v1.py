#!/usr/bin/env python3
"""Causal per-eval_date ensemble directions (v1 / v2) for B-track walk-forward alignment.

Macro/news/three-lens scores are taken from the current bundle snapshot (static across dates).
Price lens uses BTC OHLCV returns **strictly before** each eval_date (no lookahead).
research_only — not live routing.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _load_gen_module() -> Any:
    path = ROOT / "scripts" / "generate_btrack_hypothesis_prophecy_v1.py"
    spec = importlib.util.spec_from_file_location("generate_btrack_hypothesis_prophecy_v1", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_btc_closes(csv_path: Path) -> dict[str, float]:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.logos_shadow_eval_lib import load_kospi_yf_rows

    rows = load_kospi_yf_rows(csv_path)
    out: dict[str, float] = {}
    for r in rows:
        try:
            out[str(r["date"])[:10]] = float(r["close"])
        except (TypeError, ValueError, KeyError):
            continue
    return out


def _causal_price_score_rows(
    closes: dict[str, float],
    eval_date: str,
    *,
    lookback: int,
    instrument: str = "btc",
) -> list[dict[str, Any]]:
    """Build score-style rows with daily_return for dates strictly before eval_date."""
    dates = sorted(d for d in closes if d < eval_date)
    if len(dates) < 2:
        return []
    rows: list[dict[str, Any]] = []
    for i in range(1, len(dates)):
        d0, d1 = dates[i - 1], dates[i]
        c0, c1 = closes[d0], closes[d1]
        if c0 == 0:
            continue
        rows.append(
            {
                "instrument": instrument,
                "eval_date": d1,
                "daily_return": (c1 - c0) / c0,
            }
        )
    return rows[-max(1, int(lookback)) :]


_V2_ENSEMBLE_MODES = frozenset({"v2_confidence_fusion", "v2"})


def _pick_builder(gen: Any, ensemble_mode: str):
    mode = str(ensemble_mode or "v1").strip().lower()
    if mode in _V2_ENSEMBLE_MODES:
        builder = getattr(gen, "_build_ensemble_v2_from_bundle", None)
        if builder is None:
            raise RuntimeError(
                "ensemble_mode v2_confidence_fusion requested but "
                "generate_btrack_hypothesis_prophecy_v1._build_ensemble_v2_from_bundle is missing"
            )
        return builder, mode
    return gen._build_ensemble_from_bundle, "v1"


def compute_per_date_direction_rows(
    *,
    bundle: dict[str, Any],
    ensemble_cfg: dict[str, Any],
    eval_dates: list[str],
    btc_csv: Path,
    instrument: str = "btc",
) -> list[dict[str, Any]]:
    gen = _load_gen_module()
    rules = ensemble_cfg.get("rules") if isinstance(ensemble_cfg.get("rules"), dict) else {}
    lookback = int(rules.get("price_lookback_days", 5))
    ensemble_mode = str(rules.get("ensemble_mode") or "v1").strip().lower()
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
    out: list[dict[str, Any]] = []
    previous_doc: dict[str, Any] | None = None

    for ed in sorted({str(d)[:10] for d in eval_dates if d}):
        price_rows = _causal_price_score_rows(closes, ed, lookback=lookback, instrument=instrument)
        score_doc: dict[str, Any] = {"rows": price_rows}
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
            bundle,
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
                "weights": meta.get("weights"),
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


def build_per_date_direction_document(
    *,
    bundle_path: Path,
    ensemble_config_path: Path,
    eval_dates: list[str],
    btc_csv: Path,
    ensemble_mode_override: str | None = None,
) -> dict[str, Any]:
    bundle = _load_json(bundle_path)
    cfg = _load_json(ensemble_config_path) if ensemble_config_path.is_file() else {}
    rules = cfg.get("rules") if isinstance(cfg.get("rules"), dict) else {}
    if ensemble_mode_override:
        rules = dict(rules)
        rules["ensemble_mode"] = ensemble_mode_override
        cfg = dict(cfg)
        cfg["rules"] = rules
    rows = compute_per_date_direction_rows(
        bundle=bundle,
        ensemble_cfg=cfg,
        eval_dates=eval_dates,
        btc_csv=btc_csv,
    )
    from datetime import datetime, timezone

    mode = str(rules.get("ensemble_mode") or "v1")
    return {
        "schema": "btrack_ensemble_per_date_directions_v1",
        "version": "1.0.0",
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "ts_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ensemble_mode": mode,
        "research_only": True,
        "inputs": {
            "bundle_json": str(bundle_path),
            "ensemble_config_json": str(ensemble_config_path),
            "btc_csv": str(btc_csv),
            "n_eval_dates": len(eval_dates),
        },
        "note": (
            "Causal BTC price lens per eval_date; macro/news/lenses static from bundle snapshot. "
            "Use with build_btrack_prophecy_score_from_ohlcv.py --per-date-direction-json."
        ),
        "rows": rows,
    }
