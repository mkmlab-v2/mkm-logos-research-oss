#!/usr/bin/env python3
"""[HYPO] RQ-024 multi-split chronological blind holdout (overfitting guard)."""
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
    CEILING_VARIANT,
    causal_feature_map,
    chronological_cut_splits,
    run_rq024_blind_variant,
)
from scripts.run_prophecy_per_date_combo_walkforward_v1 import (  # noqa: E402
    _feature_map,
    _load_json,
    _prior_map,
)

DEFAULT_SCORE = ROOT / "reports/btrack_score_leading_180d_v1_latest.json"
DEFAULT_KOSPI = ROOT / "research/market_data/kospi_daily_external_yf.csv"
DEFAULT_BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
DEFAULT_OUT = ROOT / "reports/rq024_btc_lens_feature_v0_multisplit_v1_latest.json"
SCHEMA = "rq024_btc_lens_feature_v0_multisplit_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _agg_split_tests(splits: list[dict[str, Any]], *, key: str) -> dict[str, Any]:
    accs = [
        float((s.get(key) or {}).get("test_blind", {}).get("accuracy"))
        for s in splits
        if isinstance((s.get(key) or {}).get("test_blind", {}).get("accuracy"), (int, float))
    ]
    if not accs:
        return {"n_splits": 0}
    mean = sum(accs) / len(accs)
    var = sum((x - mean) ** 2 for x in accs) / len(accs)
    beats = sum(
        1
        for s in splits
        if (s.get(key) or {}).get("test_blind", {}).get("beats_ceiling_052")
    )
    gate = sum(
        1 for s in splits if (s.get(key) or {}).get("test_blind", {}).get("gate_055_pass")
    )
    return {
        "n_splits": len(accs),
        "mean_blind_test_accuracy": round(mean, 6),
        "stdev_blind_test_accuracy": round(var**0.5, 6),
        "min_blind_test_accuracy": round(min(accs), 6),
        "max_blind_test_accuracy": round(max(accs), 6),
        "fraction_beats_ceiling_052": round(beats / len(accs), 6),
        "fraction_gate_055_pass": round(gate / len(accs), 6),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC)
    ap.add_argument("--train-objective", choices=("accuracy", "margin_vs_bull"), default="margin_vs_bull")
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
    if len(dates) < 60:
        raise SystemExit("need >= 60 unique dates for multi-split")

    kospi_csv = args.kospi_csv if args.kospi_csv.is_absolute() else ROOT / args.kospi_csv
    btc_csv = args.btc_csv if args.btc_csv.is_absolute() else ROOT / args.btc_csv
    km = _prior_map(kospi_csv) if kospi_csv.is_file() else {}
    bm = _prior_map(btc_csv) if btc_csv.is_file() else {}
    kf = _feature_map(kospi_csv) if kospi_csv.is_file() else {}
    bf = _feature_map(btc_csv) if btc_csv.is_file() else {}
    causal = causal_feature_map(btc_csv)

    splits_out: list[dict[str, Any]] = []
    for sid, train_dates, test_dates in chronological_cut_splits(dates):
        train_set = set(train_dates)
        test_set = set(test_dates)
        train = [r for r in rows if str(r.get("eval_date"))[:10] in train_set]
        test = [r for r in rows if str(r.get("eval_date"))[:10] in test_set]
        baseline = run_rq024_blind_variant(
            slug="baseline_nf6_srcdir",
            train=train,
            test=test,
            km=km,
            bm=bm,
            kf=kf,
            bf=bf,
            causal=causal,
            train_objective=str(args.train_objective),
            overlay_version="none",
        )
        v0 = run_rq024_blind_variant(
            slug="rq024_causal_lens_v0",
            train=train,
            test=test,
            km=km,
            bm=bm,
            kf=kf,
            bf=bf,
            causal=causal,
            train_objective=str(args.train_objective),
            overlay_version="v0",
        )
        v1 = run_rq024_blind_variant(
            slug="rq024_causal_lens_v1",
            train=train,
            test=test,
            km=km,
            bm=bm,
            kf=kf,
            bf=bf,
            causal=causal,
            train_objective=str(args.train_objective),
            overlay_version="v1",
        )
        b_acc = (baseline.get("test_blind") or {}).get("accuracy")
        v0_acc = (v0.get("test_blind") or {}).get("accuracy")
        v1_acc = (v1.get("test_blind") or {}).get("accuracy")
        delta_v0 = (
            round(float(v0_acc) - float(b_acc), 6)
            if isinstance(b_acc, (int, float)) and isinstance(v0_acc, (int, float))
            else None
        )
        delta_v1 = (
            round(float(v1_acc) - float(b_acc), 6)
            if isinstance(b_acc, (int, float)) and isinstance(v1_acc, (int, float))
            else None
        )
        splits_out.append(
            {
                "split_id": sid,
                "train_dates_n": len(train_dates),
                "test_dates_n": len(test_dates),
                "train_date_first": train_dates[0],
                "train_date_last": train_dates[-1],
                "test_date_first": test_dates[0],
                "test_date_last": test_dates[-1],
                "baseline_nf6_srcdir": baseline,
                "rq024_causal_lens_v0": v0,
                "rq024_causal_lens_v1": v1,
                "delta_v0_minus_baseline": delta_v0,
                "delta_v1_minus_baseline": delta_v1,
            }
        )
        print(f"{sid}: v0={v0_acc} v1={v1_acc} baseline={b_acc} d1={delta_v1}")

    baseline_agg = _agg_split_tests(splits_out, key="baseline_nf6_srcdir")
    v0_agg = _agg_split_tests(splits_out, key="rq024_causal_lens_v0")
    v1_agg = _agg_split_tests(splits_out, key="rq024_causal_lens_v1")
    mean_b = baseline_agg.get("mean_blind_test_accuracy")
    mean_v0 = v0_agg.get("mean_blind_test_accuracy")
    mean_v1 = v1_agg.get("mean_blind_test_accuracy")
    delta_mean_v0 = (
        round(float(mean_v0) - float(mean_b), 6)
        if isinstance(mean_b, (int, float)) and isinstance(mean_v0, (int, float))
        else None
    )
    delta_mean_v1 = (
        round(float(mean_v1) - float(mean_b), 6)
        if isinstance(mean_b, (int, float)) and isinstance(mean_v1, (int, float))
        else None
    )

    def _dod_met(mean_v: Any, agg: dict[str, Any]) -> dict[str, Any]:
        return {
            "target": "mean blind test > 0.52 AND fraction_beats_ceiling_052 >= 0.5 across cuts",
            "mean_beats_052": isinstance(mean_v, (int, float)) and float(mean_v) > CEILING_BASELINE_ACCURACY,
            "fraction_beats_052_pass": (agg.get("fraction_beats_ceiling_052") or 0) >= 0.5,
            "met": bool(
                isinstance(mean_v, (int, float))
                and float(mean_v) > CEILING_BASELINE_ACCURACY
                and (agg.get("fraction_beats_ceiling_052") or 0) >= 0.5
            ),
        }

    out: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "rq_id": "RQ-024",
        "promotion_axis": "no_expanded_prior",
        "ceiling_reference": {
            "variant": CEILING_VARIANT,
            "full_wf_best_accuracy": CEILING_BASELINE_ACCURACY,
        },
        "inputs": {
            "score_json": str(score_path.relative_to(ROOT)).replace("\\", "/")
            if score_path.is_relative_to(ROOT)
            else str(score_path),
            "train_objective": args.train_objective,
            "split_dates_total": len(dates),
            "n_splits": len(splits_out),
        },
        "splits": splits_out,
        "aggregate": {
            "baseline_nf6_srcdir": baseline_agg,
            "rq024_causal_lens_v0": v0_agg,
            "rq024_causal_lens_v1": v1_agg,
            "delta_mean_v0_minus_baseline": delta_mean_v0,
            "delta_mean_v1_minus_baseline": delta_mean_v1,
        },
        "dod_multisplit": _dod_met(mean_v0, v0_agg),
        "dod_multisplit_v1": _dod_met(mean_v1, v1_agg),
    }
    out_path = args.output if args.output.is_absolute() else ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path.resolve()}")
    print(
        f"multisplit mean_v0={mean_v0} mean_v1={mean_v1} "
        f"v0_dod={out['dod_multisplit']['met']} v1_dod={out['dod_multisplit_v1']['met']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
