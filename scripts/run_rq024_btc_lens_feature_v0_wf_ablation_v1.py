#!/usr/bin/env python3
"""[HYPO] RQ-024 blocked walk-forward ablation: baseline nf6 vs causal lens v0 (BTC)."""
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

from scripts.rq024_btc_lens_feature_v0_lib import (  # noqa: E402
    CEILING_BASELINE_ACCURACY,
    blocked_walkforward_eval,
    causal_feature_map,
)
from scripts.run_prophecy_per_date_combo_walkforward_v1 import (  # noqa: E402
    _feature_map,
    _load_json,
    _prior_map,
)

DEFAULT_SCORE = ROOT / "reports/btrack_score_leading_180d_v1_latest.json"
DEFAULT_KOSPI = ROOT / "research/market_data/kospi_daily_external_yf.csv"
DEFAULT_BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
DEFAULT_OUT = ROOT / "reports/rq024_btc_lens_feature_v0_wf_ablation_v1_latest.json"
SCHEMA = "rq024_btc_lens_feature_v0_wf_ablation_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC)
    ap.add_argument("--train-objective", choices=("accuracy", "margin_vs_bull"), default="margin_vs_bull")
    ap.add_argument("--fold-counts", type=str, default="4,5,6,7", help="Comma-separated n-folds values")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    score_path = args.score_json if args.score_json.is_absolute() else ROOT / args.score_json
    doc = _load_json(score_path)
    if not doc or not isinstance(doc.get("rows"), list):
        raise SystemExit(f"invalid score json: {score_path}")

    rows = sorted(
        [r for r in doc["rows"] if isinstance(r, dict) and str(r.get("instrument") or "").strip().lower() == "btc"],
        key=lambda r: str(r.get("eval_date")),
    )
    dates = sorted({str(r.get("eval_date"))[:10] for r in rows})
    if len(dates) < 40:
        raise SystemExit("need >= 40 unique dates for wf ablation")

    kospi_csv = args.kospi_csv if args.kospi_csv.is_absolute() else ROOT / args.kospi_csv
    btc_csv = args.btc_csv if args.btc_csv.is_absolute() else ROOT / args.btc_csv
    km = _prior_map(kospi_csv) if kospi_csv.is_file() else {}
    bm = _prior_map(btc_csv) if btc_csv.is_file() else {}
    kf = _feature_map(kospi_csv) if kospi_csv.is_file() else {}
    bf = _feature_map(btc_csv) if btc_csv.is_file() else {}
    causal = causal_feature_map(btc_csv)

    fold_counts = [int(x.strip()) for x in str(args.fold_counts).split(",") if x.strip()]
    variants: list[dict[str, Any]] = []
    for nf in fold_counts:
        if nf < 2 or nf > len(dates):
            continue
        result = blocked_walkforward_eval(
            rows,
            dates,
            n_folds=nf,
            km=km,
            bm=bm,
            kf=kf,
            bf=bf,
            causal=causal,
            train_objective=str(args.train_objective),
        )
        slug = f"nf{nf}_{args.train_objective}_srcdir_rq024_v0_v1"
        b_agg = result["baseline_nf6_srcdir"]["aggregate"]
        v0_agg = result["rq024_causal_lens_v0"]["aggregate"]
        v1_agg = result["rq024_causal_lens_v1"]["aggregate"]
        row = {
            "slug": slug,
            "n_folds": nf,
            "train_objective": args.train_objective,
            "baseline_aggregate": b_agg,
            "v0_aggregate": v0_agg,
            "v1_aggregate": v1_agg,
            "delta_mean_v0_minus_baseline": (
                round(float(v0_agg["mean_test_accuracy"]) - float(b_agg["mean_test_accuracy"]), 6)
                if b_agg.get("mean_test_accuracy") is not None and v0_agg.get("mean_test_accuracy") is not None
                else None
            ),
            "delta_mean_v1_minus_baseline": (
                round(float(v1_agg["mean_test_accuracy"]) - float(b_agg["mean_test_accuracy"]), 6)
                if b_agg.get("mean_test_accuracy") is not None and v1_agg.get("mean_test_accuracy") is not None
                else None
            ),
            "delta_mean_v1_minus_v0": (
                round(float(v1_agg["mean_test_accuracy"]) - float(v0_agg["mean_test_accuracy"]), 6)
                if v0_agg.get("mean_test_accuracy") is not None and v1_agg.get("mean_test_accuracy") is not None
                else None
            ),
            "detail": result,
        }
        variants.append(row)
        print(
            f"{slug}: baseline_mean={b_agg.get('mean_test_accuracy')} "
            f"v0_mean={v0_agg.get('mean_test_accuracy')} v1_mean={v1_agg.get('mean_test_accuracy')} "
            f"v1_frac_052={v1_agg.get('fraction_test_beats_ceiling_052')}"
        )

    v0_means = [
        float(v["v0_aggregate"]["mean_test_accuracy"])
        for v in variants
        if isinstance(v.get("v0_aggregate", {}).get("mean_test_accuracy"), (int, float))
    ]
    v1_means = [
        float(v["v1_aggregate"]["mean_test_accuracy"])
        for v in variants
        if isinstance(v.get("v1_aggregate", {}).get("mean_test_accuracy"), (int, float))
    ]
    best_v0 = max(
        variants, key=lambda x: float((x.get("v0_aggregate") or {}).get("mean_test_accuracy") or -1), default=None
    )
    best_v1 = max(
        variants, key=lambda x: float((x.get("v1_aggregate") or {}).get("mean_test_accuracy") or -1), default=None
    )
    overall_v0_mean = sum(v0_means) / len(v0_means) if v0_means else None
    overall_v1_mean = sum(v1_means) / len(v1_means) if v1_means else None

    out: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "rq_id": "RQ-024",
        "promotion_axis": "no_expanded_prior",
        "expanded_prior_excluded": True,
        "ceiling_reference_accuracy": CEILING_BASELINE_ACCURACY,
        "inputs": {
            "score_json": str(score_path.relative_to(ROOT)).replace("\\", "/")
            if score_path.is_relative_to(ROOT)
            else str(score_path),
            "train_objective": args.train_objective,
            "fold_counts": fold_counts,
            "split_dates_total": len(dates),
        },
        "variants": variants,
        "best_v0_by_mean_test_accuracy": best_v0,
        "best_v1_by_mean_test_accuracy": best_v1,
        "overall_v0_mean_across_nf_configs": round(overall_v0_mean, 6) if overall_v0_mean is not None else None,
        "overall_v1_mean_across_nf_configs": round(overall_v1_mean, 6) if overall_v1_mean is not None else None,
        "dod_wf_ablation": {
            "target": "v0/v1 mean_test_accuracy > 0.52 on best nf config; gate 0.55 still out of scope for promotion",
            "best_v0_mean_beats_052": bool(
                best_v0
                and isinstance((best_v0.get("v0_aggregate") or {}).get("mean_test_accuracy"), (int, float))
                and float((best_v0["v0_aggregate"])["mean_test_accuracy"]) > CEILING_BASELINE_ACCURACY
            ),
            "best_v1_mean_beats_052": bool(
                best_v1
                and isinstance((best_v1.get("v1_aggregate") or {}).get("mean_test_accuracy"), (int, float))
                and float((best_v1["v1_aggregate"])["mean_test_accuracy"]) > CEILING_BASELINE_ACCURACY
            ),
            "any_nf_v0_gate_055_all_folds": any(
                (v.get("v0_aggregate") or {}).get("gate_055_pass_all_folds") for v in variants
            ),
            "any_nf_v1_gate_055_all_folds": any(
                (v.get("v1_aggregate") or {}).get("gate_055_pass_all_folds") for v in variants
            ),
        },
    }
    out_path = args.output if args.output.is_absolute() else ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
