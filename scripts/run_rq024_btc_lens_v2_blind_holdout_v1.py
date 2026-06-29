#!/usr/bin/env python3
"""[HYPO] RQ-024 v2 blind holdout — volume + prior intraday range overlay (50/50 chronological)."""
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
DEFAULT_V1_HOLDOUT = ROOT / "reports/rq024_btc_lens_feature_v0_blind_holdout_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/rq024_btc_lens_v2_blind_holdout_v1_latest.json"
SCHEMA = "rq024_btc_lens_v2_blind_holdout_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC)
    ap.add_argument("--train-objective", choices=("accuracy", "margin_vs_bull"), default="margin_vs_bull")
    ap.add_argument("--v1-holdout-json", type=Path, default=DEFAULT_V1_HOLDOUT)
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
    causal = causal_feature_map(btc_csv)

    variants = [
        run_rq024_blind_variant(
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
        ),
        run_rq024_blind_variant(
            slug="rq024_causal_lens_v2",
            train=train,
            test=test,
            km=km,
            bm=bm,
            kf=kf,
            bf=bf,
            causal=causal,
            train_objective=str(args.train_objective),
            overlay_version="v2",
        ),
    ]

    baseline = next((v for v in variants if v.get("slug") == "baseline_nf6_srcdir"), {})
    v2 = next((v for v in variants if v.get("slug") == "rq024_causal_lens_v2"), {})
    b_test = (baseline.get("test_blind") or {}).get("accuracy")
    v2_test = (v2.get("test_blind") or {}).get("accuracy")
    delta_v2 = (
        round(float(v2_test) - float(b_test), 6)
        if isinstance(b_test, (int, float)) and isinstance(v2_test, (int, float))
        else None
    )

    v1_holdout_path = args.v1_holdout_json if args.v1_holdout_json.is_absolute() else ROOT / args.v1_holdout_json
    v1_holdout = _load_json(v1_holdout_path) if v1_holdout_path.is_file() else {}
    v1_cmp = v1_holdout.get("comparison") or {}
    v1_test = None
    for v in v1_holdout.get("variants") or []:
        if v.get("slug") == "rq024_causal_lens_v1":
            v1_test = (v.get("test_blind") or {}).get("accuracy")
            break
    delta_v2_minus_v1 = (
        round(float(v2_test) - float(v1_test), 6)
        if isinstance(v1_test, (int, float)) and isinstance(v2_test, (int, float))
        else None
    )

    out: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "rq_id": "RQ-024",
        "overlay_version": "v2",
        "v2_features_added": ["volume_ratio_5d", "prior_intraday_range"],
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
            "v1_holdout_pointer": str(v1_holdout_path.relative_to(ROOT)).replace("\\", "/")
            if v1_holdout_path.is_relative_to(ROOT)
            else str(v1_holdout_path),
        },
        "variants": variants,
        "comparison": {
            "delta_v2_minus_baseline_blind_test_accuracy": delta_v2,
            "delta_v2_minus_v1_blind_test_accuracy": delta_v2_minus_v1,
            "v2_beats_ceiling_052": (v2.get("test_blind") or {}).get("beats_ceiling_052"),
            "v2_gate_055_pass": (v2.get("test_blind") or {}).get("gate_055_pass"),
            "v1_blind_test_accuracy_pointer": v1_test,
        },
        "dod_v2": {
            "target": "blind_test_accuracy > 0.52 on promotion-legal axis",
            "met": bool((v2.get("test_blind") or {}).get("beats_ceiling_052")),
        },
        "note": "Single 50/50 chronological holdout; v1 numbers from v0 blind holdout artifact for delta only.",
    }

    out_path = args.output if args.output.is_absolute() else ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path.resolve()}")
    for v in variants:
        tb = v.get("test_blind") or {}
        print(f"{v.get('slug')}: blind_test={tb.get('accuracy')} beats_052={tb.get('beats_ceiling_052')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
