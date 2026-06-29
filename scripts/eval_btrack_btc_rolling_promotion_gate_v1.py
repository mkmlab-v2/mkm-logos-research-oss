#!/usr/bin/env python3
"""[HYPO] Rolling blocked walk-forward promotion gate for BTC calibration/type-A policies.

Uses 180d dual per-date directions + score actuals. Does not modify operational score.
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

from scripts.build_btrack_btc_direction_error_spike_v1 import _hit_rate, _load

DEFAULT_SCORE = ROOT / "reports/btrack_prophecy_score_dual_leg_180d_rebuild_v1_latest.json"
DEFAULT_DUAL180 = ROOT / "reports/btrack_ensemble_per_date_directions_dual_180d_rebuild_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/btrack_btc_rolling_promotion_gate_v1_latest.json"
SCHEMA = "btrack_btc_rolling_promotion_gate_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _dir_from_score(score: float, deadzone: float) -> str:
    if score > deadzone:
        return "bull"
    if score < -deadzone:
        return "bear"
    return "neutral"


def _apply_type_a(rows: list[dict[str, Any]], *, score_lt: float, kospi_mode: str) -> list[dict[str, Any]]:
    out = []
    for r in rows:
        pred = str(r.get("predicted_direction") or "").lower()
        kpred = str(r.get("kospi_predicted_direction") or "").lower()
        adj = pred
        sc = r.get("btc_price_lens_score")
        if pred == "bull" and sc is not None and float(sc) < score_lt:
            if kospi_mode == "bull_only" and kpred == "bull":
                adj = "bear"
            elif kospi_mode == "not_bear" and kpred in ("bull", "neutral"):
                adj = "bear"
        x = dict(r)
        x["predicted_direction"] = adj
        out.append(x)
    return out


def _apply_cal(rows: list[dict[str, Any]], *, alpha: float, beta: float, deadzone: float) -> list[dict[str, Any]]:
    out = []
    for r in rows:
        pred = str(r.get("predicted_direction") or "").lower()
        adj = pred
        sc = r.get("btc_price_lens_score")
        if sc is not None:
            adj = _dir_from_score(alpha * float(sc) + beta, deadzone)
        x = dict(r)
        x["predicted_direction"] = adj
        out.append(x)
    return out


def _build_180d_rows(score_doc: dict[str, Any], dual_doc: dict[str, Any]) -> list[dict[str, Any]]:
    score_by = {
        str(r.get("eval_date"))[:10]: r
        for r in (score_doc.get("rows") or [])
        if isinstance(r, dict) and str(r.get("instrument")).lower() == "btc"
    }
    dual_btc = {
        str(r.get("eval_date"))[:10]: r
        for r in (dual_doc.get("rows") or [])
        if isinstance(r, dict) and str(r.get("instrument")).lower() == "btc"
    }
    dual_kospi = {
        str(r.get("eval_date"))[:10]: r
        for r in (dual_doc.get("rows") or [])
        if isinstance(r, dict) and str(r.get("instrument")).lower() == "kospi"
    }
    dates = sorted(set(dual_btc) & set(score_by))
    out: list[dict[str, Any]] = []
    for d in dates:
        br = dual_btc.get(d)
        kr = dual_kospi.get(d)
        sr = score_by.get(d)
        if not br or not sr:
            continue
        price = ((br.get("lens_values") or {}).get("price") or {}) if isinstance(br.get("lens_values"), dict) else {}
        sc = price.get("score")
        row = {
            "eval_date": d,
            "predicted_direction": br.get("predicted_direction"),
            "actual_direction": sr.get("actual_direction"),
            "btc_price_lens_score": float(sc) if sc is not None else None,
            "kospi_predicted_direction": (kr or {}).get("predicted_direction"),
        }
        out.append(row)
    return out


def _eval_policy(rows: list[dict[str, Any]], policy_id: str, params: dict[str, Any]) -> dict[str, Any]:
    if policy_id.startswith("cal_"):
        cf = _apply_cal(rows, alpha=params["alpha"], beta=params["beta"], deadzone=params["deadzone"])
    else:
        cf = _apply_type_a(rows, score_lt=params["score_lt"], kospi_mode=params["kospi_mode"])
    base = _hit_rate(rows)
    cfm = _hit_rate(cf)
    delta = None
    if base["price_directional_hit_rate"] is not None and cfm["price_directional_hit_rate"] is not None:
        delta = round(cfm["price_directional_hit_rate"] - base["price_directional_hit_rate"], 6)
    return {"policy_id": policy_id, "params": params, "baseline": base, "counterfactual": cfm, "delta_hit_rate": delta}


def _rolling_folds(dates: list[str], n_folds: int) -> list[tuple[list[str], list[str]]]:
    """Expanding train + contiguous test blocks (B0..B{n-1})."""
    n = len(dates)
    if n_folds < 2 or n < 20:
        mid = max(1, n // 2)
        return [(dates[:mid], dates[mid:])]
    boundaries = [round(i * n / n_folds) for i in range(n_folds + 1)]
    folds: list[tuple[list[str], list[str]]] = []
    for i in range(n_folds - 1):
        train = dates[: boundaries[i + 1]]
        test = dates[boundaries[i + 1] : boundaries[i + 2]]
        if len(train) >= 10 and len(test) >= 5:
            folds.append((train, test))
    return folds


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

    policies = [
        ("type_a_bull_bear_score08_kospi_bull", {"score_lt": 0.08, "kospi_mode": "bull_only"}),
        ("type_a_bull_bear_score08_kospi_not_bear", {"score_lt": 0.08, "kospi_mode": "not_bear"}),
        ("cal_a08_b-008_dz002", {"alpha": 0.8, "beta": -0.08, "deadzone": 0.02}),
    ]

    dates = sorted({str(r["eval_date"])[:10] for r in rows})
    folds = _rolling_folds(dates, args.n_folds)

    policy_results: list[dict[str, Any]] = []
    for pid, params in policies:
        fold_deltas = []
        for train_dates, test_dates in folds:
            tr = [r for r in rows if str(r["eval_date"]) in train_dates]
            te = [r for r in rows if str(r["eval_date"]) in test_dates]
            if len(te) < 5:
                continue
            ev_tr = _eval_policy(tr, pid, params)
            ev_te = _eval_policy(te, pid, params)
            fold_deltas.append(
                {
                    "train_n": len(tr),
                    "test_n": len(te),
                    "train_delta": ev_tr["delta_hit_rate"],
                    "test_delta": ev_te["delta_hit_rate"],
                    "test_baseline_hit_rate": ev_te["baseline"]["price_directional_hit_rate"],
                    "test_counterfactual_hit_rate": ev_te["counterfactual"]["price_directional_hit_rate"],
                }
            )
        if fold_deltas:
            mean_test = sum(f["test_delta"] or 0 for f in fold_deltas) / len(fold_deltas)
            pos = sum(1 for f in fold_deltas if (f["test_delta"] or 0) > 0)
            policy_results.append(
                {
                    "policy_id": pid,
                    "params": params,
                    "folds": fold_deltas,
                    "mean_test_delta": round(mean_test, 6),
                    "positive_test_folds": pos,
                    "total_folds": len(fold_deltas),
                }
            )

    # pick best by mean_test_delta
    best = max(policy_results, key=lambda x: x.get("mean_test_delta") or -1e9) if policy_results else None

    promote = False
    reasons: list[str] = []
    if best:
        mean_ok = (best.get("mean_test_delta") or 0) > args.min_mean_oos_delta
        folds_ok = best.get("positive_test_folds", 0) >= args.min_positive_folds
        reasons.append("mean_test_delta_positive" if mean_ok else "mean_test_delta_not_positive")
        reasons.append("enough_positive_folds" if folds_ok else "insufficient_positive_folds")
        promote = mean_ok and folds_ok
    else:
        reasons.append("no_policy_results")

    out = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "inputs": {"score_json": str(args.score_json), "dual_180_json": str(args.dual_180_json)},
        "n_dates_180d": len(dates),
        "n_folds": args.n_folds,
        "gate_thresholds": {
            "min_mean_oos_delta": args.min_mean_oos_delta,
            "min_positive_folds": args.min_positive_folds,
        },
        "policies": policy_results,
        "best_policy": best,
        "promotion_recommendation": "candidate_for_human_signoff" if promote else "hold_research_only",
        "would_change_active": False,
        "combined_all_passed": False,
        "reasons": reasons,
        "notes_ko": [
            "Track A·실매매 자동 승격 금지.",
            "would_change_active=false 고정.",
            "인간 승인 후 research_only 재평가 필요.",
        ],
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json.resolve()}")
    print(f"promotion={out['promotion_recommendation']} best={best['policy_id'] if best else None} mean_delta={best.get('mean_test_delta') if best else None}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())