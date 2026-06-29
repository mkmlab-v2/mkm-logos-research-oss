#!/usr/bin/env python3
"""[HYPO] Sweep Type-A BTC direction-error guards (neutral/bear conversion).

Explores threshold grids for bull->neutral and bull->bear conversions using
BTC price lens score/confidence. Does not modify operational score files.
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
DEFAULT_OUT = ROOT / "reports/btrack_btc_direction_error_policy_sweep_v1_latest.json"
SCHEMA = "btrack_btc_direction_error_policy_sweep_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _type_a_dates(rows: list[dict[str, Any]]) -> set[str]:
    return {
        str(r.get("eval_date"))[:10]
        for r in rows
        if str(r.get("predicted_direction") or "").lower() == "bull"
        and str(r.get("actual_direction") or "").lower() == "bear"
    }


def _apply(rows: list[dict[str, Any]], *, to_dir: str, score_lt: float, conf_lt: float | None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    adjusted: list[dict[str, Any]] = []
    changes: list[dict[str, Any]] = []
    for r in rows:
        pred = str(r.get("predicted_direction") or "").lower()
        adj = pred
        sc = r.get("btc_price_lens_score")
        cf = r.get("btc_price_lens_confidence")
        trig = False
        if pred == "bull" and sc is not None and float(sc) < score_lt:
            if conf_lt is None or (cf is not None and float(cf) < conf_lt):
                adj = to_dir
                trig = True
        out = dict(r)
        out["predicted_direction"] = adj
        adjusted.append(out)
        if trig and adj != pred:
            actual = str(r.get("actual_direction") or "").lower()
            changes.append(
                {
                    "eval_date": str(r.get("eval_date"))[:10],
                    "from": pred,
                    "to": adj,
                    "score_lt": score_lt,
                    "conf_lt": conf_lt,
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

    rows = _enrich_btc_rows(_load(args.score_json), _load(args.dual_json))
    baseline = _hit_rate(rows)
    type_a = _type_a_dates(rows)

    score_grid = [-0.20, -0.10, 0.0, 0.03, 0.05, 0.08, 0.12]
    conf_grid: list[float | None] = [None, 0.08, 0.10, 0.15]

    policies: list[dict[str, Any]] = []
    for to_dir in ("neutral", "bear"):
        for s in score_grid:
            for c in conf_grid:
                adj, ch = _apply(rows, to_dir=to_dir, score_lt=s, conf_lt=c)
                cf = _hit_rate(adj)
                delta = None
                if baseline["price_directional_hit_rate"] is not None and cf["price_directional_hit_rate"] is not None:
                    delta = round(cf["price_directional_hit_rate"] - baseline["price_directional_hit_rate"], 6)
                fixes = sum(1 for x in ch if x.get("post_hoc_would_fix_hit"))
                type_a_adj = sum(1 for x in ch if x.get("eval_date") in type_a)
                type_a_fix = sum(1 for x in ch if x.get("eval_date") in type_a and x.get("post_hoc_would_fix_hit"))
                policies.append(
                    {
                        "policy_id": f"{to_dir}_score_lt_{s}_conf_{c if c is not None else 'na'}",
                        "to_direction": to_dir,
                        "score_lt": s,
                        "conf_lt": c,
                        "counterfactual_btc": cf,
                        "delta_hit_rate": delta,
                        "n_adjustments": len(ch),
                        "post_hoc_would_fix_hit_count": fixes,
                        "type_a_adjustments": type_a_adj,
                        "type_a_fix_count": type_a_fix,
                    }
                )

    policies_sorted = sorted(
        policies,
        key=lambda p: (
            -1e9 if p.get("delta_hit_rate") is None else -float(p["delta_hit_rate"]),
            -int(p.get("type_a_fix_count") or 0),
            int(p.get("n_adjustments") or 0),
        ),
    )
    top = policies_sorted[:8]
    best = top[0] if top else None

    out: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "inputs": {"score_json": str(args.score_json), "dual_json": str(args.dual_json)},
        "baseline_btc": baseline,
        "type_a_dates": sorted(type_a),
        "n_type_a_days": len(type_a),
        "grid": {"score_lt": score_grid, "conf_lt": conf_grid, "to_direction": ["neutral", "bear"]},
        "top_candidates": top,
        "best_candidate": best,
        "promotion_recommendation": "hold_research_only",
        "notes_ko": [
            "type_a( bull->bear actual ) 전용 스윕. decouple 규칙과 분리.",
            "delta>0이어도 holdout 재채점 전 operational 반영 금지.",
        ],
    }
    if best and isinstance(best.get("delta_hit_rate"), float) and best["delta_hit_rate"] > 0:
        out["promotion_recommendation"] = "candidate_for_holdout_replay_not_operational"

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json.resolve()}")
    if best:
        print(
            "best",
            best["policy_id"],
            "delta",
            best.get("delta_hit_rate"),
            "typeAfix",
            best.get("type_a_fix_count"),
            "adj",
            best.get("n_adjustments"),
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
