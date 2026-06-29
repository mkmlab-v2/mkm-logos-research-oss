#!/usr/bin/env python3
"""[HYPO] Holdout replay for best continuous calibration candidate."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.btrack_wrong_dir_holdout_core_v1 import HOLDOUT_7_DEFAULT
from scripts.build_btrack_btc_direction_error_spike_v1 import _enrich_btc_rows, _hit_rate, _load

DEFAULT_SCORE = ROOT / "docs/final/artifacts/btrack_prophecy_score_latest.json"
DEFAULT_DUAL = ROOT / "reports/btrack_ensemble_per_date_directions_dual_v1_latest.json"
DEFAULT_DUAL180 = ROOT / "reports/btrack_prophecy_score_dual_leg_180d_rebuild_v1_latest.json"
DEFAULT_DUAL180_PERDATE = ROOT / "reports/btrack_ensemble_per_date_directions_dual_180d_rebuild_v1_latest.json"
DEFAULT_SWEEP = ROOT / "reports/btrack_btc_continuous_calibration_sweep_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/btrack_btc_continuous_calibration_holdout_replay_v1_latest.json"
SCHEMA = "btrack_btc_continuous_calibration_holdout_replay_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _dir(score: float, deadzone: float) -> str:
    if score > deadzone:
        return "bull"
    if score < -deadzone:
        return "bear"
    return "neutral"


def _apply(rows: list[dict[str, Any]], *, alpha: float, beta: float, deadzone: float) -> tuple[list[dict[str, Any]], int]:
    out = []
    changed = 0
    for r in rows:
        pred = str(r.get("predicted_direction") or "").lower()
        adj = pred
        sc = r.get("btc_price_lens_score")
        if sc is not None:
            adj = _dir(alpha * float(sc) + beta, deadzone)
        x = dict(r)
        x["predicted_direction"] = adj
        out.append(x)
        if adj != pred:
            changed += 1
    return out, changed


def _eval(rows: list[dict[str, Any]], *, cohort_id: str, alpha: float, beta: float, deadzone: float) -> dict[str, Any]:
    base = _hit_rate(rows)
    cf_rows, changed = _apply(rows, alpha=alpha, beta=beta, deadzone=deadzone)
    cf = _hit_rate(cf_rows)
    delta = None
    if base["price_directional_hit_rate"] is not None and cf["price_directional_hit_rate"] is not None:
        delta = round(cf["price_directional_hit_rate"] - base["price_directional_hit_rate"], 6)
    return {
        "cohort_id": cohort_id,
        "n_days": len(rows),
        "eval_dates": [str(r.get("eval_date"))[:10] for r in rows],
        "baseline_btc": base,
        "counterfactual_btc": cf,
        "delta_hit_rate": delta,
        "n_predictions_changed": changed,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--dual-json", type=Path, default=DEFAULT_DUAL)
    ap.add_argument("--dual-180-score-json", type=Path, default=DEFAULT_DUAL180)
    ap.add_argument("--dual-180-perdate-json", type=Path, default=DEFAULT_DUAL180_PERDATE)
    ap.add_argument("--sweep-json", type=Path, default=DEFAULT_SWEEP)
    ap.add_argument("--alpha", type=float, default=None)
    ap.add_argument("--beta", type=float, default=None)
    ap.add_argument("--deadzone", type=float, default=None)
    ap.add_argument("--holdout-tail-n", type=int, default=5)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    sweep = _load(args.sweep_json) if args.sweep_json.is_file() else {}
    best = sweep.get("best_candidate") if isinstance(sweep.get("best_candidate"), dict) else {}
    alpha = float(args.alpha if args.alpha is not None else best.get("alpha", 1.0))
    beta = float(args.beta if args.beta is not None else best.get("beta", 0.0))
    dz = float(args.deadzone if args.deadzone is not None else best.get("deadzone", 0.03))

    score_doc = _load(args.score_json)
    dual_doc = _load(args.dual_json)
    btc = _enrich_btc_rows(score_doc, dual_doc)

    h7 = [str(d)[:10] for d in HOLDOUT_7_DEFAULT]
    h7set = set(h7)

    cohorts = []
    if btc:
        cohorts.append(_eval(btc, cohort_id="operational_15d_full", alpha=alpha, beta=beta, deadzone=dz))
        n = max(1, min(args.holdout_tail_n, len(btc)))
        tr, tail = btc[:-n], btc[-n:]
        if tr:
            cohorts.append(_eval(tr, cohort_id=f"operational_15d_train_first_{len(tr)}", alpha=alpha, beta=beta, deadzone=dz))
        cohorts.append(_eval(tail, cohort_id=f"operational_15d_temporal_holdout_tail_{n}", alpha=alpha, beta=beta, deadzone=dz))

    if args.dual_180_score_json.is_file():
        d180 = _load(args.dual_180_score_json)
        d180_dual = _load(args.dual_180_perdate_json) if args.dual_180_perdate_json.is_file() else d180
        btc180 = _enrich_btc_rows(d180, d180_dual)
        h = [r for r in btc180 if str(r.get("eval_date"))[:10] in h7set]
        non = [r for r in btc180 if str(r.get("eval_date"))[:10] not in h7set]
        if h:
            cohorts.append(_eval(h, cohort_id="canonical_holdout7_dual_180d", alpha=alpha, beta=beta, deadzone=dz))
        if non:
            cohorts.append(_eval(non, cohort_id="dual_180d_excluding_holdout7", alpha=alpha, beta=beta, deadzone=dz))

    tail = next((c for c in cohorts if str(c.get("cohort_id", "")).startswith("operational_15d_temporal_holdout_tail")), None)
    h = next((c for c in cohorts if c.get("cohort_id") == "canonical_holdout7_dual_180d"), None)
    full = next((c for c in cohorts if c.get("cohort_id") == "operational_15d_full"), None)
    temporal_delta = (tail or {}).get("delta_hit_rate")
    holdout7_delta = (h or {}).get("delta_hit_rate")
    full_dates = set((full or {}).get("eval_dates") or [])
    tail_dates = set((tail or {}).get("eval_dates") or [])
    tail_changed = int((tail or {}).get("n_predictions_changed", 0) or 0)
    full_changed = int((full or {}).get("n_predictions_changed", 0) or 0)
    tail_delta_inflated_by_single_overlap = bool(
        tail_changed == 1
        and full_changed >= 1
        and tail_dates
        and tail_dates <= full_dates
        and (tail or {}).get("n_days", 0) <= 7
    )

    promo = "hold_research_only"
    if (
        isinstance(temporal_delta, float)
        and temporal_delta > 0
        and (tail or {}).get("n_predictions_changed", 0) > 0
        and not tail_delta_inflated_by_single_overlap
    ):
        promo = "candidate_for_extended_holdout_not_operational"
    if isinstance(holdout7_delta, float) and holdout7_delta <= 0:
        promo = "hold_research_only"

    out = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "policy_under_test": "continuous_calibration",
        "params": {"alpha": alpha, "beta": beta, "deadzone": dz, "holdout_tail_n": args.holdout_tail_n},
        "holdout7_dates": h7,
        "cohorts": cohorts,
        "summary": {
            "temporal_holdout_tail_delta": temporal_delta,
            "canonical_holdout7_delta": holdout7_delta,
            "in_sample_15d_delta": next((c.get("delta_hit_rate") for c in cohorts if c.get("cohort_id")=='operational_15d_full'), None),
            "tail_delta_inflated_by_single_overlap": tail_delta_inflated_by_single_overlap,
        },
        "promotion_recommendation": promo,
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(f"WROTE: {args.out_json.resolve()}")
    print(f"promotion={promo} temporal_delta={temporal_delta} holdout7_delta={holdout7_delta}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
