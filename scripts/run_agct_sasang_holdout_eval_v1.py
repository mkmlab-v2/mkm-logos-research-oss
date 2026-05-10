#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.91, L:0.85, K:0.67, M:0.42}
# Balance: 89
# Purpose: Evaluate AGCT-Sasang mapping generalization with train/holdout split.
# Keywords: agct, sasang, holdout, generalization, btrack
"""Run AGCT-Sasang holdout generalization evaluation.

Workflow:
1) Split paired samples into train/holdout.
2) Find best AGCT mapping on train.
3) Evaluate that mapping on holdout.
4) Report train-holdout gap and optional holdout permutation p-value.
"""

from __future__ import annotations

import argparse
import itertools
import json
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BASES = ("A", "C", "G", "T")
LABELS = ("TY", "SY", "TE", "SE")


@dataclass
class SampleSignals:
    sample_id: str
    base_counts: dict[str, int]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_cohort(path: Path, sample_col: str, label_col: str) -> dict[str, str]:
    import csv

    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fields = set(reader.fieldnames or [])
        if sample_col not in fields:
            raise ValueError(f"missing sample column: {sample_col}")
        if label_col not in fields:
            raise ValueError(f"missing label column: {label_col}")
        rows = list(reader)
    out: dict[str, str] = {}
    for row in rows:
        sid = str(row.get(sample_col) or "").strip()
        if not sid:
            continue
        label = str(row.get(label_col) or "").strip().upper()
        if label in LABELS:
            out[sid] = label
    return out


def _load_genotype_signals(path: Path, sample_col: str, genotype_col: str, cohort_labels: dict[str, str]) -> dict[str, SampleSignals]:
    import csv

    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fields = set(reader.fieldnames or [])
        if sample_col not in fields or genotype_col not in fields:
            raise ValueError(f"genotype CSV must include {sample_col} and {genotype_col}")
        rows = list(reader)
    agg: dict[str, dict[str, int]] = {}
    for row in rows:
        sid = str(row.get(sample_col) or "").strip()
        if sid not in cohort_labels:
            continue
        geno = str(row.get(genotype_col) or "").strip().upper()
        if not geno:
            continue
        counts = agg.setdefault(sid, {b: 0 for b in BASES})
        for ch in geno:
            if ch in counts:
                counts[ch] += 1
    out: dict[str, SampleSignals] = {}
    for sid, counts in agg.items():
        if sum(counts.values()) > 0:
            out[sid] = SampleSignals(sample_id=sid, base_counts=counts)
    return out


def _argmax_label(scores: dict[str, float]) -> str:
    return sorted(scores.items(), key=lambda kv: (-kv[1], LABELS.index(kv[0])))[0][0]


def _predict(signals: dict[str, SampleSignals], mapping: dict[str, str]) -> dict[str, str]:
    preds: dict[str, str] = {}
    for sid, sig in signals.items():
        score = {l: 0.0 for l in LABELS}
        for base, cnt in sig.base_counts.items():
            score[mapping[base]] += float(cnt)
        preds[sid] = _argmax_label(score)
    return preds


def _accuracy(truth: dict[str, str], preds: dict[str, str]) -> float:
    if not truth:
        return 0.0
    return sum(1 for sid, t in truth.items() if preds.get(sid) == t) / len(truth)


def _best_mapping(truth: dict[str, str], signals: dict[str, SampleSignals]) -> tuple[dict[str, str], float]:
    best_m = {b: l for b, l in zip(BASES, LABELS)}
    best_acc = -1.0
    for perm in itertools.permutations(LABELS):
        mapping = {b: l for b, l in zip(BASES, perm)}
        acc = _accuracy(truth, _predict(signals, mapping))
        if acc > best_acc:
            best_acc = acc
            best_m = mapping
    return best_m, best_acc


def _permutation_p_value(acc: float, labels: list[str], preds: list[str], repeats: int, seed: int) -> float | None:
    if not labels:
        return None
    rng = random.Random(seed)
    tmp = list(labels)
    hit = 0
    for _ in range(repeats):
        rng.shuffle(tmp)
        pacc = sum(1 for t, p in zip(tmp, preds) if t == p) / len(tmp)
        if pacc >= acc - 1e-12:
            hit += 1
    return (hit + 1) / (repeats + 1)


def main() -> int:
    ap = argparse.ArgumentParser(description="AGCT-Sasang holdout evaluation.")
    ap.add_argument("--cohort-csv", type=Path, required=True)
    ap.add_argument("--genotype-csv", type=Path, required=True)
    ap.add_argument("--sample-col", type=str, default="sample_id")
    ap.add_argument("--label-col", type=str, default="expected_parent")
    ap.add_argument("--genotype-col", type=str, default="genotype")
    ap.add_argument("--holdout-ratio", type=float, default=0.3)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--permutation-repeats", type=int, default=500)
    ap.add_argument(
        "--output-json",
        type=Path,
        default=Path("reports/agct_sasang_holdout_eval_v1_latest.json"),
    )
    ns = ap.parse_args()

    labels = _load_cohort(ns.cohort_csv, ns.sample_col, ns.label_col)
    signals = _load_genotype_signals(ns.genotype_csv, ns.sample_col, ns.genotype_col, labels)
    paired_ids = sorted(set(labels.keys()) & set(signals.keys()))
    if len(paired_ids) < 4:
        # Not enough data to run holdout — still write an artifact and exit 0 so daily
        # automation (e.g. MKM_AIV2_DailyReadiness) is not spuriously red.
        payload_ins = {
            "schema": "agct_sasang_holdout_eval_v1",
            "generated_at_utc": _utc_now(),
            "track": "B_TRACK",
            "governance": {
                "research_only": True,
                "non_gating": True,
                "human_review_required": True,
            },
            "inputs": {
                "cohort_csv": str(ns.cohort_csv.resolve()),
                "genotype_csv": str(ns.genotype_csv.resolve()),
                "sample_col": ns.sample_col,
                "label_col": ns.label_col,
                "genotype_col": ns.genotype_col,
                "holdout_ratio": float(ns.holdout_ratio),
                "seed": int(ns.seed),
                "permutation_repeats": int(ns.permutation_repeats),
            },
            "split": {
                "paired_samples": len(paired_ids),
                "train_n": 0,
                "holdout_n": 0,
            },
            "results": {},
            "summary": {
                "status": "INSUFFICIENT_PAIRED_SAMPLES_HOLD",
                "reason": "need_at_least_4_paired_samples",
            },
        }
        ns.output_json.parent.mkdir(parents=True, exist_ok=True)
        ns.output_json.write_text(json.dumps(payload_ins, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(
            f"WROTE: {ns.output_json.resolve()} "
            f"INSUFFICIENT_PAIRED_SAMPLES_HOLD paired={len(paired_ids)} (need 4+)"
        )
        return 0

    rng = random.Random(ns.seed)
    shuffled = paired_ids[:]
    rng.shuffle(shuffled)
    holdout_n = max(1, int(round(len(shuffled) * float(ns.holdout_ratio))))
    holdout_n = min(holdout_n, len(shuffled) - 1)
    holdout_ids = set(shuffled[:holdout_n])
    train_ids = set(shuffled[holdout_n:])

    train_truth = {sid: labels[sid] for sid in train_ids}
    hold_truth = {sid: labels[sid] for sid in holdout_ids}
    train_sig = {sid: signals[sid] for sid in train_ids}
    hold_sig = {sid: signals[sid] for sid in holdout_ids}

    best_train_mapping, train_acc = _best_mapping(train_truth, train_sig)
    hold_preds = _predict(hold_sig, best_train_mapping)
    hold_acc = _accuracy(hold_truth, hold_preds)
    gap = train_acc - hold_acc

    hold_best_mapping, hold_oracle_acc = _best_mapping(hold_truth, hold_sig)
    hold_ids = sorted(list(hold_truth.keys()))
    hold_labels = [hold_truth[sid] for sid in hold_ids]
    hold_pred_labels = [hold_preds[sid] for sid in hold_ids]
    hold_p = _permutation_p_value(hold_acc, hold_labels, hold_pred_labels, ns.permutation_repeats, ns.seed)

    payload = {
        "schema": "agct_sasang_holdout_eval_v1",
        "generated_at_utc": _utc_now(),
        "track": "B_TRACK",
        "governance": {
            "research_only": True,
            "non_gating": True,
            "human_review_required": True,
        },
        "inputs": {
            "cohort_csv": str(ns.cohort_csv.resolve()),
            "genotype_csv": str(ns.genotype_csv.resolve()),
            "sample_col": ns.sample_col,
            "label_col": ns.label_col,
            "genotype_col": ns.genotype_col,
            "holdout_ratio": float(ns.holdout_ratio),
            "seed": int(ns.seed),
            "permutation_repeats": int(ns.permutation_repeats),
        },
        "split": {
            "paired_samples": len(paired_ids),
            "train_n": len(train_ids),
            "holdout_n": len(holdout_ids),
        },
        "results": {
            "best_train_mapping": best_train_mapping,
            "train_accuracy": train_acc,
            "holdout_accuracy_under_train_mapping": hold_acc,
            "generalization_gap": gap,
            "holdout_oracle_best_mapping": hold_best_mapping,
            "holdout_oracle_best_accuracy": hold_oracle_acc,
            "holdout_accuracy_permutation_p_value": hold_p,
        },
        "summary": {
            "status": "PASS_GENERALIZATION" if hold_acc >= 0.5 and gap <= 0.4 else "HOLD",
        },
    }

    ns.output_json.parent.mkdir(parents=True, exist_ok=True)
    ns.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"WROTE: {ns.output_json.resolve()} train_acc={train_acc:.4f} "
        f"hold_acc={hold_acc:.4f} gap={gap:.4f} p={hold_p}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
