#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.92, L:0.86, K:0.68, M:0.41}
# Balance: 90
# Purpose: Sweep AGCT-to-Sasang mapping hypotheses and rank candidates by cohort fit.
# Keywords: bio, dna, sasang, agct, hypothesis, sweep, btrack
"""Run AGCT-Sasang hypothesis sweep (B-track).

This script evaluates all AGCT->(TY,SY,TE,SE) mapping permutations and reports:
- classification metrics against cohort labels
- optional risk-correlation metrics if risk column is provided
- permutation-test p-value for top-1 accuracy
"""

from __future__ import annotations

import argparse
import csv
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
    risk_value: float | None


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        try:
            return float(s)
        except ValueError:
            return None
    return None


def _load_cohort(path: Path, sample_col: str, label_col: str, risk_col: str) -> tuple[dict[str, str], dict[str, float | None]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fields = set(reader.fieldnames or [])
        if sample_col not in fields:
            raise ValueError(f"missing sample column: {sample_col}")
        if label_col not in fields:
            raise ValueError(f"missing label column: {label_col}")
        rows = list(reader)

    labels: dict[str, str] = {}
    risks: dict[str, float | None] = {}
    for row in rows:
        sid = str(row.get(sample_col) or "").strip()
        if not sid:
            continue
        label = str(row.get(label_col) or "").strip().upper()
        if label not in LABELS:
            continue
        labels[sid] = label
        risks[sid] = _safe_float(row.get(risk_col)) if risk_col else None
    return labels, risks


def _load_genotype_signals(
    path: Path,
    sample_col: str,
    genotype_col: str,
    cohort_labels: dict[str, str],
    cohort_risks: dict[str, float | None],
) -> dict[str, SampleSignals]:
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
        if sum(counts.values()) <= 0:
            continue
        out[sid] = SampleSignals(sample_id=sid, base_counts=counts, risk_value=cohort_risks.get(sid))
    return out


def _argmax_label(scores: dict[str, float]) -> str:
    # Deterministic tie-break by label order.
    return sorted(scores.items(), key=lambda kv: (-kv[1], LABELS.index(kv[0])))[0][0]


def _build_predictions(
    signals: dict[str, SampleSignals],
    mapping: dict[str, str],
) -> dict[str, str]:
    preds: dict[str, str] = {}
    for sid, sig in signals.items():
        score = {label: 0.0 for label in LABELS}
        for base, count in sig.base_counts.items():
            label = mapping[base]
            score[label] += float(count)
        preds[sid] = _argmax_label(score)
    return preds


def _confusion(truth: dict[str, str], pred: dict[str, str]) -> list[list[int]]:
    cm = [[0 for _ in LABELS] for _ in LABELS]
    for sid, t in truth.items():
        p = pred.get(sid)
        if p is None:
            continue
        cm[LABELS.index(t)][LABELS.index(p)] += 1
    return cm


def _classification_metrics(cm: list[list[int]]) -> dict[str, float]:
    n = sum(sum(r) for r in cm)
    correct = sum(cm[i][i] for i in range(len(LABELS)))
    accuracy = (correct / n) if n else 0.0

    f1s: list[float] = []
    for i, _label in enumerate(LABELS):
        tp = cm[i][i]
        fp = sum(cm[r][i] for r in range(len(LABELS)) if r != i)
        fn = sum(cm[i][c] for c in range(len(LABELS)) if c != i)
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
        f1s.append(f1)
    macro_f1 = sum(f1s) / len(f1s) if f1s else 0.0
    return {"accuracy": accuracy, "macro_f1": macro_f1}


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    if n < 2:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den_x = sum((x - mx) ** 2 for x in xs)
    den_y = sum((y - my) ** 2 for y in ys)
    den = (den_x * den_y) ** 0.5
    if den <= 0:
        return None
    return num / den


def _risk_correlation(
    signals: dict[str, SampleSignals],
    pred: dict[str, str],
    risk_profile: dict[str, float],
) -> dict[str, Any]:
    model_scores: list[float] = []
    obs_risks: list[float] = []
    for sid, p in pred.items():
        risk_val = signals[sid].risk_value
        if risk_val is None:
            continue
        model_scores.append(float(risk_profile[p]))
        obs_risks.append(float(risk_val))
    corr = _pearson(model_scores, obs_risks)
    return {
        "n_pairs": len(model_scores),
        "pearson_corr": corr,
    }


def _permutation_p_value(best_acc: float, labels: list[str], preds: list[str], repeats: int, seed: int) -> float | None:
    if len(labels) == 0:
        return None
    rng = random.Random(seed)
    hits = 0
    tmp = list(labels)
    for _ in range(repeats):
        rng.shuffle(tmp)
        acc = sum(1 for t, p in zip(tmp, preds) if t == p) / len(tmp)
        if acc >= best_acc - 1e-12:
            hits += 1
    return (hits + 1) / (repeats + 1)


def main() -> int:
    ap = argparse.ArgumentParser(description="Sweep AGCT->Sasang mappings on cohort/genotype data.")
    ap.add_argument("--cohort-csv", type=Path, required=True)
    ap.add_argument("--genotype-csv", type=Path, required=True, help="Long format with sample_id and genotype.")
    ap.add_argument("--sample-col", type=str, default="sample_id")
    ap.add_argument("--label-col", type=str, default="expected_parent")
    ap.add_argument("--risk-col", type=str, default="risk_score", help="Optional cohort risk column.")
    ap.add_argument(
        "--risk-profile-json",
        type=Path,
        default=None,
        help="Optional JSON mapping label->score. Default: TY:-1.0 SY:1.0 TE:-0.5 SE:0.5",
    )
    ap.add_argument("--genotype-col", type=str, default="genotype")
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--permutation-repeats", type=int, default=500)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument(
        "--output-json",
        type=Path,
        default=Path("reports/agct_sasang_hypothesis_sweep_v1_latest.json"),
    )
    ns = ap.parse_args()

    cohort_labels, cohort_risks = _load_cohort(ns.cohort_csv, ns.sample_col, ns.label_col, ns.risk_col)
    signals = _load_genotype_signals(
        ns.genotype_csv,
        ns.sample_col,
        ns.genotype_col,
        cohort_labels,
        cohort_risks,
    )
    paired_ids = sorted(set(cohort_labels.keys()) & set(signals.keys()))
    if not paired_ids:
        raise SystemExit("No paired sample_id between cohort and genotype inputs.")

    truth = {sid: cohort_labels[sid] for sid in paired_ids}
    signals = {sid: signals[sid] for sid in paired_ids}

    risk_profile = {"TY": -1.0, "SY": 1.0, "TE": -0.5, "SE": 0.5}
    if ns.risk_profile_json is not None and ns.risk_profile_json.is_file():
        obj = json.loads(ns.risk_profile_json.read_text(encoding="utf-8"))
        if isinstance(obj, dict):
            for label in LABELS:
                value = _safe_float(obj.get(label))
                if value is not None:
                    risk_profile[label] = float(value)

    rows: list[dict[str, Any]] = []
    best_preds: dict[str, str] = {}
    best_acc = -1.0

    for perm in itertools.permutations(LABELS):
        mapping = {base: label for base, label in zip(BASES, perm)}
        pred = _build_predictions(signals, mapping)
        cm = _confusion(truth, pred)
        cls = _classification_metrics(cm)
        risk = _risk_correlation(signals, pred, risk_profile)
        row = {
            "mapping": mapping,
            "metrics": cls,
            "risk_overlay": risk,
        }
        rows.append(row)
        if cls["accuracy"] > best_acc:
            best_acc = cls["accuracy"]
            best_preds = pred

    rows_sorted = sorted(
        rows,
        key=lambda r: (
            float(r["metrics"]["accuracy"]),
            float(r["metrics"]["macro_f1"]),
            abs(float(r["risk_overlay"]["pearson_corr"] or 0.0)),
        ),
        reverse=True,
    )
    top_k = max(1, int(ns.top_k))
    top_rows = rows_sorted[:top_k]

    best_labels = [truth[sid] for sid in paired_ids]
    best_pred_labels = [best_preds[sid] for sid in paired_ids]
    p_value = _permutation_p_value(best_acc, best_labels, best_pred_labels, ns.permutation_repeats, ns.seed)

    payload = {
        "schema": "agct_sasang_hypothesis_sweep_v1",
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
            "risk_col": ns.risk_col,
            "risk_profile": risk_profile,
        },
        "summary": {
            "paired_samples": len(paired_ids),
            "n_hypotheses": len(rows_sorted),
            "top_k": top_k,
            "best_accuracy": rows_sorted[0]["metrics"]["accuracy"],
            "best_macro_f1": rows_sorted[0]["metrics"]["macro_f1"],
            "best_mapping": rows_sorted[0]["mapping"],
            "best_accuracy_permutation_p_value": p_value,
            "permutation_repeats": int(ns.permutation_repeats),
            "seed": int(ns.seed),
        },
        "top_hypotheses": top_rows,
        "notes": [
            "AGCT mapping is treated as hypothesis only.",
            "Do not auto-promote to A-track/live gating.",
        ],
    }

    ns.output_json.parent.mkdir(parents=True, exist_ok=True)
    ns.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"WROTE: {ns.output_json.resolve()} paired={len(paired_ids)} "
        f"best_acc={rows_sorted[0]['metrics']['accuracy']:.4f} p={p_value}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
