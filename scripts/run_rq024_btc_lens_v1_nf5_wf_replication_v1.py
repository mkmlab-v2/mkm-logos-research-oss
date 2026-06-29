#!/usr/bin/env python3
"""[HYPO] RQ-024 v1 nf5-only blocked-WF replication (pinned config after stability readout)."""
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
DEFAULT_OUT = ROOT / "reports/rq024_btc_lens_v1_nf5_wf_replication_v1_latest.json"
SCHEMA = "rq024_btc_lens_v1_nf5_wf_replication_v1"
PINNED_N_FOLDS = 5


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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
    b_agg = result["baseline_nf6_srcdir"]["aggregate"]
    v1_agg = result["rq024_causal_lens_v1"]["aggregate"]
    v1_mean = float(v1_agg.get("mean_test_accuracy") or 0)

    weight_keys: dict[str, int] = {}
    for fold in result["rq024_causal_lens_v1"].get("folds") or []:
        w = fold.get("causal_weights_v1") or {}
        key = (
            f"ovn={w.get('w_overnight')}|pr={w.get('w_prior_range_centered')}|"
            f"dd={w.get('w_drawdown_20d')}|ldr={w.get('w_last_daily_return')}|"
            f"vol={w.get('w_realized_vol_5d')}"
        )
        weight_keys[key] = weight_keys.get(key, 0) + 1

    out: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "rq_id": "RQ-024",
        "pinned_config": {
            "overlay_version": "v1",
            "n_folds": nf,
            "train_objective": args.train_objective,
            "promotion_axis": "no_expanded_prior",
        },
        "inputs": {
            "score_json": str(score_path.relative_to(ROOT)).replace("\\", "/"),
            "split_dates_total": len(dates),
        },
        "baseline_aggregate": b_agg,
        "v1_aggregate": v1_agg,
        "delta_mean_v1_minus_baseline": round(
            v1_mean - float(b_agg.get("mean_test_accuracy") or 0), 6
        ),
        "weight_mode": sorted(weight_keys.items(), key=lambda x: -x[1])[:3],
        "fold_detail": result,
        "dod_nf5_replication": {
            "target": f"v1 mean_test_accuracy > {CEILING_BASELINE_ACCURACY} on pinned nf={nf}",
            "mean_beats_052": v1_mean > CEILING_BASELINE_ACCURACY,
            "fraction_beats_052_pass": (v1_agg.get("fraction_test_beats_ceiling_052") or 0) >= 0.5,
            "met": bool(
                v1_mean > CEILING_BASELINE_ACCURACY
                and (v1_agg.get("fraction_test_beats_ceiling_052") or 0) >= 0.5
            ),
        },
    }
    out_path = args.output if args.output.is_absolute() else ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path.resolve()}")
    print(
        f"nf{nf} v1_mean={v1_mean} frac_052={v1_agg.get('fraction_test_beats_ceiling_052')} "
        f"met={out['dod_nf5_replication']['met']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
