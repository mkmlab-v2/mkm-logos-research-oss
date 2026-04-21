#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.9, L:0.84, K:0.62, M:0.44}
# Balance: 90
# Purpose: Run baseline vs treatment holdout eval with bootstrap CI and promotion gating.
# Keywords: bio, dna, ab, holdout, bootstrap, promotion
"""A/B holdout evaluation runner for DNA feature promotion decisions.

Input contract:
- baseline/treatment CSV must contain:
  sample_id, y_true, y_pred
  (column names are configurable with args)
- Rows are joined by sample_id; only common sample_ids are evaluated.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True)
class EvalRow:
    sample_id: str
    y_true: str
    y_pred_base: str
    y_pred_treat: str


def _load_prediction_map(path: Path, sample_col: str, true_col: str, pred_col: str) -> dict[str, tuple[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        required = {sample_col, true_col, pred_col}
        fields = set(reader.fieldnames or [])
        missing = sorted(required - fields)
        if missing:
            raise ValueError(f"missing columns in {path}: {missing}")
        out: dict[str, tuple[str, str]] = {}
        for row in reader:
            sid = str(row.get(sample_col) or "").strip()
            y_true = str(row.get(true_col) or "").strip()
            y_pred = str(row.get(pred_col) or "").strip()
            if not sid or not y_true or not y_pred:
                continue
            out[sid] = (y_true, y_pred)
    return out


def _join_rows(
    baseline: dict[str, tuple[str, str]], treatment: dict[str, tuple[str, str]]
) -> list[EvalRow]:
    joined: list[EvalRow] = []
    for sid in sorted(set(baseline.keys()) & set(treatment.keys())):
        y_true_base, y_pred_base = baseline[sid]
        y_true_treat, y_pred_treat = treatment[sid]
        if y_true_base != y_true_treat:
            # Keep fact-safe behavior: skip conflicting labels.
            continue
        joined.append(
            EvalRow(
                sample_id=sid,
                y_true=y_true_base,
                y_pred_base=y_pred_base,
                y_pred_treat=y_pred_treat,
            )
        )
    return joined


def _split_holdout(rows: list[EvalRow], holdout_ratio: float) -> tuple[list[EvalRow], list[EvalRow]]:
    train: list[EvalRow] = []
    holdout: list[EvalRow] = []
    cutoff = int(holdout_ratio * 10_000)
    for r in rows:
        h = int(hashlib.sha256(r.sample_id.encode("utf-8")).hexdigest()[:8], 16) % 10_000
        if h < cutoff:
            holdout.append(r)
        else:
            train.append(r)
    return train, holdout


def _acc(rows: list[EvalRow], mode: str) -> float:
    if not rows:
        return 0.0
    hits = 0
    for r in rows:
        pred = r.y_pred_base if mode == "base" else r.y_pred_treat
        if pred == r.y_true:
            hits += 1
    return hits / len(rows)


def _bootstrap_delta_ci(
    rows: list[EvalRow], n_bootstrap: int, alpha: float, seed: int
) -> dict[str, float]:
    rng = random.Random(seed)
    if not rows:
        return {"delta_mean": 0.0, "ci_low": 0.0, "ci_high": 0.0}
    deltas: list[float] = []
    n = len(rows)
    for _ in range(n_bootstrap):
        sample = [rows[rng.randrange(0, n)] for _ in range(n)]
        d = _acc(sample, "treat") - _acc(sample, "base")
        deltas.append(d)
    deltas.sort()
    lo_i = max(0, min(len(deltas) - 1, int(math.floor((alpha / 2.0) * len(deltas)))))
    hi_i = max(0, min(len(deltas) - 1, int(math.floor((1.0 - alpha / 2.0) * len(deltas))) - 1))
    return {
        "delta_mean": sum(deltas) / len(deltas),
        "ci_low": deltas[lo_i],
        "ci_high": deltas[hi_i],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Run A/B holdout evaluation with bootstrap CI.")
    ap.add_argument("--baseline-csv", type=Path, required=True)
    ap.add_argument("--treatment-csv", type=Path, required=True)
    ap.add_argument("--sample-col", default="sample_id")
    ap.add_argument("--true-col", default="y_true")
    ap.add_argument("--pred-col", default="y_pred")
    ap.add_argument("--holdout-ratio", type=float, default=0.3)
    ap.add_argument("--bootstrap-iterations", type=int, default=2000)
    ap.add_argument("--bootstrap-alpha", type=float, default=0.05, help="0.05 = 95%% CI")
    ap.add_argument("--seed", type=int, default=20260421)
    ap.add_argument("--min-holdout-samples", type=int, default=30)
    ap.add_argument("--min-abs-uplift", type=float, default=0.01)
    ap.add_argument(
        "--output-json",
        type=Path,
        default=Path("reports/bio_dna_ab_holdout_eval_v1_latest.json"),
    )
    ns = ap.parse_args()

    if not (0.0 < ns.holdout_ratio < 1.0):
        raise ValueError("--holdout-ratio must be between 0 and 1")

    base = _load_prediction_map(ns.baseline_csv, ns.sample_col, ns.true_col, ns.pred_col)
    treat = _load_prediction_map(ns.treatment_csv, ns.sample_col, ns.true_col, ns.pred_col)
    rows = _join_rows(base, treat)
    train, holdout = _split_holdout(rows, ns.holdout_ratio)

    train_base = _acc(train, "base")
    train_treat = _acc(train, "treat")
    hold_base = _acc(holdout, "base")
    hold_treat = _acc(holdout, "treat")
    hold_delta = hold_treat - hold_base
    ci = _bootstrap_delta_ci(holdout, ns.bootstrap_iterations, ns.bootstrap_alpha, ns.seed)

    gate = {
        "holdout_sample_count_ok": len(holdout) >= ns.min_holdout_samples,
        "holdout_uplift_ok": hold_delta >= ns.min_abs_uplift,
        "holdout_ci_lower_gt_zero": ci["ci_low"] > 0.0,
    }
    passing = sum(1 for v in gate.values() if v)
    ready = passing == len(gate)

    payload: dict[str, Any] = {
        "schema": "bio_dna_ab_holdout_eval_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "inputs": {
            "baseline_csv": str(ns.baseline_csv.resolve()),
            "treatment_csv": str(ns.treatment_csv.resolve()),
            "sample_col": ns.sample_col,
            "true_col": ns.true_col,
            "pred_col": ns.pred_col,
        },
        "split": {
            "holdout_ratio": ns.holdout_ratio,
            "joined_sample_count": len(rows),
            "train_count": len(train),
            "holdout_count": len(holdout),
        },
        "metrics": {
            "train_baseline_accuracy": train_base,
            "train_treatment_accuracy": train_treat,
            "train_uplift": train_treat - train_base,
            "holdout_baseline_accuracy": hold_base,
            "holdout_treatment_accuracy": hold_treat,
            "holdout_uplift": hold_delta,
        },
        "bootstrap": {
            "iterations": ns.bootstrap_iterations,
            "alpha": ns.bootstrap_alpha,
            **ci,
        },
        "promotion_gate": {
            "thresholds": {
                "min_holdout_samples": ns.min_holdout_samples,
                "min_abs_uplift": ns.min_abs_uplift,
                "ci_lower_bound_gt_zero": True,
            },
            "checks": gate,
            "passing": passing,
            "total": len(gate),
            "promotion_candidate_ready": ready,
        },
        "note": "A/B holdout evidence only. Human review is required before any promotion claim.",
    }
    ns.output_json.parent.mkdir(parents=True, exist_ok=True)
    ns.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"WROTE: {ns.output_json.resolve()} holdout_n={len(holdout)} "
        f"uplift={hold_delta:.6f} ci=[{ci['ci_low']:.6f},{ci['ci_high']:.6f}] ready={ready}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

