# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.88, L:0.9, K:0.35, M:0.42}
# Balance: 90
# Purpose: Evaluate sasang predictions against labeled cohort ground truth.
# Keywords: sasang, clinical, precision, recall, fpr, calibration
#!/usr/bin/env python3
"""Evaluate sasang prediction quality on a labeled cohort JSONL.

Inputs:
- cohort JSONL: sample_id, expected_parent in {TY,SY,TE,SE}
- predictions JSONL: sample_id, predicted_parent in {TY,SY,TE,SE}, optional confidence [0,1]

Outputs:
- classification metrics: precision/recall/f1 (macro + micro), per-class confusion, one-vs-rest FPR
- confidence diagnostics: brier score and ECE (if confidence exists)
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
LABELS = ("TY", "SY", "TE", "SE")


@dataclass
class Pair:
    sample_id: str
    truth: str
    pred: str
    confidence: float | None


def _abs(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if isinstance(row, dict):
                rows.append(row)
    return rows


def _safe_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _clamp01(value: float | None) -> float | None:
    if value is None:
        return None
    return max(0.0, min(1.0, value))


def _idx(label: str) -> int:
    return LABELS.index(label)


def _build_pairs(
    cohort_rows: list[dict[str, Any]],
    pred_rows: list[dict[str, Any]],
) -> tuple[list[Pair], dict[str, int]]:
    cohort_map: dict[str, str] = {}
    bad_truth = 0
    for row in cohort_rows:
        sid = str(row.get("sample_id", "")).strip()
        truth = str(row.get("expected_parent", "")).strip().upper()
        if not sid or truth not in LABELS:
            bad_truth += 1
            continue
        cohort_map[sid] = truth

    pred_map: dict[str, tuple[str, float | None]] = {}
    bad_pred = 0
    for row in pred_rows:
        sid = str(row.get("sample_id", "")).strip()
        pred = str(row.get("predicted_parent", "")).strip().upper()
        conf = _clamp01(_safe_float(row.get("confidence")))
        if not sid or pred not in LABELS:
            bad_pred += 1
            continue
        pred_map[sid] = (pred, conf)

    keys = sorted(set(cohort_map) & set(pred_map))
    pairs = [
        Pair(sample_id=sid, truth=cohort_map[sid], pred=pred_map[sid][0], confidence=pred_map[sid][1])
        for sid in keys
    ]
    diagnostics = {
        "cohort_rows": len(cohort_rows),
        "prediction_rows": len(pred_rows),
        "cohort_rows_invalid": bad_truth,
        "prediction_rows_invalid": bad_pred,
        "paired_rows": len(pairs),
        "cohort_only_rows": max(0, len(cohort_map) - len(pairs)),
        "prediction_only_rows": max(0, len(pred_map) - len(pairs)),
    }
    return pairs, diagnostics


def _confusion(pairs: list[Pair]) -> list[list[int]]:
    cm = [[0 for _ in LABELS] for _ in LABELS]
    for p in pairs:
        cm[_idx(p.truth)][_idx(p.pred)] += 1
    return cm


def _class_metrics(cm: list[list[int]]) -> dict[str, dict[str, float | int | None]]:
    n = sum(sum(row) for row in cm)
    by_class: dict[str, dict[str, float | int | None]] = {}
    for c in LABELS:
        i = _idx(c)
        tp = cm[i][i]
        fp = sum(cm[r][i] for r in range(len(LABELS)) if r != i)
        fn = sum(cm[i][c2] for c2 in range(len(LABELS)) if c2 != i)
        tn = n - tp - fp - fn
        precision = tp / (tp + fp) if (tp + fp) else None
        recall = tp / (tp + fn) if (tp + fn) else None
        f1 = (
            2.0 * precision * recall / (precision + recall)
            if precision is not None and recall is not None and (precision + recall) > 0
            else None
        )
        fpr = fp / (fp + tn) if (fp + tn) else None
        by_class[c] = {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "tn": tn,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "fpr_one_vs_rest": fpr,
        }
    return by_class


def _aggregate_metrics(by_class: dict[str, dict[str, float | int | None]], cm: list[list[int]]) -> dict[str, float | None]:
    macro_precision_vals = [m["precision"] for m in by_class.values() if isinstance(m["precision"], float)]
    macro_recall_vals = [m["recall"] for m in by_class.values() if isinstance(m["recall"], float)]
    macro_f1_vals = [m["f1"] for m in by_class.values() if isinstance(m["f1"], float)]

    total = sum(sum(row) for row in cm)
    correct = sum(cm[i][i] for i in range(len(LABELS)))
    micro_precision = correct / total if total else None
    # Single-label multiclass micro precision == micro recall == micro f1 == accuracy
    micro_recall = micro_precision
    micro_f1 = micro_precision

    return {
        "accuracy": micro_precision,
        "precision_macro": (sum(macro_precision_vals) / len(macro_precision_vals)) if macro_precision_vals else None,
        "recall_macro": (sum(macro_recall_vals) / len(macro_recall_vals)) if macro_recall_vals else None,
        "f1_macro": (sum(macro_f1_vals) / len(macro_f1_vals)) if macro_f1_vals else None,
        "precision_micro": micro_precision,
        "recall_micro": micro_recall,
        "f1_micro": micro_f1,
    }


def _confidence_metrics(pairs: list[Pair], bins: int) -> dict[str, Any]:
    conf_pairs = [(p.confidence, 1.0 if p.pred == p.truth else 0.0) for p in pairs if p.confidence is not None]
    if not conf_pairs:
        return {"available": False, "count": 0}

    brier = sum((c - y) ** 2 for c, y in conf_pairs) / len(conf_pairs)

    # Expected Calibration Error (ECE) over fixed-width bins.
    ece = 0.0
    bin_rows: list[dict[str, Any]] = []
    for b in range(bins):
        lo = b / bins
        hi = (b + 1) / bins
        members = [(c, y) for c, y in conf_pairs if (c >= lo and (c < hi or (b == bins - 1 and c <= hi)))]
        if not members:
            bin_rows.append({"bin": b, "lo": lo, "hi": hi, "count": 0, "acc": None, "conf": None, "abs_gap": None})
            continue
        acc = sum(y for _, y in members) / len(members)
        conf = sum(c for c, _ in members) / len(members)
        gap = abs(acc - conf)
        ece += gap * (len(members) / len(conf_pairs))
        bin_rows.append({"bin": b, "lo": lo, "hi": hi, "count": len(members), "acc": acc, "conf": conf, "abs_gap": gap})

    return {
        "available": True,
        "count": len(conf_pairs),
        "brier_score": brier,
        "ece": ece,
        "bins": bin_rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Evaluate sasang clinical-style metrics on cohort+predictions JSONL.")
    ap.add_argument(
        "--cohort",
        default="data/constitution/korean_cohort/real_cohort.synthetic.v1.jsonl",
        help="Ground-truth cohort JSONL (sample_id, expected_parent).",
    )
    ap.add_argument("--predictions", required=True, help="Predictions JSONL (sample_id, predicted_parent, confidence?).")
    ap.add_argument(
        "--out",
        default="reports/constitution/btrack_pilot/sasang_clinical_eval_latest.json",
        help="Output JSON report path.",
    )
    ap.add_argument("--ece-bins", type=int, default=10, help="Number of ECE bins.")
    args = ap.parse_args()

    cohort_path = _abs(args.cohort)
    pred_path = _abs(args.predictions)
    out_path = _abs(args.out)
    bins = max(2, int(args.ece_bins))

    if not cohort_path.is_file():
        print(f"ERROR: missing cohort file: {cohort_path}")
        return 2
    if not pred_path.is_file():
        print(f"ERROR: missing predictions file: {pred_path}")
        return 2

    cohort_rows = _load_jsonl(cohort_path)
    pred_rows = _load_jsonl(pred_path)
    pairs, diagnostics = _build_pairs(cohort_rows, pred_rows)
    if not pairs:
        print("ERROR: no paired rows between cohort and predictions")
        return 3

    cm = _confusion(pairs)
    by_class = _class_metrics(cm)
    aggregate = _aggregate_metrics(by_class, cm)
    confidence = _confidence_metrics(pairs, bins=bins)

    report = {
        "schema": "sasang_clinical_eval_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": {
            "cohort_path": str(cohort_path),
            "predictions_path": str(pred_path),
        },
        "diagnostics": diagnostics,
        "labels": list(LABELS),
        "confusion_matrix": {
            "rows_truth_cols_pred": cm,
            "label_order": list(LABELS),
        },
        "metrics": {
            **aggregate,
            "per_class": by_class,
            "confidence": confidence,
        },
        "notes": [
            "This report is for evaluation only; not a diagnosis engine.",
            "Clinical validity depends on cohort quality and label governance.",
        ],
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK: wrote {out_path}")
    print(f"paired_rows={diagnostics['paired_rows']}, accuracy={aggregate['accuracy']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

