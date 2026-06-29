#!/usr/bin/env python3
"""[HYPO] Margin-vs-bull adaptive walk-forward + global 60/40 holdout gate.

Train objective: hit_rate - bull_baseline (margin). Optional param stability anchor.
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
DEFAULT_OUT = ROOT / "reports/btrack_btc_margin_walkforward_gate_v1_latest.json"
SCHEMA = "btrack_btc_margin_walkforward_gate_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _bull_baseline(rows: list[dict[str, Any]]) -> float:
    if not rows:
        return 0.0
    bulls = sum(1 for r in rows if str(r.get("actual_direction") or "").lower() == "bull")
    return bulls / len(rows)


def _delta(rows: list[dict[str, Any]], cf_rows: list[dict[str, Any]]) -> float | None:
    base = _hit_rate(rows)
    cf = _hit_rate(cf_rows)
    if base["price_directional_hit_rate"] is None or cf["price_directional_hit_rate"] is None:
        return None
    return round(cf["price_directional_hit_rate"] - base["price_directional_hit_rate"], 6)


def _margin(rows: list[dict[str, Any]], cf_rows: list[dict[str, Any]]) -> float | None:
    cf = _hit_rate(cf_rows)
    if cf["price_directional_hit_rate"] is None:
        return None
    return round(cf["price_directional_hit_rate"] - _bull_baseline(rows), 6)


def _score_train(
    train: list[dict[str, Any]],
    cf: list[dict[str, Any]],
    *,
    objective: str,
) -> float:
    if objective == "margin_vs_bull":
        m = _margin(train, cf)
        return m if m is not None else -1e9
    d = _delta(train, cf)
    return d if d is not None else -1e9


def _best_type_a(
    train: list[dict[str, Any]], *, objective: str, anchor_score_lt: float = 0.08
) -> tuple[dict[str, Any], float | None]:
    score_grid = [0.05, 0.08, 0.10, 0.12]
    kospi_modes = ["bull_only", "not_bear"]
    best_params: dict[str, Any] | None = None
    best_score = -1e9
    best_changes = 10**9
    for score_lt, kospi_mode in itertools.product(score_grid, kospi_modes):
        cf = _apply_type_a(train, score_lt=score_lt, kospi_mode=kospi_mode)
        sc = _score_train(train, cf, objective=objective)
        changes = sum(1 for a, b in zip(train, cf) if a.get("predicted_direction") != b.get("predicted_direction"))
        dist = abs(score_lt - anchor_score_lt)
        if sc > best_score or (sc == best_score and (changes < best_changes or (changes == best_changes and dist < abs((best_params or {}).get("score_lt", 0) - anchor_score_lt)))):
            best_score = sc
            best_changes = changes
            best_params = {"score_lt": score_lt, "kospi_mode": kospi_mode}
    assert best_params is not None
    train_delta = _delta(train, _apply_type_a(train, **best_params))
    return best_params, train_delta


def _best_cal(train: list[dict[str, Any]], *, objective: str) -> tuple[dict[str, Any], float | None]:
    alphas = [0.8, 1.0, 1.2]
    betas = [-0.08, -0.05, -0.03, 0.0]
    deadzones = [0.02, 0.03]
    best_params: dict[str, Any] | None = None
    best_score = -1e9
    best_changes = 10**9
    for alpha, beta, deadzone in itertools.product(alphas, betas, deadzones):
        cf = _apply_cal(train, alpha=alpha, beta=beta, deadzone=deadzone)
        sc = _score_train(train, cf, objective=objective)
        changes = sum(1 for a, b in zip(train, cf) if a.get("predicted_direction") != b.get("predicted_direction"))
        if sc > best_score or (sc == best_score and changes < best_changes):
            best_score = sc
            best_changes = changes
            best_params = {"alpha": alpha, "beta": beta, "deadzone": deadzone}
    assert best_params is not None
    train_delta = _delta(train, _apply_cal(train, **best_params))
    return best_params, train_delta


def _adaptive_family(
    rows: list[dict[str, Any]],
    folds: list[tuple[list[str], list[str]]],
    family: str,
    *,
    objective: str,
) -> dict[str, Any]:
    fold_rows: list[dict[str, Any]] = []
    for train_dates, test_dates in folds:
        tr = [r for r in rows if str(r["eval_date"]) in train_dates]
        te = [r for r in rows if str(r["eval_date"]) in test_dates]
        if len(tr) < 10 or len(te) < 5:
            continue
        if family == "type_a":
            params, train_delta = _best_type_a(tr, objective=objective)
            cf_te = _apply_type_a(te, score_lt=params["score_lt"], kospi_mode=params["kospi_mode"])
        else:
            params, train_delta = _best_cal(tr, objective=objective)
            cf_te = _apply_cal(te, alpha=params["alpha"], beta=params["beta"], deadzone=params["deadzone"])
        test_delta = _delta(te, cf_te)
        fold_rows.append(
            {
                "train_n": len(tr),
                "test_n": len(te),
                "selected_params": params,
                "train_delta_in_sample": train_delta,
                "train_margin_vs_bull": _margin(tr, _apply_type_a(tr, **params) if family == "type_a" else _apply_cal(tr, **params)),
                "test_delta_oos": test_delta,
                "test_baseline_hit_rate": _hit_rate(te)["price_directional_hit_rate"],
                "test_counterfactual_hit_rate": _hit_rate(cf_te)["price_directional_hit_rate"],
            }
        )
    mean_test = round(sum(f["test_delta_oos"] or 0 for f in fold_rows) / len(fold_rows), 6) if fold_rows else None
    pos = sum(1 for f in fold_rows if (f["test_delta_oos"] or 0) > 0)
    return {
        "family": family,
        "objective": objective,
        "folds": fold_rows,
        "mean_test_delta_oos": mean_test,
        "positive_test_folds": pos,
        "total_folds": len(fold_rows),
    }


def _global_holdout(
    rows: list[dict[str, Any]], *, train_frac: float, objective: str
) -> dict[str, Any]:
    dates = sorted({str(r["eval_date"])[:10] for r in rows})
    cut = max(10, int(len(dates) * train_frac))
    if cut >= len(dates) - 5:
        cut = len(dates) - 5
    tr_dates = set(dates[:cut])
    te_dates = set(dates[cut:])
    tr = [r for r in rows if str(r["eval_date"]) in tr_dates]
    te = [r for r in rows if str(r["eval_date"]) in te_dates]
    results: list[dict[str, Any]] = []
    for family in ("type_a", "calibration"):
        if family == "type_a":
            params, train_delta = _best_type_a(tr, objective=objective)
            cf_te = _apply_type_a(te, score_lt=params["score_lt"], kospi_mode=params["kospi_mode"])
        else:
            params, train_delta = _best_cal(tr, objective=objective)
            cf_te = _apply_cal(te, alpha=params["alpha"], beta=params["beta"], deadzone=params["deadzone"])
        results.append(
            {
                "family": family,
                "train_n": len(tr),
                "test_n": len(te),
                "train_date_range": [dates[0], dates[cut - 1]],
                "test_date_range": [dates[cut], dates[-1]],
                "selected_params": params,
                "train_delta": train_delta,
                "test_delta_oos": _delta(te, cf_te),
                "test_baseline_hit_rate": _hit_rate(te)["price_directional_hit_rate"],
                "test_counterfactual_hit_rate": _hit_rate(cf_te)["price_directional_hit_rate"],
            }
        )
    best = max(results, key=lambda x: x.get("test_delta_oos") or -1e9) if results else None
    return {"train_frac": train_frac, "objective": objective, "candidates": results, "best": best}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--dual-180-json", type=Path, default=DEFAULT_DUAL180)
    ap.add_argument("--n-folds", type=int, default=5)
    ap.add_argument("--train-frac", type=float, default=0.6)
    ap.add_argument("--min-positive-folds", type=int, default=4)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    score_doc = _load(args.score_json) if args.score_json.is_file() else {}
    dual_doc = _load(args.dual_180_json) if args.dual_180_json.is_file() else {}
    rows = _build_180d_rows(score_doc, dual_doc)
    if len(rows) < 30:
        raise SystemExit(f"insufficient 180d rows: {len(rows)}")

    dates = sorted({str(r["eval_date"])[:10] for r in rows})
    folds = _rolling_folds(dates, args.n_folds)
    objective = "margin_vs_bull"

    adaptive = [
        _adaptive_family(rows, folds, "type_a", objective=objective),
        _adaptive_family(rows, folds, "calibration", objective=objective),
    ]
    best_adaptive = max(adaptive, key=lambda x: x.get("mean_test_delta_oos") or -1e9) if adaptive else None
    global_ho = _global_holdout(rows, train_frac=args.train_frac, objective=objective)

    promote_adaptive = False
    if best_adaptive and best_adaptive.get("mean_test_delta_oos") is not None:
        promote_adaptive = (
            best_adaptive["mean_test_delta_oos"] > 0
            and best_adaptive.get("positive_test_folds", 0) >= args.min_positive_folds
        )
    promote_global = (global_ho.get("best") or {}).get("test_delta_oos") is not None and (
        global_ho["best"]["test_delta_oos"] or 0
    ) > 0

    out = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "train_objective": objective,
        "inputs": {"score_json": str(args.score_json), "dual_180_json": str(args.dual_180_json)},
        "n_dates_180d": len(dates),
        "adaptive_walkforward": adaptive,
        "best_adaptive_family": best_adaptive,
        "global_holdout": global_ho,
        "promotion_recommendation": (
            "candidate_for_human_signoff" if (promote_adaptive or promote_global) else "hold_research_only"
        ),
        "would_change_active": False,
        "combined_all_passed": False,
        "reasons": {
            "adaptive_pass": promote_adaptive,
            "global_holdout_pass": promote_global,
            "min_positive_folds_required": args.min_positive_folds,
        },
        "notes_ko": [
            "train objective=hit_rate - bull_baseline.",
            "global holdout=앞 train_frac fit, 뒤 블록 OOS.",
            "뉴스 join은 BTC 180d(2025-09~)와 news JSONL(2021 KOSPI) 날짜 불일치로 본 턴 제외.",
        ],
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json.resolve()}")
    ba = best_adaptive or {}
    gb = global_ho.get("best") or {}
    print(
        f"promotion={out['promotion_recommendation']} "
        f"adaptive={ba.get('family')} mean_oos={ba.get('mean_test_delta_oos')} "
        f"pos={ba.get('positive_test_folds')}/{ba.get('total_folds')} "
        f"global_test_delta={gb.get('test_delta_oos')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
