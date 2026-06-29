#!/usr/bin/env python3
"""[HYPO] RQ-024 v2 nf5 blocked-WF smoke — volume + prior intraday range overlay."""
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
    causal_feature_map,
    run_rq024_blind_variant,
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
DEFAULT_OUT = ROOT / "reports/rq024_btc_lens_v2_nf5_wf_smoke_v1_latest.json"
SCHEMA = "rq024_btc_lens_v2_nf5_wf_smoke_v1"
PINNED_N_FOLDS = 5


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _agg(folds: list[dict[str, Any]]) -> dict[str, Any]:
    accs = [
        float((f.get("test_blind") or {}).get("accuracy"))
        for f in folds
        if isinstance((f.get("test_blind") or {}).get("accuracy"), (int, float))
    ]
    beats = sum(1 for f in folds if (f.get("test_blind") or {}).get("beats_ceiling_052"))
    gate = sum(1 for f in folds if (f.get("test_blind") or {}).get("gate_055_pass"))
    if not accs:
        return {"n_folds": 0}
    mean = sum(accs) / len(accs)
    var = sum((x - mean) ** 2 for x in accs) / len(accs)
    return {
        "n_folds": len(accs),
        "mean_test_accuracy": round(mean, 6),
        "stdev_test_accuracy": round(var**0.5, 6),
        "fraction_test_beats_ceiling_052": round(beats / len(accs), 6),
        "fraction_test_gate_055_pass": round(gate / len(accs), 6),
    }


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

    v1_folds: list[dict[str, Any]] = []
    v2_folds: list[dict[str, Any]] = []
    for fi, (train_dates, test_dates) in enumerate(_blocked_walkforward_folds(dates, nf)):
        train_set, test_set = set(train_dates), set(test_dates)
        train = [r for r in rows if str(r.get("eval_date"))[:10] in train_set]
        test = [r for r in rows if str(r.get("eval_date"))[:10] in test_set]
        if not train or not test:
            continue
        common = dict(
            train=train,
            test=test,
            km=km,
            bm=bm,
            kf=kf,
            bf=bf,
            causal=causal,
            train_objective=str(args.train_objective),
        )
        v1_folds.append(
            {"fold_index": fi, **run_rq024_blind_variant(slug=f"fold{fi}_v1", overlay_version="v1", **common)}
        )
        v2_folds.append(
            {"fold_index": fi, **run_rq024_blind_variant(slug=f"fold{fi}_v2", overlay_version="v2", **common)}
        )

    v1_agg = _agg(v1_folds)
    v2_agg = _agg(v2_folds)
    v1_mean = float(v1_agg.get("mean_test_accuracy") or 0)
    v2_mean = float(v2_agg.get("mean_test_accuracy") or 0)

    out: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "rq_id": "RQ-024",
        "overlay_version": "v2",
        "v2_features_added": ["volume_ratio_5d", "prior_intraday_range"],
        "pinned_config": {"n_folds": nf, "train_objective": args.train_objective},
        "v1_aggregate": v1_agg,
        "v2_aggregate": v2_agg,
        "delta_mean_v2_minus_v1": round(v2_mean - v1_mean, 6),
        "gate_055": {
            "v1_mean_pass": v1_mean >= 0.55,
            "v2_mean_pass": v2_mean >= 0.55,
            "note": "research_only — not Track A promotion",
        },
        "ceiling_052": {
            "v1_beats": v1_mean > CEILING_BASELINE_ACCURACY,
            "v2_beats": v2_mean > CEILING_BASELINE_ACCURACY,
        },
        "folds_v2": v2_folds,
    }
    out_path = args.output if args.output.is_absolute() else ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path.resolve()}")
    print(f"v1_mean={v1_mean} v2_mean={v2_mean} delta={out['delta_mean_v2_minus_v1']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
