#!/usr/bin/env python3
"""[HYPO] Holdout replay for Type-A BTC direction-error candidate policy.

Policy under test (from sweep winner):
  bull -> bear when btc_price_lens_score < score_threshold (default 0.08)

Evaluates on:
  - operational 15d full
  - temporal tail holdout (last N days)
  - canonical holdout7 from dual 180d score
  - dual 180d excluding holdout7
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

from scripts.btrack_wrong_dir_holdout_core_v1 import HOLDOUT_7_DEFAULT
from scripts.build_btrack_btc_direction_error_spike_v1 import _enrich_btc_rows, _hit_rate, _load

DEFAULT_SCORE = ROOT / "docs/final/artifacts/btrack_prophecy_score_latest.json"
DEFAULT_DUAL = ROOT / "reports/btrack_ensemble_per_date_directions_dual_v1_latest.json"
DEFAULT_DUAL_180_SCORE = ROOT / "reports/btrack_prophecy_score_dual_leg_180d_rebuild_v1_latest.json"
DEFAULT_SWEEP = ROOT / "reports/btrack_btc_direction_error_policy_sweep_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/btrack_btc_direction_error_holdout_replay_v1_latest.json"
SCHEMA = "btrack_btc_direction_error_holdout_replay_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _apply_bear_score_threshold(
    rows: list[dict[str, Any]],
    *,
    score_threshold: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    adjusted: list[dict[str, Any]] = []
    changes: list[dict[str, Any]] = []
    for r in rows:
        pred = str(r.get("predicted_direction") or "").lower()
        actual = str(r.get("actual_direction") or "").lower()
        sc = r.get("btc_price_lens_score")
        adj = pred
        if pred == "bull" and sc is not None and float(sc) < score_threshold:
            adj = "bear"
        out = dict(r)
        out["predicted_direction"] = adj
        adjusted.append(out)
        if adj != pred:
            changes.append(
                {
                    "eval_date": str(r.get("eval_date"))[:10],
                    "from": pred,
                    "to": adj,
                    "score_threshold": score_threshold,
                    "btc_price_lens_score": sc,
                    "post_hoc_actual": actual,
                    "post_hoc_would_fix_hit": adj == actual,
                }
            )
    return adjusted, changes


def _eval_cohort(
    rows: list[dict[str, Any]],
    *,
    cohort_id: str,
    score_threshold: float,
) -> dict[str, Any]:
    baseline = _hit_rate(rows)
    cf_rows, changes = _apply_bear_score_threshold(rows, score_threshold=score_threshold)
    counterfactual = _hit_rate(cf_rows)
    delta = None
    if (
        baseline["price_directional_hit_rate"] is not None
        and counterfactual["price_directional_hit_rate"] is not None
    ):
        delta = round(
            counterfactual["price_directional_hit_rate"] - baseline["price_directional_hit_rate"],
            6,
        )
    return {
        "cohort_id": cohort_id,
        "eval_dates": [str(r.get("eval_date"))[:10] for r in rows],
        "n_days": len(rows),
        "baseline_btc": baseline,
        "counterfactual_btc": counterfactual,
        "delta_hit_rate": delta,
        "n_adjustments": len(changes),
        "adjustments": changes,
        "type_a_fix_count": sum(
            1
            for c in changes
            if c.get("post_hoc_would_fix_hit")
            and c.get("post_hoc_actual") == "bear"
        ),
    }


def _btc_rows_from_score(score_doc: dict[str, Any], dual_doc: dict[str, Any]) -> list[dict[str, Any]]:
    return _enrich_btc_rows(score_doc, dual_doc)


def _load_best_threshold(sweep_path: Path, default_threshold: float) -> float:
    if not sweep_path.is_file():
        return default_threshold
    try:
        sweep = _load(sweep_path)
    except Exception:
        return default_threshold
    best = sweep.get("best_candidate") if isinstance(sweep.get("best_candidate"), dict) else {}
    if str(best.get("to_direction") or "").lower() != "bear":
        return default_threshold
    value = best.get("score_lt")
    try:
        return float(value)
    except Exception:
        return default_threshold


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--dual-json", type=Path, default=DEFAULT_DUAL)
    ap.add_argument("--dual-180-score-json", type=Path, default=DEFAULT_DUAL_180_SCORE)
    ap.add_argument("--sweep-json", type=Path, default=DEFAULT_SWEEP)
    ap.add_argument("--score-threshold", type=float, default=None)
    ap.add_argument("--holdout-tail-n", type=int, default=5)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    threshold = (
        float(args.score_threshold)
        if args.score_threshold is not None
        else _load_best_threshold(args.sweep_json, 0.08)
    )
    holdout7 = [str(d)[:10] for d in HOLDOUT_7_DEFAULT]
    holdout7_set = set(holdout7)

    cohorts: list[dict[str, Any]] = []

    if args.score_json.is_file() and args.dual_json.is_file():
        btc = _btc_rows_from_score(_load(args.score_json), _load(args.dual_json))
        if btc:
            cohorts.append(_eval_cohort(btc, cohort_id="operational_15d_full", score_threshold=threshold))
            tail_n = max(1, min(args.holdout_tail_n, len(btc)))
            train = btc[:-tail_n]
            hold = btc[-tail_n:]
            if train:
                cohorts.append(
                    _eval_cohort(
                        train,
                        cohort_id=f"operational_15d_train_first_{len(train)}",
                        score_threshold=threshold,
                    )
                )
            cohorts.append(
                _eval_cohort(
                    hold,
                    cohort_id=f"operational_15d_temporal_holdout_tail_{tail_n}",
                    score_threshold=threshold,
                )
            )

    if args.dual_180_score_json.is_file():
        d180_doc = _load(args.dual_180_score_json)
        btc180 = _btc_rows_from_score(d180_doc, d180_doc)
        h7 = [r for r in btc180 if str(r.get("eval_date"))[:10] in holdout7_set]
        non_h7 = [r for r in btc180 if str(r.get("eval_date"))[:10] not in holdout7_set]
        if h7:
            cohorts.append(
                _eval_cohort(
                    h7,
                    cohort_id="canonical_holdout7_dual_180d",
                    score_threshold=threshold,
                )
            )
        if non_h7:
            cohorts.append(
                _eval_cohort(
                    non_h7,
                    cohort_id="dual_180d_excluding_holdout7",
                    score_threshold=threshold,
                )
            )

    tail = next(
        (c for c in cohorts if str(c.get("cohort_id", "")).startswith("operational_15d_temporal_holdout_tail")),
        None,
    )
    h7 = next((c for c in cohorts if c.get("cohort_id") == "canonical_holdout7_dual_180d"), None)
    full = next((c for c in cohorts if c.get("cohort_id") == "operational_15d_full"), None)

    temporal_delta = (tail or {}).get("delta_hit_rate")
    h7_delta = (h7 or {}).get("delta_hit_rate")

    full_adj_dates = {
        str(a.get("eval_date"))[:10]
        for a in (full or {}).get("adjustments") or []
        if isinstance(a, dict)
    }
    tail_adj_dates = {
        str(a.get("eval_date"))[:10]
        for a in (tail or {}).get("adjustments") or []
        if isinstance(a, dict)
    }
    tail_delta_inflated_by_single_overlap = bool(
        tail_adj_dates
        and tail_adj_dates <= full_adj_dates
        and len(tail_adj_dates) == 1
        and (tail or {}).get("n_days", 0) <= 7
    )

    promotion = "hold_research_only"
    if (
        isinstance(temporal_delta, float)
        and temporal_delta > 0
        and (tail or {}).get("n_adjustments", 0) >= 1
        and not tail_delta_inflated_by_single_overlap
    ):
        promotion = "candidate_for_extended_holdout_not_operational"
    if isinstance(h7_delta, float) and h7_delta <= 0:
        promotion = "hold_research_only"

    out: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "policy_under_test": "type_a_bull_to_bear_when_price_lens_below_threshold",
        "params": {"score_threshold": threshold, "holdout_tail_n": args.holdout_tail_n},
        "holdout7_dates": holdout7,
        "inputs": {
            "score_json": str(args.score_json) if args.score_json.is_file() else None,
            "dual_json": str(args.dual_json) if args.dual_json.is_file() else None,
            "dual_180_score_json": str(args.dual_180_score_json) if args.dual_180_score_json.is_file() else None,
            "sweep_json": str(args.sweep_json) if args.sweep_json.is_file() else None,
        },
        "cohorts": cohorts,
        "summary": {
            "temporal_holdout_tail_delta": temporal_delta,
            "canonical_holdout7_delta": h7_delta,
            "in_sample_15d_delta": (full or {}).get("delta_hit_rate"),
            "tail_delta_inflated_by_single_overlap": tail_delta_inflated_by_single_overlap,
            "adjustment_dates_full": sorted(full_adj_dates),
            "adjustment_dates_temporal_tail": sorted(tail_adj_dates),
        },
        "promotion_recommendation": promotion,
        "notes_ko": [
            "Type-A( bull 예측, 실제 bear ) 전용 홀드아웃 검증.",
            "tail 개선이 단일 날짜 중첩이면 독립 검증으로 보지 않음.",
            "delta>0이어도 Track A·실매매 자동 반영 금지.",
        ],
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json.resolve()}")
    print(
        f"promotion={promotion} temporal_delta={temporal_delta} holdout7_delta={h7_delta} threshold={threshold}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

