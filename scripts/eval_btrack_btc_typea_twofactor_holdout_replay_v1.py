#!/usr/bin/env python3
"""[HYPO] Holdout replay for Type-A two-factor best candidate.

Loads best candidate from btrack_btc_typea_twofactor_sweep_v1_latest.json unless overridden.
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
DEFAULT_DUAL_180 = ROOT / "reports/btrack_prophecy_score_dual_leg_180d_rebuild_v1_latest.json"
DEFAULT_DUAL_180_PERDATE = ROOT / "reports/btrack_ensemble_per_date_directions_dual_180d_rebuild_v1_latest.json"
DEFAULT_SWEEP = ROOT / "reports/btrack_btc_typea_twofactor_sweep_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/btrack_btc_typea_twofactor_holdout_replay_v1_latest.json"
SCHEMA = "btrack_btc_typea_twofactor_holdout_replay_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _apply(rows: list[dict[str, Any]], *, score_lt: float, conf_lt: float | None, kospi_mode: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    adjusted: list[dict[str, Any]] = []
    changes: list[dict[str, Any]] = []
    for r in rows:
        pred = str(r.get("predicted_direction") or "").lower()
        actual = str(r.get("actual_direction") or "").lower()
        kpred = str(r.get("kospi_predicted_direction") or "").lower()
        sc = r.get("btc_price_lens_score")
        cf = r.get("btc_price_lens_confidence")
        adj = pred

        cond_score = pred == "bull" and sc is not None and float(sc) < score_lt
        cond_conf = conf_lt is None or (cf is not None and float(cf) < conf_lt)
        if kospi_mode == "bull_only":
            cond_k = kpred == "bull"
        elif kospi_mode == "not_bear":
            cond_k = kpred in ("bull", "neutral")
        else:
            cond_k = True

        if cond_score and cond_conf and cond_k:
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
                    "score_lt": score_lt,
                    "conf_lt": conf_lt,
                    "kospi_mode": kospi_mode,
                    "post_hoc_actual": actual,
                    "post_hoc_would_fix_hit": adj == actual,
                }
            )
    return adjusted, changes


def _enrich_kpred(rows: list[dict[str, Any]], score_doc: dict[str, Any]) -> list[dict[str, Any]]:
    kby = {
        str(r.get("eval_date"))[:10]: str(r.get("predicted_direction") or "").lower()
        for r in (score_doc.get("rows") or [])
        if isinstance(r, dict) and str(r.get("instrument")).lower() == "kospi"
    }
    out = []
    for r in rows:
        x = dict(r)
        x["kospi_predicted_direction"] = kby.get(str(r.get("eval_date"))[:10])
        out.append(x)
    return out


def _eval(rows: list[dict[str, Any]], *, cohort_id: str, score_lt: float, conf_lt: float | None, kospi_mode: str) -> dict[str, Any]:
    baseline = _hit_rate(rows)
    adj_rows, changes = _apply(rows, score_lt=score_lt, conf_lt=conf_lt, kospi_mode=kospi_mode)
    cf = _hit_rate(adj_rows)
    delta = None
    if baseline["price_directional_hit_rate"] is not None and cf["price_directional_hit_rate"] is not None:
        delta = round(cf["price_directional_hit_rate"] - baseline["price_directional_hit_rate"], 6)
    return {
        "cohort_id": cohort_id,
        "n_days": len(rows),
        "eval_dates": [str(r.get("eval_date"))[:10] for r in rows],
        "baseline_btc": baseline,
        "counterfactual_btc": cf,
        "delta_hit_rate": delta,
        "n_adjustments": len(changes),
        "adjustments": changes,
        "type_a_fix_count": sum(1 for c in changes if c.get("post_hoc_would_fix_hit") and c.get("post_hoc_actual") == "bear"),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--dual-json", type=Path, default=DEFAULT_DUAL)
    ap.add_argument("--dual-180-score-json", type=Path, default=DEFAULT_DUAL_180)
    ap.add_argument("--dual-180-perdate-json", type=Path, default=DEFAULT_DUAL_180_PERDATE)
    ap.add_argument("--sweep-json", type=Path, default=DEFAULT_SWEEP)
    ap.add_argument("--score-lt", type=float, default=None)
    ap.add_argument("--conf-lt", type=float, default=None)
    ap.add_argument("--kospi-mode", choices=["bull_only", "not_bear"], default=None)
    ap.add_argument("--holdout-tail-n", type=int, default=5)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    sweep = _load(args.sweep_json) if args.sweep_json.is_file() else {}
    best = sweep.get("best_candidate") if isinstance(sweep.get("best_candidate"), dict) else {}

    score_lt = float(args.score_lt if args.score_lt is not None else best.get("score_lt", 0.08))
    conf_lt = args.conf_lt if args.conf_lt is not None else best.get("conf_lt")
    if conf_lt is not None:
        conf_lt = float(conf_lt)
    kospi_mode = args.kospi_mode or str(best.get("kospi_mode") or "bull_only")

    score_doc = _load(args.score_json)
    dual_doc = _load(args.dual_json)
    btc = _enrich_btc_rows(score_doc, dual_doc)
    btc = _enrich_kpred(btc, score_doc)

    holdout7 = [str(d)[:10] for d in HOLDOUT_7_DEFAULT]
    h7_set = set(holdout7)

    cohorts: list[dict[str, Any]] = []
    if btc:
        cohorts.append(_eval(btc, cohort_id="operational_15d_full", score_lt=score_lt, conf_lt=conf_lt, kospi_mode=kospi_mode))
        n = max(1, min(args.holdout_tail_n, len(btc)))
        train, tail = btc[:-n], btc[-n:]
        if train:
            cohorts.append(_eval(train, cohort_id=f"operational_15d_train_first_{len(train)}", score_lt=score_lt, conf_lt=conf_lt, kospi_mode=kospi_mode))
        cohorts.append(_eval(tail, cohort_id=f"operational_15d_temporal_holdout_tail_{n}", score_lt=score_lt, conf_lt=conf_lt, kospi_mode=kospi_mode))

    if args.dual_180_score_json.is_file():
        d180 = _load(args.dual_180_score_json)
        d180_dual = _load(args.dual_180_perdate_json) if args.dual_180_perdate_json.is_file() else d180
        btc180 = _enrich_btc_rows(d180, d180_dual)
        btc180 = _enrich_kpred(btc180, d180)
        h7 = [r for r in btc180 if str(r.get("eval_date"))[:10] in h7_set]
        non = [r for r in btc180 if str(r.get("eval_date"))[:10] not in h7_set]
        if h7:
            cohorts.append(_eval(h7, cohort_id="canonical_holdout7_dual_180d", score_lt=score_lt, conf_lt=conf_lt, kospi_mode=kospi_mode))
        if non:
            cohorts.append(_eval(non, cohort_id="dual_180d_excluding_holdout7", score_lt=score_lt, conf_lt=conf_lt, kospi_mode=kospi_mode))

    tail = next((c for c in cohorts if str(c.get("cohort_id", "")).startswith("operational_15d_temporal_holdout_tail")), None)
    h7 = next((c for c in cohorts if c.get("cohort_id") == "canonical_holdout7_dual_180d"), None)

    promotion = "hold_research_only"
    temporal_delta = (tail or {}).get("delta_hit_rate")
    holdout7_delta = (h7 or {}).get("delta_hit_rate")
    if isinstance(temporal_delta, float) and temporal_delta > 0 and (tail or {}).get("n_adjustments", 0) > 0:
        promotion = "candidate_for_extended_holdout_not_operational"
    if isinstance(holdout7_delta, float) and holdout7_delta <= 0:
        promotion = "hold_research_only"

    out = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "policy_under_test": "type_a_twofactor_bull_to_bear",
        "params": {"score_lt": score_lt, "conf_lt": conf_lt, "kospi_mode": kospi_mode, "holdout_tail_n": args.holdout_tail_n},
        "holdout7_dates": holdout7,
        "cohorts": cohorts,
        "summary": {
            "temporal_holdout_tail_delta": temporal_delta,
            "canonical_holdout7_delta": holdout7_delta,
            "in_sample_15d_delta": next((c.get("delta_hit_rate") for c in cohorts if c.get("cohort_id") == "operational_15d_full"), None),
        },
        "promotion_recommendation": promotion,
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json.resolve()}")
    print(f"promotion={promotion} temporal_delta={temporal_delta} holdout7_delta={holdout7_delta}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
