#!/usr/bin/env python3
"""[HYPO] Apply Type-A BTC guard (bull->bear) to score JSON rows — research shadow lane."""
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
DEFAULT_POLICY = ROOT / "docs/final/artifacts/btrack_btc_typea_guard_v1.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/btrack_prophecy_score_btc_typea_guard_v1_latest.json"
SCHEMA = "btrack_btc_typea_guard_apply_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _kospi_pred_by_date(score_doc: dict[str, Any]) -> dict[str, str]:
    return {
        str(r.get("eval_date"))[:10]: str(r.get("predicted_direction") or "").lower()
        for r in (score_doc.get("rows") or [])
        if isinstance(r, dict) and str(r.get("instrument")).lower() == "kospi"
    }


def apply_typea_guard(
    score_doc: dict[str, Any],
    dual_doc: dict[str, Any],
    *,
    score_lt: float,
    kospi_mode: str,
    policy_id: str,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    kospi_by = _kospi_pred_by_date(score_doc)
    btc_enriched = _enrich_btc_rows(score_doc, dual_doc)
    for r in btc_enriched:
        d = str(r.get("eval_date"))[:10]
        r["kospi_predicted_direction"] = kospi_by.get(d)

    baseline = _hit_rate(btc_enriched)
    changes: list[dict[str, Any]] = []
    btc_adj: dict[str, str] = {}

    for r in btc_enriched:
        d = str(r.get("eval_date"))[:10]
        pred = str(r.get("predicted_direction") or "").lower()
        kpred = str(r.get("kospi_predicted_direction") or "").lower()
        sc = r.get("btc_price_lens_score")
        adj = pred
        if pred == "bull" and sc is not None and float(sc) < score_lt:
            if kospi_mode == "bull_only" and kpred == "bull":
                adj = "bear"
            elif kospi_mode == "not_bear" and kpred in ("bull", "neutral"):
                adj = "bear"
        btc_adj[d] = adj
        if adj != pred:
            changes.append(
                {
                    "eval_date": d,
                    "instrument": "btc",
                    "from": pred,
                    "to": adj,
                    "btc_price_lens_score": sc,
                    "kospi_predicted_direction": kpred,
                    "score_lt": score_lt,
                    "kospi_mode": kospi_mode,
                }
            )

    out_doc = json.loads(json.dumps(score_doc))
    rows_out: list[dict[str, Any]] = []
    for r in out_doc.get("rows") or []:
        if not isinstance(r, dict):
            continue
        row = dict(r)
        if str(row.get("instrument")).lower() == "btc":
            d = str(row.get("eval_date"))[:10]
            if d in btc_adj:
                row["predicted_direction"] = btc_adj[d]
                row["typea_guard_applied"] = True
                row["typea_guard_policy_id"] = policy_id
        rows_out.append(row)
    out_doc["rows"] = rows_out
    meta = out_doc.setdefault("meta", {})
    if isinstance(meta, dict):
        meta["btc_typea_guard_v1"] = {
            "policy_id": policy_id,
            "score_lt": score_lt,
            "kospi_mode": kospi_mode,
            "n_btc_rows_changed": len(changes),
            "applied_at_utc": _utc_now(),
        }
    inputs = out_doc.setdefault("inputs", {})
    if isinstance(inputs, dict):
        inputs["btc_typea_guard_policy"] = policy_id

    cf = _hit_rate(
        [
            {**r, "predicted_direction": btc_adj.get(str(r.get("eval_date"))[:10], r.get("predicted_direction"))}
            for r in btc_enriched
        ]
    )
    delta = None
    if baseline["price_directional_hit_rate"] is not None and cf["price_directional_hit_rate"] is not None:
        delta = round(cf["price_directional_hit_rate"] - baseline["price_directional_hit_rate"], 6)

    summary = {
        "baseline_btc": baseline,
        "counterfactual_btc": cf,
        "delta_hit_rate": delta,
        "n_changes": len(changes),
        "changes": changes,
    }
    return out_doc, changes, summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--dual-json", type=Path, default=DEFAULT_DUAL)
    ap.add_argument("--policy-json", type=Path, default=DEFAULT_POLICY)
    ap.add_argument("--score-lt", type=float, default=None)
    ap.add_argument("--kospi-mode", choices=["bull_only", "not_bear"], default=None)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--summary-json", type=Path, default=ROOT / "reports/btrack_btc_typea_guard_apply_summary_v1_latest.json")
    ap.add_argument(
        "--promote-operational",
        action="store_true",
        help="Write directly to btrack_prophecy_score_latest.json (requires approval JSON on disk).",
    )
    ap.add_argument(
        "--approval-json",
        type=Path,
        default=ROOT / "docs/final/artifacts/btrack_btc_typea_guard_human_approval_v1_latest.json",
    )
    args = ap.parse_args(argv)

    if args.promote_operational:
        if not args.approval_json.is_file():
            raise SystemExit(f"missing approval for promote-operational: {args.approval_json}")
        apv = _load(args.approval_json)
        if str(apv.get("decision") or "") != "APPROVED_BTC_TYPEA_GUARD_OPERATIONAL_SCORE":
            raise SystemExit(f"approval decision not approved: {apv.get('decision')}")
        args.out_json = DEFAULT_SCORE

    policy = _load(args.policy_json) if args.policy_json.is_file() else {}
    score_lt = args.score_lt if args.score_lt is not None else float(policy.get("score_lt", 0.12))
    kospi_mode = args.kospi_mode or str(policy.get("kospi_mode", "bull_only"))
    policy_id = str(policy.get("policy_id", "type_a_bull_bear_score12_kospi_bull"))

    score_doc = _load(args.score_json)
    dual_doc = _load(args.dual_json)
    out_doc, changes, summary = apply_typea_guard(
        score_doc, dual_doc, score_lt=score_lt, kospi_mode=kospi_mode, policy_id=policy_id
    )

    out_doc["generated_at_utc"] = _utc_now()
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "inputs": {
            "score_json": str(args.score_json),
            "dual_json": str(args.dual_json),
            "policy_json": str(args.policy_json),
        },
        "policy": {"policy_id": policy_id, "score_lt": score_lt, "kospi_mode": kospi_mode},
        "output_score_json": str(args.out_json),
        "promoted_operational": bool(args.promote_operational),
        **summary,
    }
    args.summary_json.parent.mkdir(parents=True, exist_ok=True)
    args.summary_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"WROTE: {args.out_json.resolve()}")
    print(f"WROTE: {args.summary_json.resolve()}")
    print(f"btc_delta={summary.get('delta_hit_rate')} n_changes={len(changes)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
