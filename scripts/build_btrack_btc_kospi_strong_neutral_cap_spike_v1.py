#!/usr/bin/env python3
"""[HYPO] Spike: on KOSPI-strong days, cap BTC leg prediction to neutral when it was bear.

Does not write btrack_prophecy_score_latest.json unless --write-counterfactual-score (off by default).
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
DEFAULT_OUT = ROOT / "reports/btrack_btc_kospi_strong_neutral_cap_spike_v1_latest.json"
SCHEMA = "btrack_btc_kospi_strong_neutral_cap_spike_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _hit_rate(rows: list[dict[str, Any]], *, pred_key: str = "predicted_direction") -> dict[str, Any]:
    hits = n = 0
    for r in rows:
        pred = str(r.get(pred_key) or r.get("predicted_direction") or "").lower()
        actual = str(r.get("actual_direction") or "").lower()
        if not pred or not actual:
            continue
        n += 1
        if pred == actual:
            hits += 1
    rate = round(hits / n, 6) if n else None
    return {"price_directional_hit_rate": rate, "n_evaluated": n, "price_hits": hits}


def _is_kospi_strong(
    k_row: dict[str, Any] | None,
    *,
    min_flow: float,
    min_kospi_ret_pct: float,
) -> tuple[bool, str]:
    if not k_row:
        return False, "no_kospi_row"
    flow = float(k_row.get("flow_score_for_reversal") or 0)
    k_pred = str(k_row.get("predicted_direction") or "").lower()
    k_ret = float(k_row.get("daily_return") or 0) * 100.0
    if flow >= min_flow and k_pred == "bull":
        return True, f"flow>={min_flow}_and_kospi_pred_bull"
    if k_ret >= min_kospi_ret_pct and k_pred in ("bull", "neutral"):
        return True, f"kospi_ret>={min_kospi_ret_pct}pct"
    return False, "not_strong"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--min-flow-score", type=float, default=3000.0)
    ap.add_argument("--min-kospi-return-pct", type=float, default=0.8)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--write-counterfactual-score", action="store_true")
    args = ap.parse_args(argv)

    doc = _load(args.score_json)
    rows = [r for r in (doc.get("rows") or []) if isinstance(r, dict)]
    btc = sorted([r for r in rows if str(r.get("instrument")).lower() == "btc"], key=lambda r: str(r.get("eval_date")))
    kospi_by = {
        str(r.get("eval_date"))[:10]: r for r in rows if str(r.get("instrument")).lower() == "kospi"
    }

    baseline = _hit_rate(btc)
    adjusted_rows: list[dict[str, Any]] = []
    changes: list[dict[str, Any]] = []

    for r in btc:
        d = str(r.get("eval_date"))[:10]
        k = kospi_by.get(d)
        strong, reason = _is_kospi_strong(
            k, min_flow=args.min_flow_score, min_kospi_ret_pct=args.min_kospi_return_pct
        )
        pred = str(r.get("predicted_direction") or "").lower()
        adj_pred = pred
        if strong and pred == "bear":
            adj_pred = "neutral"
        adj = dict(r)
        adj["predicted_direction_baseline"] = pred
        adj["predicted_direction"] = adj_pred
        adj["kospi_strong_day"] = strong
        adj["kospi_strong_reason"] = reason
        if adj_pred != pred:
            changes.append(
                {
                    "eval_date": d,
                    "from": pred,
                    "to": adj_pred,
                    "reason": reason,
                    "kospi_predicted": k.get("predicted_direction") if k else None,
                    "flow_score": k.get("flow_score_for_reversal") if k else None,
                }
            )
        adjusted_rows.append(adj)

    counterfactual = _hit_rate(adjusted_rows)
    delta = None
    if baseline["price_directional_hit_rate"] is not None and counterfactual["price_directional_hit_rate"] is not None:
        delta = round(counterfactual["price_directional_hit_rate"] - baseline["price_directional_hit_rate"], 6)

    out: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "rule_ko": "KOSPI-strong day AND BTC pred bear -> counterfactual neutral (else unchanged).",
        "params": {
            "min_flow_score": args.min_flow_score,
            "min_kospi_return_pct": args.min_kospi_return_pct,
        },
        "inputs": {"score_json": str(args.score_json)},
        "baseline_btc": baseline,
        "counterfactual_btc": counterfactual,
        "delta_hit_rate": delta,
        "n_adjustments": len(changes),
        "adjustments": changes,
        "promotion_recommendation": "hold_research_only",
        "notes_ko": [
            "운영 score JSON은 기본 미갱신. 승격·Track A 합선 없음.",
            "delta>0이어도 15일 표본·과적합 주의 — holdout 재채점 전제.",
        ],
    }
    if delta is not None and delta > 0 and counterfactual["price_directional_hit_rate"] is not None:
        if counterfactual["price_directional_hit_rate"] >= 0.5:
            out["promotion_recommendation"] = "candidate_for_holdout_replay_not_operational"

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.write_counterfactual_score:
        cf_path = ROOT / "reports/_tmp_btrack_score_btc_kospi_strong_cap_spike_v1.json"
        cf_doc = dict(doc)
        other = [r for r in rows if str(r.get("instrument")).lower() != "btc"]
        cf_doc["rows"] = other + adjusted_rows
        cf_doc["spike_note"] = "counterfactual; do not use for operational headline"
        cf_path.write_text(json.dumps(cf_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        out["counterfactual_score_path"] = str(cf_path)

    print(f"WROTE: {args.out_json.resolve()}")
    print(
        f"baseline={baseline['price_directional_hit_rate']} "
        f"counterfactual={counterfactual['price_directional_hit_rate']} "
        f"delta={delta} adjustments={len(changes)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
