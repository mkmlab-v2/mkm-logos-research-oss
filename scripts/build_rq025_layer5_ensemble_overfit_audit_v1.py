#!/usr/bin/env python3
"""[HYPO] Layer-5 ensemble overfit audit — train/test gap, p/n ratio, blocked WF."""
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
    _blocked_folds,
    _fit_logistic,
    _predict_proba,
    _standardize,
)
from scripts.rq025_ensemble_labeling_v1 import build_intersection_labeled  # noqa: E402

DEFAULT_WIDE = ROOT / "reports/rq025_vault_macro_direct_wide_hypo_v1_latest.json"
DEFAULT_CAUSAL = ROOT / "reports/rq025_vault_macro_direct_causal_hypo_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/rq025_layer5_ensemble_overfit_audit_v1_latest.json"
SCHEMA = "rq025_layer5_ensemble_overfit_audit_v1"
P_OVER_N_WARN = 0.2


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _wf_with_train_gap(
    labeled: list[tuple[str, np.ndarray, float]],
    *,
    n_folds: int,
) -> dict[str, Any]:
    dates = [d for d, _, _ in labeled]
    vec_by_date = {d: v for d, v, _ in labeled}
    y_by_date = {d: y for d, _, y in labeled}
    test_accs: list[float] = []
    train_accs: list[float] = []
    gaps: list[float] = []
    folds_out: list[dict[str, Any]] = []
    for fi, (train_dates, test_dates) in enumerate(_blocked_folds(dates, n_folds)):
        x_train = np.vstack([vec_by_date[d] for d in train_dates])
        y_train = np.array([y_by_date[d] for d in train_dates])
        x_test = np.vstack([vec_by_date[d] for d in test_dates])
        y_test = np.array([y_by_date[d] for d in test_dates])
        x_train_z, mu, sd = _standardize(x_train)
        x_test_z = (x_test - mu) / sd
        w = _fit_logistic(x_train_z, y_train)
        train_pred = (_predict_proba(x_train_z, w) >= 0.5).astype(float)
        test_pred = (_predict_proba(x_test_z, w) >= 0.5).astype(float)
        tr = float(np.mean(train_pred == y_train))
        te = float(np.mean(test_pred == y_test)) if y_test.size else 0.0
        test_accs.append(te)
        train_accs.append(tr)
        gaps.append(tr - te)
        folds_out.append(
            {
                "fold_index": fi,
                "n_train": len(train_dates),
                "n_test": len(test_dates),
                "train_accuracy": round(tr, 6),
                "test_accuracy": round(te, 6),
                "train_minus_test_gap": round(tr - te, 6),
            }
        )
    mean_train = sum(train_accs) / len(train_accs) if train_accs else 0.0
    mean_test = sum(test_accs) / len(test_accs) if test_accs else 0.0
    mean_gap = sum(gaps) / len(gaps) if gaps else 0.0
    return {
        "mean_train_accuracy": round(mean_train, 6),
        "mean_test_accuracy": round(mean_test, 6),
        "mean_train_minus_test_gap": round(mean_gap, 6),
        "folds": folds_out,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--wide-join-json", type=Path, default=DEFAULT_WIDE)
    ap.add_argument("--causal-json", type=Path, default=DEFAULT_CAUSAL)
    ap.add_argument("--n-folds", type=int, default=3)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    wide = _load(args.wide_join_json if args.wide_join_json.is_absolute() else ROOT / args.wide_join_json)
    causal = _load(args.causal_json if args.causal_json.is_absolute() else ROOT / args.causal_json)
    baseline, ensemble, meta = build_intersection_labeled(wide, causal)
    n = int(meta.get("n_labeled_rows") or 0)
    p_base = int(meta.get("n_baseline_features") or 0)
    p_ens = p_base + int(meta.get("n_ensemble_features_added") or 0)

    base_wf = _wf_with_train_gap(baseline, n_folds=int(args.n_folds))
    ens_wf = _wf_with_train_gap(ensemble, n_folds=int(args.n_folds))
    p_over_n = round(p_ens / max(n, 1), 6)

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "gating": "[NON_GATING]",
        "rq_id": "RQ-025",
        "labeling": meta,
        "p_over_n": p_over_n,
        "p_over_n_warn_threshold": P_OVER_N_WARN,
        "causal_baseline": base_wf,
        "full_ensemble": ens_wf,
        "verdict": {
            "high_p_over_n_risk": p_over_n > P_OVER_N_WARN,
            "ensemble_gap_worse_than_baseline": float(ens_wf["mean_train_minus_test_gap"])
            > float(base_wf["mean_train_minus_test_gap"]),
            "ensemble_test_below_baseline": float(ens_wf["mean_test_accuracy"])
            < float(base_wf["mean_test_accuracy"]),
            "overfit_suspected": (
                p_over_n > P_OVER_N_WARN
                and float(ens_wf["mean_train_minus_test_gap"]) >= 0.08
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
        f"WROTE: {out_path} p_over_n={p_over_n} ens_gap={ens_wf['mean_train_minus_test_gap']} "
        f"overfit={payload['verdict']['overfit_suspected']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
