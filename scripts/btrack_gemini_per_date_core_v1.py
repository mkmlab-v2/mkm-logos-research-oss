#!/usr/bin/env python3
"""[HYPO] Gemini per-eval_date directions — causal OHLCV loop, no batch cheating.

One independent Gemini call per eval_date. Lens artifacts are the same static bundle snapshot
as local ensemble per-date (see btrack_ensemble_per_date_core_v1 note); BTC price features
use only data strictly before eval_date.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.btrack_ensemble_per_date_core_v1 import _causal_price_score_rows
from scripts.generate_btrack_hypothesis_prophecy_v1 import SCHEMA_ID, run_gemini_hypothesis_prompt

DEFAULT_BUNDLE = ROOT / "docs/final/artifacts/btrack_llm_input_bundle_latest.json"
DEFAULT_BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
DEFAULT_KOSPI = ROOT / "research/market_data/kospi_daily_external_yf.csv"
DEFAULT_SCHEMA_PATH = ROOT / "docs/final/BTRACK_HYPOTHESIS_PROPHECY_V1.schema.json"
MAX_PANEL_DAYS_DEFAULT = 30
MAX_PANEL_DAYS_HARD_CAP = 180


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_eval_dates(
    *,
    recent_trading_days: int,
    kospi_csv: Path,
    btc_csv: Path,
    max_panel_days: int = MAX_PANEL_DAYS_DEFAULT,
) -> list[str]:
    cap = min(int(max_panel_days), MAX_PANEL_DAYS_HARD_CAP)
    if recent_trading_days < 1 or recent_trading_days > cap:
        raise ValueError(f"recent_trading_days must be 1..{cap}")
    from scripts.build_btrack_ensemble_per_date_directions_v1 import _eval_dates_from_recent_trading_days

    return _eval_dates_from_recent_trading_days(
        kospi_csv=kospi_csv, btc_csv=btc_csv, n=recent_trading_days
    )


def build_causal_context_for_eval_date(
    *,
    eval_date: str,
    btc_csv: Path,
    price_lookback_days: int = 5,
) -> dict[str, Any]:
    from scripts.btrack_causal_ohlc_features_v1 import (
        load_btc_ohlc_by_date,
        overnight_return_at_eval,
        prior_range_position_at_eval,
        realized_vol_5d_at_eval,
        vol_regime_high,
    )

    ohlc = load_btc_ohlc_by_date(btc_csv)
    closes = {d: v["close"] for d, v in ohlc.items()}
    ed = str(eval_date)[:10]
    price_rows = _causal_price_score_rows(
        closes, ed, lookback=price_lookback_days, instrument="btc"
    )
    ctx: dict[str, Any] = {
        "eval_date": ed,
        "instrument": "btc",
        "causal_price_daily_returns": price_rows,
        "price_lookback_rows": len(price_rows),
    }
    ovn = overnight_return_at_eval(ohlc, ed)
    if ovn is not None:
        ctx["overnight_return_at_eval_open"] = ovn
    prp = prior_range_position_at_eval(ohlc, ed)
    if prp is not None:
        ctx["prior_range_position_at_eval_open"] = prp
    rv = realized_vol_5d_at_eval(closes, ed)
    if rv is not None:
        ctx["realized_vol_5d_before_eval"] = rv
        ctx["vol_regime_high"] = vol_regime_high(rv, threshold=0.03)
    return ctx


def build_per_date_gemini_prompt(
    *,
    eval_date: str,
    bundle: dict[str, Any],
    causal_ctx: dict[str, Any],
    schema_path: Path = DEFAULT_SCHEMA_PATH,
) -> str:
    schema_text = schema_path.read_text(encoding="utf-8") if schema_path.is_file() else ""
    bundle_slice = {
        "schema": bundle.get("schema"),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "note": (
            "Static lens snapshot (same as local ensemble per-date). "
            "Do not use any market data on or after eval_date."
        ),
        "artifacts": bundle.get("artifacts"),
    }
    return f"""You are a B-Track [HYPO] hypothesis generator for ONE eval_date only.

TASK: Predict BTC direction for eval_date={eval_date} using information available before that date's close.
You must NOT use prices or returns on or after {eval_date}.

Output a single JSON object only (no markdown). Required schema: {SCHEMA_ID}
Required: hypothesis_tier=\"B\", boundary_ack=true, label contains \"[HYPO]\", ts_utc (ISO UTC),
prediction.instrument=\"btc\", prediction.horizon=\"1d\", prediction.direction in bull|bear|neutral|abstain.

Causal market context (strictly before eval_date):
{json.dumps(causal_ctx, ensure_ascii=False)[:40000]}

Lens / fusion bundle snapshot (static across dates — same convention as local ensemble):
{json.dumps(bundle_slice, ensure_ascii=False)[:80000]}

JSON Schema reference:
{schema_text[:60000]}
"""


def _direction_from_hypothesis(doc: dict[str, Any]) -> tuple[str, float | None]:
    pred = doc.get("prediction") if isinstance(doc.get("prediction"), dict) else {}
    direction = str(pred.get("direction") or "neutral").strip().lower()
    if direction not in ("bull", "bear", "neutral", "abstain"):
        direction = "neutral"
    conf_raw = pred.get("confidence")
    try:
        conf = float(conf_raw) if conf_raw is not None else None
    except (TypeError, ValueError):
        conf = None
    return direction, conf


def call_gemini_for_eval_date(
    *,
    eval_date: str,
    bundle: dict[str, Any],
    btc_csv: Path,
    model: str,
    timeout: int,
    max_retries: int,
    retry_backoff_sec: float,
    cache_path: Path | None,
    price_lookback_days: int,
) -> dict[str, Any]:
    ed = str(eval_date)[:10]
    if cache_path and cache_path.is_file():
        cached = _load_json(cache_path)
        if cached.get("eval_date") == ed and cached.get("hypothesis"):
            hyp = cached["hypothesis"]
            direction, conf = _direction_from_hypothesis(hyp)
            return {
                "eval_date": ed,
                "instrument": "btc",
                "predicted_direction": direction,
                "confidence": conf,
                "engine": "gemini_per_date_v1",
                "cache_hit": True,
                "hypothesis_path": str(cache_path),
            }

    causal_ctx = build_causal_context_for_eval_date(
        eval_date=ed, btc_csv=btc_csv, price_lookback_days=price_lookback_days
    )
    prompt = build_per_date_gemini_prompt(eval_date=ed, bundle=bundle, causal_ctx=causal_ctx)
    last_err: str | None = None
    hyp: dict[str, Any] | None = None
    for attempt in range(max(1, int(max_retries))):
        try:
            hyp = run_gemini_hypothesis_prompt(
                prompt=prompt, bundle=bundle, model=model, timeout=timeout
            )
            break
        except Exception as exc:  # noqa: BLE001 — retry with backoff for rate limits
            last_err = str(exc)
            if attempt + 1 >= max_retries:
                raise
            time.sleep(retry_backoff_sec * (2**attempt))
    if hyp is None:
        raise RuntimeError(last_err or "gemini call failed")

    if cache_path:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(
            json.dumps(
                {"eval_date": ed, "hypothesis": hyp, "cached_at_utc": _utc_now()},
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    direction, conf = _direction_from_hypothesis(hyp)
    return {
        "eval_date": ed,
        "instrument": "btc",
        "predicted_direction": direction,
        "confidence": conf,
        "engine": "gemini_per_date_v1",
        "cache_hit": False,
        "hypothesis_path": str(cache_path) if cache_path else None,
        "causal_ctx_summary": {
            "price_lookback_rows": causal_ctx.get("price_lookback_rows"),
            "overnight_return": causal_ctx.get("overnight_return_at_eval_open"),
        },
    }


def build_gemini_per_date_direction_document(
    *,
    bundle_path: Path,
    btc_csv: Path,
    kospi_csv: Path,
    recent_trading_days: int,
    model: str,
    timeout: int,
    sleep_between_calls_sec: float,
    max_retries: int,
    retry_backoff_sec: float,
    cache_dir: Path | None,
    price_lookback_days: int = 5,
    dry_run: bool = False,
    max_panel_days: int = MAX_PANEL_DAYS_DEFAULT,
) -> dict[str, Any]:
    cap = min(int(max_panel_days), MAX_PANEL_DAYS_HARD_CAP)
    if recent_trading_days > cap:
        raise ValueError(f"Cap: max {cap} trading days for Gemini per-date panel")
    eval_dates = resolve_eval_dates(
        recent_trading_days=recent_trading_days,
        kospi_csv=kospi_csv,
        btc_csv=btc_csv,
        max_panel_days=cap,
    )
    bundle = _load_json(bundle_path)
    plan = {
        "n_eval_dates": len(eval_dates),
        "eval_dates": eval_dates,
        "model": model,
        "sleep_between_calls_sec": sleep_between_calls_sec,
        "max_retries": max_retries,
    }
    if dry_run:
        return {
            "schema": "btrack_gemini_per_date_directions_v1",
            "version": "1.0.0",
            "hypothesis_tier": "B",
            "boundary_ack": True,
            "research_only": True,
            "dry_run": True,
            "ts_utc": _utc_now(),
            "plan": plan,
            "rows": [],
            "note": "Dry-run: no Gemini API calls.",
        }

    rows: list[dict[str, Any]] = []
    api_calls = 0
    for i, ed in enumerate(eval_dates):
        cache_path = (cache_dir / f"hypothesis_{ed}.json") if cache_dir else None
        if not (cache_path and cache_path.is_file()):
            if i > 0 and sleep_between_calls_sec > 0:
                time.sleep(float(sleep_between_calls_sec))
        row = call_gemini_for_eval_date(
            eval_date=ed,
            bundle=bundle,
            btc_csv=btc_csv,
            model=model,
            timeout=timeout,
            max_retries=max_retries,
            retry_backoff_sec=retry_backoff_sec,
            cache_path=cache_path,
            price_lookback_days=price_lookback_days,
        )
        if not row.get("cache_hit"):
            api_calls += 1
        rows.append(row)

    return {
        "schema": "btrack_gemini_per_date_directions_v1",
        "version": "1.0.0",
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "research_only": True,
        "ts_utc": _utc_now(),
        "engine": "gemini_per_date_v1",
        "inputs": {
            "bundle_json": str(bundle_path),
            "btc_csv": str(btc_csv),
            "kospi_csv": str(kospi_csv),
            "recent_trading_days": recent_trading_days,
            "model": model,
        },
        "plan": {**plan, "api_calls": api_calls},
        "note": (
            "One Gemini call per eval_date; causal BTC features before eval_date; "
            "lens static from bundle (matches ensemble per-date convention). "
            "Score via build_btrack_prophecy_score_from_ohlcv.py --per-date-direction-json."
        ),
        "rows": rows,
    }
