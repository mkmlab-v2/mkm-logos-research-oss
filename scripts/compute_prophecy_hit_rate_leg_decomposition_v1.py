"""Per-leg hit-rate decomposition for frozen-batch B-track score JSON (observability only)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCORE = ROOT / "docs/final/artifacts/btrack_prophecy_score_latest.json"
SCHEMA = "prophecy_hit_rate_leg_decomposition_v1"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _leg_rows(rows: list[dict[str, Any]], leg: str | None) -> list[dict[str, Any]]:
    if leg is None:
        return rows
    return [r for r in rows if str(r.get("instrument") or "").lower() == leg]


def _eval_leg(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.eval_prophecy_hit_rate_v1 import _hit_on_directional_calls_only, _hit_on_rows

    hits, n, rate = _hit_on_rows(rows)
    call_hits, n_calls, n_neutral_pred, call_rate = _hit_on_directional_calls_only(rows)
    bulls = bears = neuts = 0
    for r in rows:
        pd = str(r.get("predicted_direction") or "").strip().lower()
        ad = str(r.get("actual_direction") or "").strip().lower()
        if not pd or not ad:
            continue
        if pd not in ("bull", "bear", "neutral") or ad not in ("bull", "bear", "neutral"):
            continue
        if ad == "bull":
            bulls += 1
        elif ad == "bear":
            bears += 1
        else:
            neuts += 1
    n_dir = bulls + bears
    frozen = str(rows[0].get("predicted_direction") or "").strip().lower() if rows else None
    bear_base = bears / n_dir if n_dir else None
    bull_base = bulls / n_dir if n_dir else None
    frozen_base = None
    if frozen == "bear":
        frozen_base = bear_base
    elif frozen == "bull":
        frozen_base = bull_base
    return {
        "price_hits": hits,
        "n_evaluated": n,
        "price_directional_hit_rate": round(rate, 6) if rate is not None else None,
        "directional_call_hits": call_hits,
        "n_directional_calls": n_calls,
        "n_neutral_predictions": n_neutral_pred,
        "price_hit_rate_on_directional_calls": round(call_rate, 6) if call_rate is not None else None,
        "n_directional_actual": n_dir,
        "actual_bull": bulls,
        "actual_bear": bears,
        "actual_neutral": neuts,
        "baselines": {
            "coin_flip": 0.5,
            "always_bear_if_directional": round(bear_base, 6) if bear_base is not None else None,
            "always_bull_if_directional": round(bull_base, 6) if bull_base is not None else None,
            "frozen_single_direction": frozen,
            "equals_always_frozen_direction": (
                rate is not None
                and frozen_base is not None
                and abs(rate - frozen_base) < 1e-9
            ),
        },
    }


def _fmt_pct(rate: float | None) -> str:
    if rate is None:
        return "n/a"
    return f"{rate:.2%}"


def _resolve_headline_instrument(doc: dict[str, Any]) -> str:
    inputs = doc.get("inputs") if isinstance(doc.get("inputs"), dict) else {}
    declared = str(inputs.get("hypothesis_instrument_declared") or "").strip().lower()
    if declared in ("btc", "kospi"):
        return declared
    effective = str(inputs.get("effective_instrument") or "").strip().lower()
    if effective in ("btc", "kospi"):
        return effective
    return "pooled"


def compute_decomposition(score_path: Path) -> dict[str, Any]:
    doc = _load_json(score_path)
    rows = [r for r in doc.get("rows", []) if isinstance(r, dict)]
    meta = doc.get("meta") if isinstance(doc.get("meta"), dict) else {}
    dates = meta.get("batch_eval_dates") if isinstance(meta.get("batch_eval_dates"), list) else []
    legs: dict[str, Any] = {}
    for key, leg in (("pooled", None), ("btc", "btc"), ("kospi", "kospi")):
        sub = _leg_rows(rows, leg)
        if not sub:
            legs[key] = {"available": False}
            continue
        legs[key] = {"available": True, **_eval_leg(sub)}
    return {
        "schema": SCHEMA,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "zeroing_note": (
            "price hit over score rows; frozen hypothesis applies same predicted_direction to each "
            "eval_date (see meta.frozen_prediction_note). Not walk-forward per-date skill."
        ),
        "inputs": {
            "score_json": str(score_path.relative_to(ROOT)) if score_path.is_relative_to(ROOT) else str(score_path),
            "eval_date": doc.get("eval_date"),
            "neutral_bps": doc.get("neutral_bps"),
            "force_dual_leg_panel": (doc.get("inputs") or {}).get("force_dual_leg_panel"),
            "recent_trading_days": (doc.get("inputs") or {}).get("recent_trading_days"),
        },
        "window": {
            "batch_eval_dates_first": dates[0] if dates else None,
            "batch_eval_dates_last": dates[-1] if dates else None,
            "n_dates": len(dates),
        },
        "legs": legs,
        "headline_instrument": _resolve_headline_instrument(doc),
        "scoring_mode": (
            "per_date_direction_overrides"
            if (doc.get("inputs") or {}).get("per_date_direction_json")
            else "frozen_single_direction_batch"
        ),
    }


def format_alert_lines(
    decomp: dict[str, Any],
    min_headline_rate: float,
    min_promotion_rate: float | None = None,
    min_directional_rate: float | None = None,
    min_directional_calls: int | None = None,
) -> list[str]:
    promo = min_promotion_rate if min_promotion_rate is not None else min_headline_rate
    lines = [
        "[MKM-BTRACK-DAILY-EVAL-OBS]",
        f"- ALERT_1 headline floor: {min_headline_rate:.0%} | promotion band: {promo:.0%} (not live trading)",
        "* [HYPO] observability only — no Track A / auto-promote from this block.",
    ]
    headline_key = str(decomp.get("headline_instrument") or "pooled")
    headline = decomp.get("legs", {}).get(headline_key) or {}
    if headline.get("available"):
        rate = headline.get("price_directional_hit_rate")
        n = headline.get("n_evaluated")
        if rate is not None and rate < min_headline_rate:
            status = "below_headline_floor"
        elif rate is not None and rate < promo:
            status = "at_or_above_floor_below_promotion_band"
        else:
            status = "at_or_above_promotion_band"
        label = headline_key.upper() if headline_key != "pooled" else "Pooled dual"
        lines.append(f"- Headline ({label}, ALERT_1 all rows): {rate:.2%} (n={n}) -> {status}")
        call_rate = headline.get("price_hit_rate_on_directional_calls")
        n_calls = headline.get("n_directional_calls")
        n_neutral = headline.get("n_neutral_predictions")
        if n_calls is not None and int(n_calls) > 0:
            lines.append(
                f"- Headline ({label}, directional calls only): {_fmt_pct(call_rate)} "
                f"(hits={headline.get('directional_call_hits')}/{n_calls}, "
                f"neutral_preds={n_neutral})"
            )
        if min_directional_rate is not None and min_directional_calls is not None:
            if n_calls is None or int(n_calls) < int(min_directional_calls):
                status_1b = "insufficient_sample"
            elif call_rate is None:
                status_1b = "no_directional_rate"
            elif float(call_rate) < float(min_directional_rate):
                status_1b = "below_directional_floor"
            else:
                status_1b = "pass"
            lines.append(
                f"- ALERT_1b ({label}, directional skill): {_fmt_pct(call_rate)} "
                f"(hits={headline.get('directional_call_hits')}/{n_calls}, "
                f"min_calls={min_directional_calls}, floor={min_directional_rate:.0%}) "
                f"-> {status_1b} | informational only (no webhook / no exit)"
            )
    pooled = decomp.get("legs", {}).get("pooled") or {}
    if pooled.get("available") and headline_key != "pooled":
        rate = pooled.get("price_directional_hit_rate")
        n = pooled.get("n_evaluated")
        lines.append(f"- Pooled dual (observation only): {rate:.2%} (n={n})")
    for label, key in (("BTC leg", "btc"), ("KOSPI leg", "kospi")):
        leg = decomp.get("legs", {}).get(key) or {}
        if not leg.get("available"):
            lines.append(f"  +- {label}: unavailable")
            continue
        rate = leg.get("price_directional_hit_rate")
        n = leg.get("n_evaluated")
        lines.append(f"  +- {label}: {rate:.2%} (n={n})")
    if pooled.get("available"):
        bl = pooled.get("baselines") or {}
        lines.append(
            f"- Baselines (directional actuals): coin_flip=50% | "
            f"always_bear={bl.get('always_bear_if_directional')} | "
            f"always_bull={bl.get('always_bull_if_directional')}"
        )
        if bl.get("equals_always_frozen_direction"):
            lines.append(
                f"- Frozen direction={bl.get('frozen_single_direction')}: "
                "pooled hit equals 'always that direction' on this window (not WF skill)."
            )
    btc = decomp.get("legs", {}).get("btc") or {}
    if btc.get("available"):
        bbl = btc.get("baselines") or {}
        if bbl.get("equals_always_frozen_direction"):
            lines.append(
                "- BTC leg: hit equals 'always bear' on this window (frozen batch; not WF skill)."
            )
    kospi = decomp.get("legs", {}).get("kospi") or {}
    if kospi.get("available"):
        kbl = kospi.get("baselines") or {}
        if kbl.get("equals_always_frozen_direction"):
            lines.append(
                "- KOSPI leg: hit equals 'always bear' on this window (frozen batch; not WF skill)."
            )
    mode = decomp.get("scoring_mode")
    if mode == "per_date_direction_overrides":
        lines.append("- Scoring: per_date_direction_overrides (ensemble v1 causal rows).")
    else:
        lines.append("- Scoring: frozen_single_direction_batch (same pred each eval_date).")
    return lines


def main() -> int:
    ap = argparse.ArgumentParser(description="B-track per-leg hit decomposition (observability).")
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--output", type=Path, default=None)
    ap.add_argument("--stdout-only", action="store_true")
    ap.add_argument("--min-headline-rate", type=float, default=0.50, help="Headline skill floor for alert lines.")
    ap.add_argument(
        "--min-promotion-rate",
        type=float,
        default=0.60,
        help="Promotion band threshold for alert lines (informational).",
    )
    ap.add_argument(
        "--min-hit-rate",
        type=float,
        default=None,
        help="Legacy alias for --min-promotion-rate.",
    )
    ap.add_argument(
        "--min-directional-rate",
        type=float,
        default=0.50,
        help="ALERT_1b floor on price_hit_rate_on_directional_calls (informational).",
    )
    ap.add_argument(
        "--min-directional-calls",
        type=int,
        default=10,
        help="ALERT_1b minimum n_directional_calls before skill floor applies.",
    )
    ap.add_argument("--format-alert", action="store_true", help="Append human alert block to stdout.")
    args = ap.parse_args()
    score_path = args.score_json if args.score_json.is_absolute() else ROOT / args.score_json
    if not score_path.is_file():
        print(f"Missing score JSON: {score_path}", file=sys.stderr)
        return 2
    decomp = compute_decomposition(score_path)
    promo_rate = args.min_promotion_rate
    if args.min_hit_rate is not None:
        promo_rate = args.min_hit_rate
    if args.format_alert:
        decomp["alert_lines"] = format_alert_lines(
            decomp,
            args.min_headline_rate,
            min_promotion_rate=promo_rate,
            min_directional_rate=args.min_directional_rate,
            min_directional_calls=args.min_directional_calls,
        )
    text = json.dumps(decomp, indent=2, ensure_ascii=False)
    if args.stdout_only:
        print(text)
    if args.output:
        out = args.output if args.output.is_absolute() else ROOT / args.output
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8")
        print(f"WROTE: {out}")
    elif not args.stdout_only:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
