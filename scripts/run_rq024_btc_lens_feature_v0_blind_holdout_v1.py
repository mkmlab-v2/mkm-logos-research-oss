#!/usr/bin/env python3
"""[HYPO] RQ-024 B-track: BTC lens causal feature v0 blind holdout (50/50 chronological).

Promotion-legal axis: no expanded-prior. Compares nf6 baseline vs causal OHLC overlay v0.
Research-only — beating 0.52 on blind test is the v0 DoD, not combined 0.55 / Track A.
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
DEFAULT_OUT = ROOT / "reports/rq024_btc_lens_feature_v0_blind_holdout_v1_latest.json"
SCHEMA = "rq024_btc_lens_feature_v0_blind_holdout_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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
    if not rows:
        raise SystemExit("no btc rows in score json")

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
        ),
        run_rq024_blind_variant(
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
        ),
    ]

    baseline = next((v for v in variants if v.get("slug") == "baseline_nf6_srcdir"), {})
    v0 = next((v for v in variants if v.get("slug") == "rq024_causal_lens_v0"), {})
    v1 = next((v for v in variants if v.get("slug") == "rq024_causal_lens_v1"), {})
    b_test = (baseline.get("test_blind") or {}).get("accuracy")
    v0_test = (v0.get("test_blind") or {}).get("accuracy")
    v1_test = (v1.get("test_blind") or {}).get("accuracy")
    delta_v0 = (
        round(float(v0_test) - float(b_test), 6)
        if isinstance(b_test, (int, float)) and isinstance(v0_test, (int, float))
        else None
    )
    delta_v1 = (
        round(float(v1_test) - float(b_test), 6)
        if isinstance(b_test, (int, float)) and isinstance(v1_test, (int, float))
        else None
    )

    out: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "rq_id": "RQ-024",
        "lane": "B_primary_btc_lens_feature_v0",
        "promotion_axis": "no_expanded_prior",
        "ceiling_reference": {
            "variant": CEILING_VARIANT,
            "full_wf_best_accuracy": CEILING_BASELINE_ACCURACY,
            "source": "reports/baseline_lens_wf_ablation_v1_latest.json",
        },
        "inputs": {
            "score_json": str(score_path.relative_to(ROOT)).replace("\\", "/")
            if score_path.is_relative_to(ROOT)
            else str(score_path),
            "train_objective": args.train_objective,
            "split_dates_total": len(dates),
            "train_dates_n": len(train_dates),
            "test_dates_n": len(test_dates),
            "causal_feature_dates_n": len(causal),
        },
        "variants": variants,
        "comparison": {
            "delta_v0_minus_baseline_blind_test_accuracy": delta_v0,
            "delta_v1_minus_baseline_blind_test_accuracy": delta_v1,
            "v0_beats_ceiling_052": (v0.get("test_blind") or {}).get("beats_ceiling_052"),
            "v1_beats_ceiling_052": (v1.get("test_blind") or {}).get("beats_ceiling_052"),
            "baseline_beats_ceiling_052": (baseline.get("test_blind") or {}).get("beats_ceiling_052"),
            "v0_gate_055_pass": (v0.get("test_blind") or {}).get("gate_055_pass"),
            "v1_gate_055_pass": (v1.get("test_blind") or {}).get("gate_055_pass"),
        },
        "dod_v0": {
            "target": "blind_test_accuracy > 0.52 on promotion-legal axis",
            "met": bool((v0.get("test_blind") or {}).get("beats_ceiling_052")),
        },
        "dod_v1": {
            "target": "blind_test_accuracy > 0.52 on promotion-legal axis (5-axis overlay)",
            "met": bool((v1.get("test_blind") or {}).get("beats_ceiling_052")),
        },
        "note": "Single 50/50 chronological holdout; baseline nf6 fit on train, causal overlay grid on train only.",
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
