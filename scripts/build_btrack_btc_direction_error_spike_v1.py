#!/usr/bin/env python3
"""[HYPO] Spike: Type-A BTC direction errors (pred bull vs actual bear) — price-lens guards.

Separate from decouple (KOSPI bull / BTC bear). Uses operational score + dual per-date for lens.
research_only — does not write operational score.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCORE = ROOT / "docs/final/artifacts/btrack_prophecy_score_latest.json"
DEFAULT_DUAL = ROOT / "reports/btrack_ensemble_per_date_directions_dual_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/btrack_btc_direction_error_spike_v1_latest.json"
SCHEMA = "btrack_btc_direction_error_spike_v1"


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


def _price_lens(dual_btc_row: dict[str, Any] | None) -> tuple[float | None, float | None]:
    if not dual_btc_row:
        return None, None
    price = ((dual_btc_row.get("lens_values") or {}).get("price") or {}) if isinstance(
        dual_btc_row.get("lens_values"), dict
    ) else {}
    sc = price.get("score")
    conf = price.get("confidence")
    return (float(sc) if sc is not None else None, float(conf) if conf is not None else None)


def _enrich_btc_rows(
    score_doc: dict[str, Any], dual_doc: dict[str, Any]
) -> list[dict[str, Any]]:
    rows = [r for r in (score_doc.get("rows") or []) if isinstance(r, dict)]
    dual_btc = {
        str(r.get("eval_date"))[:10]: r
        for r in (dual_doc.get("rows") or [])
        if str(r.get("instrument")).lower() == "btc"
    }
    out: list[dict[str, Any]] = []
    for r in rows:
        if str(r.get("instrument")).lower() != "btc":
            continue
        d = str(r.get("eval_date"))[:10]
        dual_r = dual_btc.get(d)
        sc, conf = _price_lens(dual_r)
        row = dict(r)
        row["btc_price_lens_score"] = sc
        row["btc_price_lens_confidence"] = conf
        out.append(row)
    return sorted(out, key=lambda x: str(x.get("eval_date")))


def _apply(
    btc_rows: list[dict[str, Any]],
    *,
    policy_id: str,
    max_lens_score: float,
    max_confidence: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    adjusted: list[dict[str, Any]] = []
    changes: list[dict[str, Any]] = []
    for r in btc_rows:
        pred = str(r.get("predicted_direction") or "").lower()
        adj = pred
        sc = r.get("btc_price_lens_score")
        conf = r.get("btc_price_lens_confidence")
        triggered = False
        reason = ""

        if policy_id == "D1_bull_low_lens_neutral":
            if pred == "bull" and sc is not None and sc < max_lens_score:
                adj = "neutral"
                triggered = True
                reason = f"price_lens<{max_lens_score}"
        elif policy_id == "D2_bull_negative_lens_bear":
            if pred == "bull" and sc is not None and sc < 0:
                adj = "bear"
                triggered = True
                reason = "price_lens<0"
        elif policy_id == "D3_bull_low_conf_neutral":
            if pred == "bull" and conf is not None and conf < max_confidence:
                adj = "neutral"
                triggered = True
                reason = f"conf<{max_confidence}"
        elif policy_id == "D4_bull_lens_and_conf_neutral":
            if (
                pred == "bull"
                and sc is not None
                and sc <= 0
                and conf is not None
                and conf < max_confidence
            ):
                adj = "neutral"
                triggered = True
                reason = f"lens<={0}_and_conf<{max_confidence}"
        else:
            raise ValueError(policy_id)

        out = dict(r)
        out["predicted_direction_baseline"] = pred
        out["predicted_direction"] = adj
        if triggered and adj != pred:
            changes.append(
                {
                    "eval_date": str(r.get("eval_date"))[:10],
                    "policy_id": policy_id,
                    "from": pred,
                    "to": adj,
                    "reason": reason,
                    "btc_price_lens_score": sc,
                    "btc_price_lens_confidence": conf,
                    "post_hoc_actual": r.get("actual_direction"),
                    "post_hoc_would_fix_hit": adj == str(r.get("actual_direction") or "").lower(),
                }
            )
        adjusted.append(out)
    return adjusted, changes


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--dual-json", type=Path, default=DEFAULT_DUAL)
    ap.add_argument("--max-lens-score", type=float, default=0.08)
    ap.add_argument("--max-confidence", type=float, default=0.10)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    if not args.dual_json.is_file():
        raise SystemExit(f"missing dual json: {args.dual_json}")

    btc = _enrich_btc_rows(_load(args.score_json), _load(args.dual_json))
    baseline = _hit_rate(btc)

    policy_ids = [
        "D1_bull_low_lens_neutral",
        "D2_bull_negative_lens_bear",
        "D3_bull_low_conf_neutral",
        "D4_bull_lens_and_conf_neutral",
    ]
    policies: list[dict[str, Any]] = []
    best_delta = -1.0
    best_id: str | None = None

    for pid in policy_ids:
        adj, ch = _apply(
            btc,
            policy_id=pid,
            max_lens_score=args.max_lens_score,
            max_confidence=args.max_confidence,
        )
        cf = _hit_rate(adj)
        delta = None
        if baseline["price_directional_hit_rate"] is not None and cf["price_directional_hit_rate"] is not None:
            delta = round(cf["price_directional_hit_rate"] - baseline["price_directional_hit_rate"], 6)
        entry = {
            "policy_id": pid,
            "counterfactual_btc": cf,
            "delta_hit_rate": delta,
            "n_adjustments": len(ch),
            "post_hoc_would_fix_hit_count": sum(1 for c in ch if c.get("post_hoc_would_fix_hit")),
            "adjustments": ch,
        }
        policies.append(entry)
        if delta is not None and delta > best_delta:
            best_delta = delta
            best_id = pid

    type_a_dates = [
        str(r.get("eval_date"))[:10]
        for r in btc
        if str(r.get("predicted_direction") or "").lower() == "bull"
        and str(r.get("actual_direction") or "").lower() == "bear"
    ]

    out: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "problem_class": "type_a_direction_error_bull_vs_bear_actual",
        "params": {"max_lens_score": args.max_lens_score, "max_confidence": args.max_confidence},
        "inputs": {"score_json": str(args.score_json), "dual_json": str(args.dual_json)},
        "type_a_miss_dates": type_a_dates,
        "n_type_a_miss_days": len(type_a_dates),
        "baseline_btc": baseline,
        "policies": policies,
        "best_policy_by_delta": best_id,
        "promotion_recommendation": "hold_research_only",
        "notes_ko": [
            "decouple(P3)와 분리된 축 — KOSPI leg 불일치 없이 BTC bull 과신 보정.",
            "post_hoc_would_fix_hit는 사후 분석용.",
        ],
    }
    if best_delta > 0:
        out["promotion_recommendation"] = "candidate_for_holdout_replay_not_operational"

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json.resolve()}")
    for p in policies:
        print(
            f"  {p['policy_id']}: delta={p['delta_hit_rate']} adj={p['n_adjustments']} "
            f"fixes={p['post_hoc_would_fix_hit_count']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
