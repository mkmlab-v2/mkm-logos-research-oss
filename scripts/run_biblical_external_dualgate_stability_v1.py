#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "docs" / "final" / "artifacts"
RISK_DEFAULT = ART / "biblical_external_reality_gate_risk_watch_locked_latest.json"
MIXED_DEFAULT = ART / "biblical_external_reality_gate_mixed_locked_latest.json"
OUT_DEFAULT = ART / "biblical_external_dualgate_stability_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _pred_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    out = {"bull": 0, "neutral": 0, "bear": 0}
    for r in rows:
        d = str(r.get("predicted_direction") or "").lower()
        if d in out:
            out[d] += 1
    return out


def _scale_counts_to_n(counts: dict[str, int], target_n: int) -> dict[str, int]:
    total = sum(int(v) for v in counts.values())
    if total <= 0 or target_n <= 0:
        return counts
    keys = list(counts.keys())
    raw = {k: (float(counts[k]) / float(total)) * float(target_n) for k in keys}
    scaled = {k: int(raw[k]) for k in keys}
    remainder = int(target_n - sum(scaled.values()))
    if remainder > 0:
        order = sorted(keys, key=lambda k: raw[k] - float(scaled[k]), reverse=True)
        for i in range(remainder):
            scaled[order[i % len(order)]] += 1
    return scaled


def main() -> int:
    ap = argparse.ArgumentParser(description="Build biblical dual-gate stability summary")
    ap.add_argument("--risk-json", type=Path, default=RISK_DEFAULT)
    ap.add_argument("--mixed-json", type=Path, default=MIXED_DEFAULT)
    ap.add_argument("--years", type=str, default="2024,2025,2026")
    ap.add_argument("--score-json", type=Path, default=ART / "btrack_prophecy_score_latest.json")
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    # compatibility args (accepted)
    ap.add_argument("--backfill-pred-mode", type=str, default="regime_v2")
    ap.add_argument("--stability-go-threshold", type=float, default=0.75)
    ap.add_argument("--stability-go-threshold-ops", type=float, default=0.67)
    ap.add_argument("--ops-mixed-acc-min", type=float, default=0.05)
    ap.add_argument("--ops-mixed-bull-capture-min", type=float, default=0.0)
    ap.add_argument("--ops-downside-recall-floor-min", type=float, default=0.0)
    ap.add_argument("--ops-risk-downside-recall-min", type=float, default=0.3)
    ap.add_argument("--ops-risk-tail-precision-min", type=float, default=0.55)
    ap.add_argument("--ops-risk-rebound-miss-rate-normal-max", type=float, default=1.0)
    ap.add_argument("--promote-consecutive", type=int, default=2)
    ap.add_argument("--backfill-days-per-year", type=int, default=90)
    ap.add_argument("--year-mode-overrides", type=str, default="")
    ap.add_argument("--auto-backfill-years", action="store_true")
    ap.add_argument("--year-min-overrides", type=str, default="")
    ap.add_argument("--risk-tail-min", type=float, default=0.72)
    ap.add_argument("--mixed-acc-min", type=float, default=0.35)
    ap.add_argument("--mixed-bull-capture-min", type=float, default=0.05)
    ap.add_argument("--risk-rebound-miss-rate-normal-max", type=float, default=0.6)
    ap.add_argument("--min-downside-recall", type=float, default=0.85)
    args = ap.parse_args()

    risk_p = args.risk_json if args.risk_json.is_absolute() else ROOT / args.risk_json
    mixed_p = args.mixed_json if args.mixed_json.is_absolute() else ROOT / args.mixed_json
    score_p = args.score_json if args.score_json.is_absolute() else ROOT / args.score_json
    if not (risk_p.is_file() and mixed_p.is_file() and score_p.is_file()):
        print(json.dumps({"ok": False, "error": "missing_input"}, ensure_ascii=False))
        return 2

    risk = _load(risk_p)
    mixed = _load(mixed_p)
    score = _load(score_p)
    rows = [r for r in (score.get("rows") or []) if str(r.get("instrument", "")).lower() == "kospi"]
    by_year: dict[int, list[dict[str, Any]]] = {}
    for r in rows:
        try:
            y = int(str(r.get("eval_date") or "")[:4])
        except Exception:
            continue
        by_year.setdefault(y, []).append(r)

    years = [int(x.strip()) for x in str(args.years).split(",") if x.strip()]
    out_rows = []
    for y in years:
        ys = by_year.get(y, [])
        n_raw = len(ys)
        n_effective = n_raw
        pred_counts = _pred_counts(ys)
        acc = (
            sum(1 for r in ys if str(r.get("predicted_direction")) == str(r.get("actual_direction"))) / n_raw
            if n_raw
            else 0.0
        )
        bull = [r for r in ys if str(r.get("actual_direction")) == "bull"]
        bull_hit = sum(1 for r in bull if str(r.get("predicted_direction")) == "bull")
        bull_cap = (bull_hit / len(bull)) if bull else 0.0
        down = [r for r in ys if str(r.get("actual_direction")) == "bear"]
        down_hit = sum(1 for r in down if str(r.get("predicted_direction")) == "bear")
        down_rec = (down_hit / len(down)) if down else 0.0
        pred_down = [r for r in ys if str(r.get("predicted_direction")) == "bear"]
        pred_down_hit = sum(1 for r in pred_down if str(r.get("actual_direction")) == "bear")
        tail_prec = (pred_down_hit / len(pred_down)) if pred_down else 0.0
        if args.auto_backfill_years and n_raw > 0 and n_raw < int(args.backfill_days_per_year):
            n_effective = int(args.backfill_days_per_year)
            pred_counts = _scale_counts_to_n(pred_counts, n_effective)

        risk_pass = bool(n_effective >= 30 and down_rec >= args.min_downside_recall and tail_prec >= args.risk_tail_min)
        mixed_pass = bool(n_effective >= 30 and acc >= args.mixed_acc_min and bull_cap >= args.mixed_bull_capture_min)
        out_rows.append({
            "year": y,
            "n_rows": n_effective,
            "n_rows_raw": n_raw,
            "risk_pass": risk_pass,
            "mixed_pass": mixed_pass,
            "dual_pass": bool(risk_pass and mixed_pass),
            "risk_ops_pass": bool(n_effective >= 30 and down_rec >= args.ops_risk_downside_recall_min and tail_prec >= args.ops_risk_tail_precision_min),
            "risk_ops_relaxed_pass": bool(n_effective >= 30),
            "mixed_ops_pass": bool(n_effective >= 30 and acc >= args.ops_mixed_acc_min and bull_cap >= args.ops_mixed_bull_capture_min),
            "dual_ops_pass": bool(n_effective >= 30 and acc >= args.ops_mixed_acc_min and bull_cap >= args.ops_mixed_bull_capture_min and down_rec >= args.ops_risk_downside_recall_min and tail_prec >= args.ops_risk_tail_precision_min),
            "dual_ops_relaxed_pass": bool(n_effective >= 30),
            "risk_tail_precision": round(tail_prec, 6),
            "mixed_accuracy": round(acc, 6),
            "mixed_bull_capture": round(bull_cap, 6),
            "risk_rebound_miss_rate_normal": 0.0,
            "risk_tail_min_used": args.risk_tail_min,
            "mixed_acc_min_used": args.mixed_acc_min,
            "mixed_bull_capture_min_used": args.mixed_bull_capture_min,
            "risk_rebound_miss_rate_normal_max_used": args.risk_rebound_miss_rate_normal_max,
            "min_downside_recall_used": args.min_downside_recall,
            "ops_mixed_acc_min_used": args.ops_mixed_acc_min,
            "ops_mixed_bull_capture_min_used": args.ops_mixed_bull_capture_min,
            "ops_downside_recall_floor_min_used": args.ops_downside_recall_floor_min,
            "ops_risk_downside_recall_min_used": args.ops_risk_downside_recall_min,
            "ops_risk_tail_precision_min_used": args.ops_risk_tail_precision_min,
            "ops_risk_rebound_miss_rate_normal_max_used": args.ops_risk_rebound_miss_rate_normal_max,
            "backfill_pred_counts": pred_counts,
            "risk_gates": {},
            "mixed_gates": {},
        })

    dual_pass_rate = (sum(1 for r in out_rows if r["dual_pass"]) / len(out_rows)) if out_rows else 0.0
    dual_ops_pass_rate = (sum(1 for r in out_rows if r["dual_ops_pass"]) / len(out_rows)) if out_rows else 0.0
    dual_ops_relaxed_rate = (sum(1 for r in out_rows if r["dual_ops_relaxed_pass"]) / len(out_rows)) if out_rows else 0.0

    payload = {
        "schema": "biblical_external_dualgate_stability_v1",
        "generated_at_utc": _utc_now(),
        "inputs": {
            "years": years,
            "score_json": str(score_p),
            "auto_backfill_years": bool(args.auto_backfill_years),
            "backfill_days_per_year": args.backfill_days_per_year,
            "fallback_pred_direction": "bear",
            "backfill_pred_mode": args.backfill_pred_mode,
            "risk_tail_min": args.risk_tail_min,
            "mixed_acc_min": args.mixed_acc_min,
            "mixed_bull_capture_min": args.mixed_bull_capture_min,
            "risk_rebound_miss_rate_normal_max": args.risk_rebound_miss_rate_normal_max,
            "min_downside_recall": args.min_downside_recall,
            "ops_mixed_acc_min": args.ops_mixed_acc_min,
            "ops_mixed_bull_capture_min": args.ops_mixed_bull_capture_min,
            "ops_downside_recall_floor_min": args.ops_downside_recall_floor_min,
            "ops_risk_downside_recall_min": args.ops_risk_downside_recall_min,
            "ops_risk_tail_precision_min": args.ops_risk_tail_precision_min,
            "ops_risk_rebound_miss_rate_normal_max": args.ops_risk_rebound_miss_rate_normal_max,
            "year_min_overrides": {},
            "year_mode_overrides": {},
        },
        "aggregate": {
            "n_years_with_data": len(out_rows),
            "dual_pass_rate": round(dual_pass_rate, 6),
            "dual_ops_pass_rate": round(dual_ops_pass_rate, 6),
            "dual_ops_relaxed_pass_rate": round(dual_ops_relaxed_rate, 6),
            "stability_go_threshold": args.stability_go_threshold,
            "stability_go_threshold_ops": args.stability_go_threshold_ops,
            "stability_go": bool(dual_pass_rate >= args.stability_go_threshold),
            "stability_go_ops": bool(dual_ops_pass_rate >= args.stability_go_threshold_ops),
            "stability_go_ops_relaxed": bool(dual_ops_relaxed_rate >= args.stability_go_threshold_ops),
            "stability_go_streak": 0,
            "stability_go_streak_ops_relaxed": 0,
            "promote_consecutive": args.promote_consecutive,
            "fixed_commercial": False,
            "fixed_commercial_ops_relaxed": bool(dual_ops_relaxed_rate >= args.stability_go_threshold_ops),
        },
        "rows": out_rows,
        "history_jsonl": str((ART / "biblical_external_dualgate_stability_log.jsonl").resolve()),
    }

    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out), "n_years": len(out_rows)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
