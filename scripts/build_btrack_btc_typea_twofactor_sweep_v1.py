#!/usr/bin/env python3
"""[HYPO] Type-A two-factor policy sweep (bull->bear) for BTC.

Second factors use prediction-time fields only (KOSPI predicted direction, lens confidence).
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
DEFAULT_OUT = ROOT / "reports/btrack_btc_typea_twofactor_sweep_v1_latest.json"
SCHEMA = "btrack_btc_typea_twofactor_sweep_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _enrich_with_kospi_pred(rows: list[dict[str, Any]], score_doc: dict[str, Any]) -> list[dict[str, Any]]:
    kospi_by = {
        str(r.get("eval_date"))[:10]: str(r.get("predicted_direction") or "").lower()
        for r in (score_doc.get("rows") or [])
        if isinstance(r, dict) and str(r.get("instrument")).lower() == "kospi"
    }
    out: list[dict[str, Any]] = []
    for r in rows:
        d = str(r.get("eval_date"))[:10]
        x = dict(r)
        x["kospi_predicted_direction"] = kospi_by.get(d)
        out.append(x)
    return out


def _apply(
    rows: list[dict[str, Any]],
    *,
    score_lt: float,
    conf_lt: float | None,
    kospi_mode: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
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
                    "kospi_predicted_direction": kpred,
                    "btc_price_lens_score": sc,
                    "btc_price_lens_confidence": cf,
                    "post_hoc_actual": actual,
                    "post_hoc_would_fix_hit": adj == actual,
                }
            )
    return adjusted, changes


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--dual-json", type=Path, default=DEFAULT_DUAL)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    score_doc = _load(args.score_json)
    dual_doc = _load(args.dual_json)
    btc = _enrich_btc_rows(score_doc, dual_doc)
    btc = _enrich_with_kospi_pred(btc, score_doc)

    baseline = _hit_rate(btc)
    type_a = {
        str(r.get("eval_date"))[:10]
        for r in btc
        if str(r.get("predicted_direction") or "").lower() == "bull"
        and str(r.get("actual_direction") or "").lower() == "bear"
    }

    score_grid = [0.05, 0.08, 0.12]
    conf_grid: list[float | None] = [None, 0.08, 0.10]
    kospi_modes = ["bull_only", "not_bear"]

    candidates: list[dict[str, Any]] = []
    for s in score_grid:
        for c in conf_grid:
            for km in kospi_modes:
                adj, ch = _apply(btc, score_lt=s, conf_lt=c, kospi_mode=km)
                cf = _hit_rate(adj)
                delta = None
                if baseline["price_directional_hit_rate"] is not None and cf["price_directional_hit_rate"] is not None:
                    delta = round(cf["price_directional_hit_rate"] - baseline["price_directional_hit_rate"], 6)
                candidates.append(
                    {
                        "policy_id": f"bear_score_lt_{s}_conf_{c if c is not None else 'na'}_k_{km}",
                        "score_lt": s,
                        "conf_lt": c,
                        "kospi_mode": km,
                        "counterfactual_btc": cf,
                        "delta_hit_rate": delta,
                        "n_adjustments": len(ch),
                        "post_hoc_would_fix_hit_count": sum(1 for x in ch if x.get("post_hoc_would_fix_hit")),
                        "type_a_adjustments": sum(1 for x in ch if x.get("eval_date") in type_a),
                        "type_a_fix_count": sum(
                            1
                            for x in ch
                            if x.get("eval_date") in type_a and x.get("post_hoc_would_fix_hit")
                        ),
                    }
                )

    candidates = sorted(
        candidates,
        key=lambda x: (
            -1e9 if x.get("delta_hit_rate") is None else -float(x["delta_hit_rate"]),
            -int(x.get("type_a_fix_count") or 0),
            int(x.get("n_adjustments") or 0),
        ),
    )

    best = candidates[0] if candidates else None
    out: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "inputs": {"score_json": str(args.score_json), "dual_json": str(args.dual_json)},
        "baseline_btc": baseline,
        "n_type_a_days": len(type_a),
        "type_a_dates": sorted(type_a),
        "grid": {"score_lt": score_grid, "conf_lt": conf_grid, "kospi_mode": kospi_modes},
        "best_candidate": best,
        "top_candidates": candidates[:8],
        "promotion_recommendation": "hold_research_only",
        "notes_ko": [
            "2조건: score 임계 + (kospi_pred 또는 confidence) 게이트.",
            "delta>0이어도 holdout replay 전 operational 반영 금지.",
        ],
    }
    if best and isinstance(best.get("delta_hit_rate"), float) and best["delta_hit_rate"] > 0:
        out["promotion_recommendation"] = "candidate_for_holdout_replay_not_operational"

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json.resolve()}")
    if best:
        print("best", best["policy_id"], "delta", best.get("delta_hit_rate"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
