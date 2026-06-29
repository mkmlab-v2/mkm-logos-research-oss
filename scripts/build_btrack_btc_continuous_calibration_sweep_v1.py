#!/usr/bin/env python3
"""[HYPO] Continuous calibration sweep for BTC price-lens score.

Transforms raw score via affine + bias and maps to direction with deadzone.
Used as research-only alternative to hard rule switches.
"""
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

from scripts.build_btrack_btc_direction_error_spike_v1 import _enrich_btc_rows, _hit_rate, _load

DEFAULT_SCORE = ROOT / "docs/final/artifacts/btrack_prophecy_score_latest.json"
DEFAULT_DUAL = ROOT / "reports/btrack_ensemble_per_date_directions_dual_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/btrack_btc_continuous_calibration_sweep_v1_latest.json"
SCHEMA = "btrack_btc_continuous_calibration_sweep_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _dir_from_score(score: float, deadzone: float) -> str:
    if score > deadzone:
        return "bull"
    if score < -deadzone:
        return "bear"
    return "neutral"


def _apply(rows: list[dict[str, Any]], *, alpha: float, beta: float, deadzone: float) -> tuple[list[dict[str, Any]], int, int]:
    out: list[dict[str, Any]] = []
    n_changed = 0
    type_a_fix = 0
    for r in rows:
        pred = str(r.get("predicted_direction") or "").lower()
        actual = str(r.get("actual_direction") or "").lower()
        sc = r.get("btc_price_lens_score")
        adj = pred
        if sc is not None:
            cal = alpha * float(sc) + beta
            adj = _dir_from_score(cal, deadzone)
        x = dict(r)
        x["predicted_direction"] = adj
        out.append(x)
        if adj != pred:
            n_changed += 1
        if pred == "bull" and actual == "bear" and adj == "bear":
            type_a_fix += 1
    return out, n_changed, type_a_fix


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--dual-json", type=Path, default=DEFAULT_DUAL)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    rows = _enrich_btc_rows(_load(args.score_json), _load(args.dual_json))
    baseline = _hit_rate(rows)

    type_a_days = {
        str(r.get("eval_date"))[:10]
        for r in rows
        if str(r.get("predicted_direction") or "").lower() == "bull"
        and str(r.get("actual_direction") or "").lower() == "bear"
    }

    alphas = [0.8, 1.0, 1.2]
    betas = [-0.08, -0.05, -0.03, 0.0]
    deadzones = [0.02, 0.03, 0.04]

    candidates: list[dict[str, Any]] = []
    for a in alphas:
        for b in betas:
            for dz in deadzones:
                cf_rows, n_changed, type_a_fix = _apply(rows, alpha=a, beta=b, deadzone=dz)
                cf = _hit_rate(cf_rows)
                delta = None
                if baseline["price_directional_hit_rate"] is not None and cf["price_directional_hit_rate"] is not None:
                    delta = round(cf["price_directional_hit_rate"] - baseline["price_directional_hit_rate"], 6)
                candidates.append(
                    {
                        "policy_id": f"cal_a{a}_b{b}_dz{dz}",
                        "alpha": a,
                        "beta": b,
                        "deadzone": dz,
                        "counterfactual_btc": cf,
                        "delta_hit_rate": delta,
                        "n_predictions_changed": n_changed,
                        "type_a_fix_count": type_a_fix,
                    }
                )

    candidates = sorted(
        candidates,
        key=lambda x: (
            -1e9 if x.get("delta_hit_rate") is None else -float(x["delta_hit_rate"]),
            -int(x.get("type_a_fix_count") or 0),
            int(x.get("n_predictions_changed") or 0),
        ),
    )

    best = candidates[0] if candidates else None
    out = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "inputs": {"score_json": str(args.score_json), "dual_json": str(args.dual_json)},
        "baseline_btc": baseline,
        "n_type_a_days": len(type_a_days),
        "type_a_dates": sorted(type_a_days),
        "grid": {"alpha": alphas, "beta": betas, "deadzone": deadzones},
        "best_candidate": best,
        "top_candidates": candidates[:10],
        "promotion_recommendation": "hold_research_only",
        "notes_ko": [
            "연속 보정: calibrated_score = alpha*score + beta.",
            "direction = sign(calibrated_score, deadzone).",
            "delta>0이어도 holdout replay 전 operational 반영 금지.",
        ],
    }
    if best and isinstance(best.get("delta_hit_rate"), float) and best["delta_hit_rate"] > 0:
        out["promotion_recommendation"] = "candidate_for_holdout_replay_not_operational"

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json.resolve()}")
    if best:
        print("best", best["policy_id"], "delta", best.get("delta_hit_rate"), "changed", best.get("n_predictions_changed"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
