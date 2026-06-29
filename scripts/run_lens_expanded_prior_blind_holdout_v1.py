#!/usr/bin/env python3
"""[HYPO] Single chronological blind holdout: fit lens grid on first half dates, score second half (BTC leg).

Compares baseline 7-param, source-direction, and expanded-prior grids on the same split.
Research-only — expanded-prior lane is not a Track A promotion axis.
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

from scripts.run_prophecy_per_date_combo_walkforward_v1 import (  # noqa: E402
    _acc,
    _best_params_on_train,
    _feature_map,
    _load_json,
    _params_to_dict,
    _prior_map,
)

DEFAULT_SCORE = ROOT / "reports/btrack_score_leading_180d_v1_latest.json"
DEFAULT_KOSPI = ROOT / "research/market_data/kospi_daily_external_yf.csv"
DEFAULT_BTC = ROOT / "research/market_data/btc_daily_external_yf.csv"
DEFAULT_OUT = ROOT / "reports/lens_expanded_prior_blind_holdout_v1_latest.json"
SCHEMA = "lens_expanded_prior_blind_holdout_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _bull_frac(rows: list[dict[str, Any]]) -> float:
    if not rows:
        return 0.0
    return sum(1 for r in rows if str(r.get("actual_direction") or "").strip().lower() == "bull") / len(rows)


def _run_variant(
    *,
    slug: str,
    train: list[dict[str, Any]],
    test: list[dict[str, Any]],
    km: dict[str, float],
    bm: dict[str, float],
    kf: dict[str, dict[str, float]],
    bf: dict[str, dict[str, float]],
    include_source_direction_signal: bool,
    include_expanded_prior_features: bool,
    train_objective: str,
) -> dict[str, Any]:
    fitted = _best_params_on_train(
        train,
        km,
        bm,
        kf,
        bf,
        train_objective=train_objective,
        include_source_direction_signal=include_source_direction_signal,
        include_expanded_prior_features=include_expanded_prior_features,
    )
    if fitted is None:
        return {"slug": slug, "error": "no_train_candidate"}
    train_acc_fit, params = fitted
    train_acc, train_hit = _acc(
        train,
        params,
        km,
        bm,
        kf,
        bf,
        include_source_direction_signal=include_source_direction_signal,
        include_expanded_prior_features=include_expanded_prior_features,
    )
    test_acc, test_hit = _acc(
        test,
        params,
        km,
        bm,
        kf,
        bf,
        include_source_direction_signal=include_source_direction_signal,
        include_expanded_prior_features=include_expanded_prior_features,
    )
    bull_train = _bull_frac(train)
    bull_test = _bull_frac(test)
    return {
        "slug": slug,
        "include_source_direction_signal": include_source_direction_signal,
        "include_expanded_prior_features": include_expanded_prior_features,
        "best_params_from_train": _params_to_dict(
            params,
            include_source_direction_signal=include_source_direction_signal,
            include_expanded_prior_features=include_expanded_prior_features,
        ),
        "train": {
            "accuracy": round(train_acc, 6),
            "hits": train_hit,
            "n": len(train),
            "always_bull_control": round(bull_train, 6),
            "margin_vs_bull": round(train_acc - bull_train, 6),
        },
        "test_blind": {
            "accuracy": round(test_acc, 6),
            "hits": test_hit,
            "n": len(test),
            "always_bull_control": round(bull_test, 6),
            "margin_vs_bull": round(test_acc - bull_test, 6),
            "beats_always_bull": test_acc > bull_test,
            "gate_055_pass": test_acc >= 0.55,
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC)
    ap.add_argument("--target-instrument", choices=("btc", "kospi", "all"), default="btc")
    ap.add_argument("--train-objective", choices=("accuracy", "margin_vs_bull"), default="margin_vs_bull")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    score_path = args.score_json if args.score_json.is_absolute() else ROOT / args.score_json
    doc = _load_json(score_path)
    if not doc or not isinstance(doc.get("rows"), list):
        raise SystemExit(f"invalid score json: {score_path}")

    all_rows = sorted(
        [r for r in doc["rows"] if isinstance(r, dict)],
        key=lambda r: (str(r.get("eval_date")), str(r.get("instrument"))),
    )
    if args.target_instrument == "all":
        rows = all_rows
    else:
        rows = [r for r in all_rows if str(r.get("instrument") or "").strip().lower() == args.target_instrument]
    if not rows:
        raise SystemExit(f"no rows for target {args.target_instrument}")

    dates = sorted({str(r.get("eval_date"))[:10] for r in rows})
    half = max(1, len(dates) // 2)
    train_dates = set(dates[:half])
    test_dates = set(dates[half:])
    train = [r for r in rows if str(r.get("eval_date"))[:10] in train_dates]
    test = [r for r in rows if str(r.get("eval_date"))[:10] in test_dates]

    kospi_csv = args.kospi_csv if args.kospi_csv.is_absolute() else ROOT / args.kospi_csv
    btc_csv = args.btc_csv if args.btc_csv.is_absolute() else ROOT / args.btc_csv
    km = _prior_map(kospi_csv) if kospi_csv.is_file() else {}
    bm = _prior_map(btc_csv) if btc_csv.is_file() else {}
    kf = _feature_map(kospi_csv) if kospi_csv.is_file() else {}
    bf = _feature_map(btc_csv) if btc_csv.is_file() else {}

    variants_spec = [
        ("baseline_7param", False, False),
        ("source_direction", True, False),
        ("expanded_prior_srcdir", True, True),
    ]
    variants: list[dict[str, Any]] = []
    for slug, src, exp in variants_spec:
        variants.append(
            _run_variant(
                slug=slug,
                train=train,
                test=test,
                km=km,
                bm=bm,
                kf=kf,
                bf=bf,
                include_source_direction_signal=src,
                include_expanded_prior_features=exp,
                train_objective=str(args.train_objective),
            )
        )
        v = variants[-1]
        print(
            f"{slug}: blind_test={v.get('test_blind', {}).get('accuracy')} "
            f"beats_bull={v.get('test_blind', {}).get('beats_always_bull')}"
        )

    baseline = next((v for v in variants if v.get("slug") == "baseline_7param"), {})
    expanded = next((v for v in variants if v.get("slug") == "expanded_prior_srcdir"), {})
    b_test = (baseline.get("test_blind") or {}).get("accuracy")
    e_test = (expanded.get("test_blind") or {}).get("accuracy")
    delta = round(float(e_test) - float(b_test), 6) if isinstance(b_test, (int, float)) and isinstance(e_test, (int, float)) else None

    out = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "inputs": {
            "score_json": str(score_path.relative_to(ROOT)).replace("\\", "/") if score_path.is_relative_to(ROOT) else str(score_path),
            "target_instrument": args.target_instrument,
            "train_objective": args.train_objective,
            "split_dates_total": len(dates),
            "train_dates_n": len(train_dates),
            "test_dates_n": len(test_dates),
            "train_date_first": dates[0] if dates else None,
            "train_date_last": dates[half - 1] if half else None,
            "test_date_first": dates[half] if half < len(dates) else None,
            "test_date_last": dates[-1] if dates else None,
        },
        "variants": variants,
        "comparison": {
            "delta_expanded_minus_baseline_blind_test_accuracy": delta,
            "expanded_blind_gate_055_pass": (expanded.get("test_blind") or {}).get("gate_055_pass"),
            "promotion_axis": "forbidden_expanded_prior_per_btrack_playbook",
        },
        "note": "Single 50/50 chronological holdout; params fit on train only, blind test on latter half.",
    }
    out_path = args.output if args.output.is_absolute() else ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
