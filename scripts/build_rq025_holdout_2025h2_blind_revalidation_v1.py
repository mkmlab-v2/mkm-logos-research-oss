#!/usr/bin/env python3
"""[HYPO] Blind temporal holdout: train <2025-07-01, test 2025H2 only (vault-direct stack)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_rq025_gbdt_shadow_hypo_v1 import (  # noqa: E402
    _fit_logistic,
    _predict_proba,
    _standardize,
)
from scripts.rq025_ensemble_labeling_v1 import build_intersection_labeled  # noqa: E402

DEFAULT_WIDE = ROOT / "reports/rq025_vault_macro_direct_wide_hypo_v1_latest.json"
DEFAULT_CAUSAL = ROOT / "reports/rq025_vault_macro_direct_causal_hypo_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/rq025_holdout_2025h2_blind_revalidation_v1_latest.json"
SCHEMA = "rq025_holdout_2025h2_blind_revalidation_v1"
HOLDOUT_START = "2025-07-01"
HOLDOUT_END = "2025-12-31"
TRAIN_CUTOFF = "2025-07-01"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _eval_split(
    labeled: list[tuple[str, np.ndarray, float]],
    *,
    train_dates: set[str],
    test_dates: set[str],
) -> dict[str, Any]:
    train = [(d, v, y) for d, v, y in labeled if d in train_dates]
    test = [(d, v, y) for d, v, y in labeled if d in test_dates]
    if len(train) < 8 or len(test) < 8:
        return {
            "n_train": len(train),
            "n_test": len(test),
            "status": "insufficient_rows",
        }
    x_train = np.vstack([v for _, v, _ in train])
    y_train = np.array([y for _, _, y in train])
    x_test = np.vstack([v for _, v, _ in test])
    y_test = np.array([y for _, _, y in test])
    x_train_z, mu, sd = _standardize(x_train)
    x_test_z = (x_test - mu) / sd
    w = _fit_logistic(x_train_z, y_train)
    pred = (_predict_proba(x_test_z, w) >= 0.5).astype(float)
    acc = float(np.mean(pred == y_test))
    base = max(float(np.mean(y_test)), 1.0 - float(np.mean(y_test)))
    train_pred = (_predict_proba(x_train_z, w) >= 0.5).astype(float)
    train_acc = float(np.mean(train_pred == y_train))
    return {
        "n_train": len(train),
        "n_test": len(test),
        "status": "ok",
        "train_accuracy": round(train_acc, 6),
        "test_accuracy": round(acc, 6),
        "train_minus_test_gap": round(train_acc - acc, 6),
        "always_majority_baseline": round(base, 6),
        "delta_minus_majority": round(acc - base, 6),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--wide-join-json", type=Path, default=DEFAULT_WIDE)
    ap.add_argument("--causal-json", type=Path, default=DEFAULT_CAUSAL)
    ap.add_argument("--holdout-start", default=HOLDOUT_START)
    ap.add_argument("--holdout-end", default=HOLDOUT_END)
    ap.add_argument("--train-cutoff", default=TRAIN_CUTOFF)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    wide = _load(args.wide_join_json if args.wide_join_json.is_absolute() else ROOT / args.wide_join_json)
    causal = _load(args.causal_json if args.causal_json.is_absolute() else ROOT / args.causal_json)
    baseline, ensemble, meta = build_intersection_labeled(wide, causal)

    h0, h1 = args.holdout_start[:10], args.holdout_end[:10]
    cutoff = args.train_cutoff[:10]
    all_dates = {d for d, _, _ in baseline}
    train_dates = {d for d in all_dates if d < cutoff}
    test_dates = {d for d in all_dates if h0 <= d <= h1}

    base_eval = _eval_split(baseline, train_dates=train_dates, test_dates=test_dates)
    ens_eval = _eval_split(ensemble, train_dates=train_dates, test_dates=test_dates)
    delta = None
    if base_eval.get("status") == "ok" and ens_eval.get("status") == "ok":
        delta = round(float(ens_eval["test_accuracy"]) - float(base_eval["test_accuracy"]), 6)

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "gating": "[NON_GATING]",
        "rq_id": "RQ-025",
        "protocol": {
            "train_dates": f"eval_date < {cutoff}",
            "test_dates": f"{h0} .. {h1}",
            "feature_selection_leakage_ack": (
                "causal selected_features were fit on full sample upstream; "
                "holdout is blind for model fit only"
            ),
        },
        "labeling": meta,
        "n_train_dates": len(train_dates),
        "n_test_dates": len(test_dates),
        "causal_baseline": base_eval,
        "full_ensemble": ens_eval,
        "delta_ensemble_minus_baseline_test": delta,
        "verdict": {
            "ensemble_improves_holdout_test": bool(delta is not None and delta > 0),
            "beats_majority_on_holdout": bool(
                ens_eval.get("status") == "ok"
                and float(ens_eval.get("test_accuracy") or 0)
                > float(ens_eval.get("always_majority_baseline") or 1)
            ),
            "gate_0_55_on_holdout": bool(
                ens_eval.get("status") == "ok" and float(ens_eval.get("test_accuracy") or 0) >= 0.55
            ),
            "track_a_promotion": False,
        },
        "track_wall": {
            "track_a_auto_merge": False,
            "oracle_promotion": False,
            "live_trading": False,
        },
    }
    out_path = args.output if args.output.is_absolute() else ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"WROTE: {out_path} test_base={base_eval.get('test_accuracy')} "
        f"test_ens={ens_eval.get('test_accuracy')} delta={delta}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
