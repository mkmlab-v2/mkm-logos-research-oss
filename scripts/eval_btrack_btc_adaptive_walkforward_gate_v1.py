#!/usr/bin/env python3
"""[HYPO] Adaptive walk-forward gate — fit policy params on train fold, evaluate on test only.

research_only; does not modify operational score.
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_btrack_btc_direction_error_spike_v1 import _hit_rate, _load
from scripts.eval_btrack_btc_rolling_promotion_gate_v1 import (
    _apply_cal,
    _apply_type_a,
    _build_180d_rows,
    _rolling_folds,
)

DEFAULT_SCORE = ROOT / "reports/btrack_prophecy_score_dual_leg_180d_rebuild_v1_latest.json"
DEFAULT_DUAL180 = ROOT / "reports/btrack_ensemble_per_date_directions_dual_180d_rebuild_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/btrack_btc_adaptive_walkforward_gate_v1_latest.json"
SCHEMA = "btrack_btc_adaptive_walkforward_gate_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _delta(rows: list[dict[str, Any]], cf_rows: list[dict[str, Any]]) -> float | None:
    base = _hit_rate(rows)
    cf = _hit_rate(cf_rows)
    if base["price_directional_hit_rate"] is None or cf["price_directional_hit_rate"] is None:
        return None
    return round(cf["price_directional_hit_rate"] - base["price_directional_hit_rate"], 6)


def _best_type_a_on_train(train: list[dict[str, Any]]) -> tuple[dict[str, Any], float | None]:
    score_grid = [0.05, 0.08, 0.12, 0.15]
    kospi_modes = ["bull_only", "not_bear"]
    best_params: dict[str, Any] | None = None
    best_delta = -1e9
    best_changes = 10**9
    for score_lt, kospi_mode in itertools.product(score_grid, kospi_modes):
        cf = _apply_type_a(train, score_lt=score_lt, kospi_mode=kospi_mode)
        d = _delta(train, cf)
        changes = sum(1 for a, b in zip(train, cf) if a.get("predicted_direction") != b.get("predicted_direction"))
        if d is None:
            continue
        if d > best_delta or (d == best_delta and changes < best_changes):
            best_delta = d
            best_changes = changes
            best_params = {"score_lt": score_lt, "kospi_mode": kospi_mode}
    if best_params is None:
        best_params = {"score_lt": 0.08, "kospi_mode": "bull_only"}
        best_delta = _delta(train, _apply_type_a(train, **best_params))
    return best_params, best_delta


def _best_cal_on_train(train: list[dict[str, Any]]) -> tuple[dict[str, Any], float | None]:
    alphas = [0.8, 1.0, 1.2]
    betas = [-0.08, -0.05, -0.03, 0.0]
    deadzones = [0.02, 0.03, 0.04]
    best_params: dict[str, Any] | None = None
    best_delta = -1e9
    best_changes = 10**9
    for alpha, beta, deadzone in itertools.product(alphas, betas, deadzones):
        cf = _apply_cal(train, alpha=alpha, beta=beta, deadzone=deadzone)
        d = _delta(train, cf)
        changes = sum(1 for a, b in zip(train, cf) if a.get("predicted_direction") != b.get("predicted_direction"))
        if d is None:
            continue
        if d > best_delta or (d == best_delta and changes < best_changes):
            best_delta = d
            best_changes = changes
            best_params = {"alpha": alpha, "beta": beta, "deadzone": deadzone}
    if best_params is None:
        best_params = {"alpha": 0.8, "beta": -0.08, "deadzone": 0.02}
        best_delta = _delta(train, _apply_cal(train, **best_params))
    return best_params, best_delta


def _eval_family(
    rows: list[dict[str, Any]],
    folds: list[tuple[list[str], list[str]]],
    family: str,
) -> dict[str, Any]:
    fold_rows: list[dict[str, Any]] = []
    for train_dates, test_dates in folds:
        tr = [r for r in rows if str(r["eval_date"]) in train_dates]
        te = [r for r in rows if str(r["eval_date"]) in test_dates]
        if len(tr) < 10 or len(te) < 5:
            continue
        if family == "type_a":
            params, train_delta = _best_type_a_on_train(tr)
            cf_te = _apply_type_a(te, score_lt=params["score_lt"], kospi_mode=params["kospi_mode"])
        else:
            params, train_delta = _best_cal_on_train(tr)
            cf_te = _apply_cal(te, alpha=params["alpha"], beta=params["beta"], deadzone=params["deadzone"])
        test_delta = _delta(te, cf_te)
        base_te = _hit_rate(te)
        cf_hit = _hit_rate(cf_te)
        fold_rows.append(
            {
                "train_n": len(tr),
                "test_n": len(te),
                "selected_params": params,
                "train_delta_in_sample": train_delta,
                "test_delta_oos": test_delta,
                "test_baseline_hit_rate": base_te["price_directional_hit_rate"],
                "test_counterfactual_hit_rate": cf_hit["price_directional_hit_rate"],
            }
        )
    mean_test = (
        round(sum(f["test_delta_oos"] or 0 for f in fold_rows) / len(fold_rows), 6) if fold_rows else None
    )
    pos = sum(1 for f in fold_rows if (f["test_delta_oos"] or 0) > 0)
    return {
        "family": family,
        "folds": fold_rows,
        "mean_test_delta_oos": mean_test,
        "positive_test_folds": pos,
        "total_folds": len(fold_rows),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--dual-180-json", type=Path, default=DEFAULT_DUAL180)
    ap.add_argument("--n-folds", type=int, default=5)
    ap.add_argument("--min-positive-folds", type=int, default=4)
    ap.add_argument("--min-mean-oos-delta", type=float, default=0.0)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    score_doc = _load(args.score_json) if args.score_json.is_file() else {}
    dual_doc = _load(args.dual_180_json) if args.dual_180_json.is_file() else {}
    rows = _build_180d_rows(score_doc, dual_doc)
    if len(rows) < 30:
        raise SystemExit(f"insufficient 180d rows: {len(rows)}")

    dates = sorted({str(r["eval_date"])[:10] for r in rows})
    folds = _rolling_folds(dates, args.n_folds)

    families = [_eval_family(rows, folds, "type_a"), _eval_family(rows, folds, "calibration")]
    best = max(families, key=lambda x: x.get("mean_test_delta_oos") or -1e9) if families else None

    promote = False
    reasons: list[str] = []
    if best and best.get("mean_test_delta_oos") is not None:
        mean_ok = best["mean_test_delta_oos"] > args.min_mean_oos_delta
        folds_ok = best.get("positive_test_folds", 0) >= args.min_positive_folds
        reasons.append("mean_test_delta_oos_positive" if mean_ok else "mean_test_delta_oos_not_positive")
        reasons.append("enough_positive_folds" if folds_ok else "insufficient_positive_folds")
        promote = mean_ok and folds_ok
    else:
        reasons.append("no_family_results")

    out = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "method": "train_fold_grid_search_then_test_oos",
        "inputs": {"score_json": str(args.score_json), "dual_180_json": str(args.dual_180_json)},
        "n_dates_180d": len(dates),
        "n_folds": args.n_folds,
        "gate_thresholds": {
            "min_mean_oos_delta": args.min_mean_oos_delta,
            "min_positive_folds": args.min_positive_folds,
        },
        "families": families,
        "best_family": best,
        "promotion_recommendation": "candidate_for_human_signoff" if promote else "hold_research_only",
        "would_change_active": False,
        "combined_all_passed": False,
        "reasons": reasons,
        "notes_ko": [
            "train fold에서만 grid search; test는 고정 파라미터 OOS.",
            "Track A·실매매 자동 승격 금지.",
        ],
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json.resolve()}")
    bf = best or {}
    print(
        f"promotion={out['promotion_recommendation']} "
        f"best={bf.get('family')} mean_oos={bf.get('mean_test_delta_oos')} "
        f"pos_folds={bf.get('positive_test_folds')}/{bf.get('total_folds')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
