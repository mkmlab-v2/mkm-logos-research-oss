#!/usr/bin/env python3
"""[HYPO] Spike v2: decouple-only counterfactual policies for BTC dual leg.

Spec: docs/final/artifacts/btrack_btc_decouple_spike_v2_spec_v1.json
Does not write operational score JSON unless --write-counterfactual-score (off by default).
research_only — not Track A / not live trading.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCORE = ROOT / "docs/final/artifacts/btrack_prophecy_score_latest.json"
DEFAULT_SPEC = ROOT / "docs/final/artifacts/btrack_btc_decouple_spike_v2_spec_v1.json"
DEFAULT_OUT = ROOT / "reports/btrack_btc_decouple_spike_v2_latest.json"
SCHEMA = "btrack_btc_decouple_spike_v2"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _hit_rate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    hits = n = 0
    for r in rows:
        pred = str(r.get("predicted_direction") or "").lower()
        actual = str(r.get("actual_direction") or "").lower()
        if not pred or not actual:
            continue
        n += 1
        if pred == actual:
            hits += 1
    rate = round(hits / n, 6) if n else None
    return {"price_directional_hit_rate": rate, "n_evaluated": n, "price_hits": hits}


def _is_decouple(k_row: dict[str, Any] | None, btc_pred: str) -> bool:
    if not k_row:
        return False
    k_pred = str(k_row.get("predicted_direction") or "").lower()
    if k_pred != "bull" or btc_pred != "bear":
        return False
    return k_pred != btc_pred


def _apply_policy(
    btc_rows: list[dict[str, Any]],
    kospi_by: dict[str, dict[str, Any]],
    *,
    policy_id: str,
    min_flow: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    adjusted: list[dict[str, Any]] = []
    changes: list[dict[str, Any]] = []

    for r in btc_rows:
        d = str(r.get("eval_date"))[:10]
        k = kospi_by.get(d)
        pred = str(r.get("predicted_direction") or "").lower()
        decouple = _is_decouple(k, pred)
        flow = float((k or {}).get("flow_score_for_reversal") or 0)
        adj_pred = pred

        if policy_id == "P0_baseline":
            pass
        elif policy_id == "P1_decouple_bear_to_neutral":
            if decouple and pred == "bear":
                adj_pred = "neutral"
        elif policy_id == "P2_decouple_bear_to_bull":
            if decouple and pred == "bear":
                adj_pred = "bull"
        elif policy_id == "P3_decouple_flow_bear_to_neutral":
            if decouple and pred == "bear" and flow >= min_flow:
                adj_pred = "neutral"
        else:
            raise ValueError(f"unknown policy_id: {policy_id}")

        adj = dict(r)
        adj["predicted_direction_baseline"] = pred
        adj["predicted_direction"] = adj_pred
        adj["decouple_day"] = decouple
        if adj_pred != pred:
            changes.append(
                {
                    "eval_date": d,
                    "policy_id": policy_id,
                    "from": pred,
                    "to": adj_pred,
                    "kospi_predicted": (k or {}).get("predicted_direction"),
                    "flow_score": flow,
                    "post_hoc_actual": r.get("actual_direction"),
                    "post_hoc_would_fix_hit": adj_pred == str(r.get("actual_direction") or "").lower(),
                }
            )
        adjusted.append(adj)

    return adjusted, changes


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--spec-json", type=Path, default=DEFAULT_SPEC)
    ap.add_argument("--min-flow-score", type=float, default=3000.0)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--write-counterfactual-score", action="store_true")
    args = ap.parse_args(argv)

    spec = _load(args.spec_json) if args.spec_json.is_file() else {}
    doc = _load(args.score_json)
    rows = [r for r in (doc.get("rows") or []) if isinstance(r, dict)]
    btc = sorted(
        [r for r in rows if str(r.get("instrument")).lower() == "btc"],
        key=lambda r: str(r.get("eval_date")),
    )
    kospi_by = {
        str(r.get("eval_date"))[:10]: r for r in rows if str(r.get("instrument")).lower() == "kospi"
    }

    decouple_dates = [
        str(r.get("eval_date"))[:10]
        for r in btc
        if _is_decouple(kospi_by.get(str(r.get("eval_date"))[:10]), str(r.get("predicted_direction") or "").lower())
    ]

    baseline_rows = [dict(r, predicted_direction=str(r.get("predicted_direction") or "").lower()) for r in btc]
    baseline = _hit_rate(baseline_rows)

    policy_ids = ["P0_baseline", "P1_decouple_bear_to_neutral", "P2_decouple_bear_to_bull", "P3_decouple_flow_bear_to_neutral"]
    policy_results: list[dict[str, Any]] = []

    best_delta = -1.0
    best_policy: str | None = None

    for pid in policy_ids:
        if pid == "P0_baseline":
            adj_rows = baseline_rows
            changes: list[dict[str, Any]] = []
        else:
            adj_rows, changes = _apply_policy(
                btc, kospi_by, policy_id=pid, min_flow=args.min_flow_score
            )
        cf = _hit_rate(adj_rows)
        delta = None
        if baseline["price_directional_hit_rate"] is not None and cf["price_directional_hit_rate"] is not None:
            delta = round(cf["price_directional_hit_rate"] - baseline["price_directional_hit_rate"], 6)
        post_hoc_fixes = sum(1 for c in changes if c.get("post_hoc_would_fix_hit"))
        entry = {
            "policy_id": pid,
            "counterfactual_btc": cf,
            "delta_hit_rate": delta,
            "n_adjustments": len(changes),
            "post_hoc_would_fix_hit_count": post_hoc_fixes,
            "adjustments": changes,
        }
        policy_results.append(entry)
        if delta is not None and delta > best_delta:
            best_delta = delta
            best_policy = pid

    v1_ref = ROOT / "reports/btrack_btc_kospi_strong_neutral_cap_spike_v1_latest.json"
    v1_delta = None
    if v1_ref.is_file():
        v1_delta = _load(v1_ref).get("delta_hit_rate")

    out: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "spec_json": str(args.spec_json),
        "inputs": {"score_json": str(args.score_json)},
        "decouple_dates_in_window": decouple_dates,
        "n_decouple_days": len(decouple_dates),
        "baseline_btc": baseline,
        "policies": policy_results,
        "best_policy_by_delta": best_policy,
        "comparison_v1_neutral_cap_delta": v1_delta,
        "promotion_recommendation": "hold_research_only",
        "notes_ko": [
            "트리거는 kospi pred bull + btc pred bear(decouple)만 사용.",
            "post_hoc_* 필드는 사후 분석용이며 운영 트리거에 쓰지 않음.",
            "delta>0이어도 holdout·휴먼 승인 전 operational 반영 금지.",
        ],
    }
    if best_delta > 0 and best_policy and best_policy != "P0_baseline":
        out["promotion_recommendation"] = "candidate_for_holdout_replay_not_operational"

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.write_counterfactual_score and best_policy and best_policy != "P0_baseline":
        adj_rows, _ = _apply_policy(btc, kospi_by, policy_id=best_policy, min_flow=args.min_flow_score)
        cf_path = ROOT / "reports/_tmp_btrack_score_btc_decouple_spike_v2.json"
        cf_doc = dict(doc)
        other = [r for r in rows if str(r.get("instrument")).lower() != "btc"]
        cf_doc["rows"] = other + adj_rows
        cf_doc["spike_note"] = f"counterfactual {best_policy}; do not use for operational headline"
        cf_path.write_text(json.dumps(cf_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        out["counterfactual_score_path"] = str(cf_path)

    print(f"WROTE: {args.out_json.resolve()}")
    for p in policy_results:
        if p["policy_id"] == "P0_baseline":
            continue
        print(
            f"  {p['policy_id']}: rate={p['counterfactual_btc']['price_directional_hit_rate']} "
            f"delta={p['delta_hit_rate']} adj={p['n_adjustments']} "
            f"post_hoc_fixes={p['post_hoc_would_fix_hit_count']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
