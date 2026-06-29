#!/usr/bin/env python3
"""[HYPO] Holdout replay for BTC decouple spike policies (esp. P3 flow cap).

Evaluates baseline vs P3 on:
  - canonical holdout7 (frozen dates, dual-leg 180d score)
  - temporal tail holdout on operational 15d panel (no peeking at tail for tuning)

Does not modify operational score JSON. research_only.
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
from scripts.build_btrack_btc_decouple_spike_v2 import _apply_policy, _hit_rate, _is_decouple

DEFAULT_SCORE = ROOT / "docs/final/artifacts/btrack_prophecy_score_latest.json"
DEFAULT_DUAL_180 = ROOT / "reports/btrack_prophecy_score_dual_leg_180d_latest.json"
DEFAULT_OUT = ROOT / "reports/btrack_btc_decouple_spike_holdout_replay_v1_latest.json"
SCHEMA = "btrack_btc_decouple_spike_holdout_replay_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _rows_by_instrument(doc: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    rows = [r for r in (doc.get("rows") or []) if isinstance(r, dict)]
    btc = sorted(
        [r for r in rows if str(r.get("instrument")).lower() == "btc"],
        key=lambda r: str(r.get("eval_date")),
    )
    kospi_by = {
        str(r.get("eval_date"))[:10]: r for r in rows if str(r.get("instrument")).lower() == "kospi"
    }
    return btc, kospi_by


def _eval_cohort(
    btc_rows: list[dict[str, Any]],
    kospi_by: dict[str, dict[str, Any]],
    *,
    cohort_id: str,
    min_flow: float,
) -> dict[str, Any]:
    baseline = _hit_rate(btc_rows)
    p3_rows, p3_changes = _apply_policy(
        btc_rows, kospi_by, policy_id="P3_decouple_flow_bear_to_neutral", min_flow=min_flow
    )
    p3 = _hit_rate(p3_rows)
    delta = None
    if baseline["price_directional_hit_rate"] is not None and p3["price_directional_hit_rate"] is not None:
        delta = round(p3["price_directional_hit_rate"] - baseline["price_directional_hit_rate"], 6)
    decouple_n = sum(
        1
        for r in btc_rows
        if _is_decouple(
            kospi_by.get(str(r.get("eval_date"))[:10]),
            str(r.get("predicted_direction") or "").lower(),
        )
    )
    return {
        "cohort_id": cohort_id,
        "eval_dates": [str(r.get("eval_date"))[:10] for r in btc_rows],
        "n_days": len(btc_rows),
        "n_decouple_days": decouple_n,
        "baseline_btc": baseline,
        "p3_decouple_flow_bear_to_neutral": p3,
        "delta_hit_rate_p3": delta,
        "n_p3_adjustments": len(p3_changes),
        "p3_adjustments": p3_changes,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--dual-180-score-json", type=Path, default=DEFAULT_DUAL_180)
    ap.add_argument("--holdout-tail-n", type=int, default=5)
    ap.add_argument("--min-flow-score", type=float, default=3000.0)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    holdout7 = [str(d)[:10] for d in HOLDOUT_7_DEFAULT]
    holdout7_set = set(holdout7)

    cohorts: list[dict[str, Any]] = []

    if args.score_json.is_file():
        btc, kospi_by = _rows_by_instrument(_load(args.score_json))
        if btc:
            cohorts.append(_eval_cohort(btc, kospi_by, cohort_id="operational_15d_full", min_flow=args.min_flow_score))
            tail_n = max(1, min(args.holdout_tail_n, len(btc)))
            train = btc[:-tail_n]
            hold = btc[-tail_n:]
            if train:
                cohorts.append(
                    _eval_cohort(
                        train,
                        kospi_by,
                        cohort_id=f"operational_15d_train_first_{len(train)}",
                        min_flow=args.min_flow_score,
                    )
                )
            cohorts.append(
                _eval_cohort(
                    hold,
                    kospi_by,
                    cohort_id=f"operational_15d_temporal_holdout_tail_{tail_n}",
                    min_flow=args.min_flow_score,
                )
            )

    if args.dual_180_score_json.is_file():
        btc180, k180 = _rows_by_instrument(_load(args.dual_180_score_json))
        h7 = [r for r in btc180 if str(r.get("eval_date"))[:10] in holdout7_set]
        non_h7 = [r for r in btc180 if str(r.get("eval_date"))[:10] not in holdout7_set]
        if h7:
            cohorts.append(
                _eval_cohort(h7, k180, cohort_id="canonical_holdout7_dual_180d", min_flow=args.min_flow_score)
            )
        if non_h7:
            cohorts.append(
                _eval_cohort(
                    non_h7,
                    k180,
                    cohort_id="dual_180d_excluding_holdout7",
                    min_flow=args.min_flow_score,
                )
            )

    v2_path = ROOT / "reports/btrack_btc_decouple_spike_v2_latest.json"
    v2_in_sample_delta = None
    if v2_path.is_file():
        v2 = _load(v2_path)
        for p in v2.get("policies") or []:
            if p.get("policy_id") == "P3_decouple_flow_bear_to_neutral":
                v2_in_sample_delta = p.get("delta_hit_rate")

    tail_cohort = next(
        (c for c in cohorts if str(c.get("cohort_id", "")).startswith("operational_15d_temporal_holdout_tail")),
        None,
    )
    h7_cohort = next((c for c in cohorts if c.get("cohort_id") == "canonical_holdout7_dual_180d"), None)

    temporal_delta = (tail_cohort or {}).get("delta_hit_rate_p3")
    holdout7_delta = (h7_cohort or {}).get("delta_hit_rate_p3")

    full_cohort = next((c for c in cohorts if c.get("cohort_id") == "operational_15d_full"), None)
    full_adj_dates = {
        str(a.get("eval_date"))[:10]
        for a in (full_cohort or {}).get("p3_adjustments") or []
        if isinstance(a, dict)
    }
    tail_adj_dates = {
        str(a.get("eval_date"))[:10]
        for a in (tail_cohort or {}).get("p3_adjustments") or []
        if isinstance(a, dict)
    }
    tail_delta_inflated_by_single_overlap = bool(
        tail_adj_dates
        and tail_adj_dates <= full_adj_dates
        and len(tail_adj_dates) == 1
        and (tail_cohort or {}).get("n_days", 0) <= 7
    )

    promotion = "hold_research_only"
    if (
        temporal_delta is not None
        and temporal_delta > 0
        and (tail_cohort or {}).get("n_p3_adjustments", 0) >= 1
        and not tail_delta_inflated_by_single_overlap
    ):
        promotion = "candidate_for_extended_holdout_not_operational"
    if holdout7_delta is not None and holdout7_delta <= 0:
        promotion = "hold_research_only"

    out: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "policy_under_test": "P3_decouple_flow_bear_to_neutral",
        "params": {"min_flow_score": args.min_flow_score, "holdout_tail_n": args.holdout_tail_n},
        "holdout7_dates": holdout7,
        "inputs": {
            "score_json": str(args.score_json) if args.score_json.is_file() else None,
            "dual_180_score_json": str(args.dual_180_score_json) if args.dual_180_score_json.is_file() else None,
        },
        "comparison_v2_in_sample_p3_delta": v2_in_sample_delta,
        "cohorts": cohorts,
        "summary": {
            "temporal_holdout_tail_delta_p3": temporal_delta,
            "canonical_holdout7_delta_p3": holdout7_delta,
            "in_sample_15d_delta_p3": next(
                (c.get("delta_hit_rate_p3") for c in cohorts if c.get("cohort_id") == "operational_15d_full"),
                None,
            ),
            "tail_delta_inflated_by_single_overlap": tail_delta_inflated_by_single_overlap,
            "p3_adjustment_dates_full": sorted(full_adj_dates),
            "p3_adjustment_dates_temporal_tail": sorted(tail_adj_dates),
        },
        "promotion_recommendation": promotion,
        "notes_ko": [
            "canonical holdout7은 dual 180d에서 decouple(bull/bear) 0일 — P3 무반응이 정상.",
            "temporal tail +20%p는 n=5·조정 1일(5/29)과 in-sample 유일 조정일 동일 — 독립 검증 아님.",
            "173d( holdout7 제외)에서도 P3 조정 0·delta 0 — 정책이 역사 패널에 거의 발화하지 않음.",
            "operational 반영 전: 더 긴 dual-leg holdout·flow 백필·다른 decouple 규칙 필요.",
        ],
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json.resolve()}")
    print(f"promotion={promotion} temporal_delta={temporal_delta} holdout7_delta={holdout7_delta}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
