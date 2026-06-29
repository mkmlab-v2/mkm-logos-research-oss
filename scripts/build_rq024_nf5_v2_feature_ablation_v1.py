#!/usr/bin/env python3
"""[HYPO] RQ-024 nf5 v2 feature ablation — volume_ratio_5d vs prior_intraday_range."""
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
    acc_with_causal_overlay_v1,
    acc_with_causal_overlay_v2,
    best_causal_weights_v2_on_train,
    causal_feature_map,
    fit_baseline_nf6_on_train,
)
from scripts.run_prophecy_per_date_combo_walkforward_v1 import (  # noqa: E402
    _blocked_walkforward_folds,
    _feature_map,
    _load_json,
    _prior_map,
)

DEFAULT_SCORE = ROOT / "reports/btrack_score_leading_180d_v1_latest.json"
DEFAULT_KOSPI = ROOT / "research/market_data/kospi_daily_external_yf.csv"
DEFAULT_BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
DEFAULT_OUT = ROOT / "reports/rq024_nf5_v2_feature_ablation_v1_latest.json"
SCHEMA = "rq024_nf5_v2_feature_ablation_v1"
PINNED_N_FOLDS = 5
V2_FEATURE_INDEX = {"volume_ratio_5d": 5, "prior_intraday_range": 6}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _mean_acc(folds: list[dict[str, Any]]) -> float:
    accs = [float(f["test_accuracy"]) for f in folds if "test_accuracy" in f]
    return round(sum(accs) / len(accs), 6) if accs else 0.0


def _zero_weight(w: tuple[float, ...], idx: int) -> tuple[float, ...]:
    parts = list(w)
    if 0 <= idx < len(parts):
        parts[idx] = 0.0
    return tuple(parts)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC)
    ap.add_argument("--train-objective", choices=("accuracy", "margin_vs_bull"), default="margin_vs_bull")
    ap.add_argument("--n-folds", type=int, default=PINNED_N_FOLDS)
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
    nf = int(args.n_folds)
    if nf < 2 or nf > len(dates):
        raise SystemExit(f"n_folds={nf} invalid for {len(dates)} dates")

    kospi_csv = args.kospi_csv if args.kospi_csv.is_absolute() else ROOT / args.kospi_csv
    btc_csv = args.btc_csv if args.btc_csv.is_absolute() else ROOT / args.btc_csv
    km = _prior_map(kospi_csv) if kospi_csv.is_file() else {}
    bm = _prior_map(btc_csv) if btc_csv.is_file() else {}
    kf = _feature_map(kospi_csv) if kospi_csv.is_file() else {}
    bf = _feature_map(btc_csv) if btc_csv.is_file() else {}
    causal = causal_feature_map(btc_csv)

    variants: dict[str, list[dict[str, Any]]] = {
        "v1_full": [],
        "v2_full": [],
        "v2_ablate_no_volume_ratio_5d": [],
        "v2_ablate_no_prior_intraday_range": [],
    }

    for fi, (train_dates, test_dates) in enumerate(_blocked_walkforward_folds(dates, nf)):
        train_set, test_set = set(train_dates), set(test_dates)
        train = [r for r in rows if str(r.get("eval_date"))[:10] in train_set]
        test = [r for r in rows if str(r.get("eval_date"))[:10] in test_set]
        if not train or not test:
            continue

        params, _ = fit_baseline_nf6_on_train(train, km, bm, kf, bf, train_objective=args.train_objective)
        if params is None:
            continue

        from scripts.rq024_btc_lens_feature_v0_lib import best_causal_weights_v1_on_train

        w_v1, _ = best_causal_weights_v1_on_train(
            train,
            params,
            km,
            bm,
            kf,
            bf,
            causal,
            include_source_direction_signal=True,
            train_objective=args.train_objective,
        )
        w_v2, _ = best_causal_weights_v2_on_train(
            train,
            params,
            km,
            bm,
            kf,
            bf,
            causal,
            include_source_direction_signal=True,
            train_objective=args.train_objective,
        )
        w_no_vol = _zero_weight(w_v2, V2_FEATURE_INDEX["volume_ratio_5d"])
        w_no_pir = _zero_weight(w_v2, V2_FEATURE_INDEX["prior_intraday_range"])

        def _eval_test(weights: tuple[float, ...], version: str) -> dict[str, Any]:
            if version == "v1":
                acc, hits = acc_with_causal_overlay_v1(
                    test,
                    params,
                    km,
                    bm,
                    kf,
                    bf,
                    causal,
                    include_source_direction_signal=True,
                    causal_weights=weights,
                )
            else:
                acc, hits = acc_with_causal_overlay_v2(
                    test,
                    params,
                    km,
                    bm,
                    kf,
                    bf,
                    causal,
                    include_source_direction_signal=True,
                    causal_weights=weights,
                )
            return {
                "fold_index": fi,
                "test_accuracy": round(acc, 6),
                "test_hits": hits,
                "test_n": len(test),
                "gate_055_pass": acc >= 0.55,
                "beats_ceiling_052": acc > CEILING_BASELINE_ACCURACY,
            }

        variants["v1_full"].append(_eval_test(w_v1, "v1"))
        variants["v2_full"].append(_eval_test(w_v2, "v2"))
        variants["v2_ablate_no_volume_ratio_5d"].append(_eval_test(w_no_vol, "v2"))
        variants["v2_ablate_no_prior_intraday_range"].append(_eval_test(w_no_pir, "v2"))

    summary = {
        slug: {
            "mean_test_accuracy": _mean_acc(folds),
            "n_folds": len(folds),
            "gate_055_pass": _mean_acc(folds) >= 0.55,
        }
        for slug, folds in variants.items()
    }
    v1_mean = float(summary["v1_full"]["mean_test_accuracy"])
    v2_mean = float(summary["v2_full"]["mean_test_accuracy"])

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "rq_id": "RQ-024",
        "v2_features": ["volume_ratio_5d", "prior_intraday_range"],
        "pinned_config": {"n_folds": nf, "train_objective": args.train_objective},
        "summary": summary,
        "delta_vs_v1": {
            "v2_full_minus_v1": round(v2_mean - v1_mean, 6),
            "v2_no_vol_minus_v1": round(
                float(summary["v2_ablate_no_volume_ratio_5d"]["mean_test_accuracy"]) - v1_mean, 6
            ),
            "v2_no_pir_minus_v1": round(
                float(summary["v2_ablate_no_prior_intraday_range"]["mean_test_accuracy"]) - v1_mean, 6
            ),
        },
        "interpretation": {
            "v2_underperforms_v1": v2_mean < v1_mean,
            "likely_harmful_feature": (
                "volume_ratio_5d"
                if float(summary["v2_ablate_no_volume_ratio_5d"]["mean_test_accuracy"]) > v2_mean
                else (
                    "prior_intraday_range"
                    if float(summary["v2_ablate_no_prior_intraday_range"]["mean_test_accuracy"]) > v2_mean
                    else "inconclusive"
                )
            ),
            "track_a_promotion": False,
        },
        "folds": variants,
        "track_wall": {
            "track_a_auto_merge": False,
            "oracle_promotion": False,
            "live_trading": False,
        },
    }
    out_path = args.output if args.output.is_absolute() else ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path} v1={v1_mean} v2={v2_mean} harm={payload['interpretation']['likely_harmful_feature']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
