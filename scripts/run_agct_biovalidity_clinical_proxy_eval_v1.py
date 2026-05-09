#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

AXES = ("TY", "SY", "TE", "SE")
BASES = ("A", "C", "G", "T")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_float(v: str | float | int | None) -> float | None:
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return None
        try:
            return float(s)
        except ValueError:
            return None
    return None


def _normalize(d: dict[str, float]) -> dict[str, float]:
    s = sum(d.values())
    if s <= 0:
        return {k: 0.0 for k in d}
    return {k: v / s for k, v in d.items()}


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    if n < 2:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = sum((x - mx) ** 2 for x in xs)
    dy = sum((y - my) ** 2 for y in ys)
    den = (dx * dy) ** 0.5
    if den <= 0:
        return None
    return num / den


def _load_labels(path: Path, sample_col: str, label_col: str, risk_col: str) -> tuple[dict[str, str], dict[str, float]]:
    labels: dict[str, str] = {}
    risks: dict[str, float] = {}
    with path.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            sid = str(row.get(sample_col) or "").strip()
            lab = str(row.get(label_col) or "").strip().upper()
            rv = _safe_float(row.get(risk_col))
            if not sid:
                continue
            if lab in AXES:
                labels[sid] = lab
            if rv is not None:
                risks[sid] = rv
    return labels, risks


def _load_geno_counts(path: Path, sample_col: str, genotype_col: str) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    with path.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            sid = str(row.get(sample_col) or "").strip()
            geno = str(row.get(genotype_col) or "").strip().upper()
            if not sid or not geno:
                continue
            c = out.setdefault(sid, {b: 0 for b in BASES})
            for ch in geno:
                if ch in c:
                    c[ch] += 1
    return out


def _predict(counts: dict[str, dict[str, int]], weights: dict[str, dict[str, float]]) -> dict[str, dict[str, float]]:
    pred: dict[str, dict[str, float]] = {}
    for sid, c in counts.items():
        t = sum(c.values()) or 1
        ratios = {b: c[b] / t for b in BASES}
        raw = {ax: sum(ratios[b] * float(weights[b][ax]) for b in BASES) for ax in AXES}
        pred[sid] = _normalize(raw)
    return pred


def _top_axis(proj: dict[str, float]) -> str:
    return sorted(proj.items(), key=lambda kv: (-kv[1], AXES.index(kv[0])))[0][0]


def _confusion(truth: dict[str, str], pred: dict[str, str]) -> list[list[int]]:
    cm = [[0 for _ in AXES] for _ in AXES]
    for sid, t in truth.items():
        p = pred.get(sid)
        if p is None:
            continue
        cm[AXES.index(t)][AXES.index(p)] += 1
    return cm


def _metrics(cm: list[list[int]]) -> dict[str, float]:
    n = sum(sum(r) for r in cm)
    acc = (sum(cm[i][i] for i in range(len(AXES))) / n) if n else 0.0
    f1s: list[float] = []
    for i in range(len(AXES)):
        tp = cm[i][i]
        fp = sum(cm[r][i] for r in range(len(AXES)) if r != i)
        fn = sum(cm[i][c] for c in range(len(AXES)) if c != i)
        pr = tp / (tp + fp) if (tp + fp) else 0.0
        rc = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (2 * pr * rc / (pr + rc)) if (pr + rc) else 0.0
        f1s.append(f1)
    return {"accuracy": acc, "macro_f1": (sum(f1s) / len(f1s) if f1s else 0.0)}


def main() -> int:
    ap = argparse.ArgumentParser(description="B-track proxy biological validity / clinical predictive evaluation.")
    ap.add_argument("--cohort-csv", type=Path, required=True)
    ap.add_argument("--genotype-csv", type=Path, required=True)
    ap.add_argument("--weights-json", type=Path, required=True)
    ap.add_argument("--sample-col", type=str, default="sample_id")
    ap.add_argument("--label-col", type=str, default="expected_parent")
    ap.add_argument("--risk-col", type=str, default="risk_score")
    ap.add_argument("--genotype-col", type=str, default="genotype")
    ap.add_argument("--output-json", type=Path, default=Path("reports/agct_biovalidity_clinical_proxy_eval_v1_latest.json"))
    ns = ap.parse_args()

    labels, risks = _load_labels(ns.cohort_csv, ns.sample_col, ns.label_col, ns.risk_col)
    counts = _load_geno_counts(ns.genotype_csv, ns.sample_col, ns.genotype_col)
    weights = json.loads(ns.weights_json.read_text(encoding="utf-8"))

    common = sorted(set(labels.keys()) & set(counts.keys()))
    if not common:
        raise SystemExit("No overlapping sample_id between cohort and genotype.")

    pred_proj = _predict({k: counts[k] for k in common}, weights)
    pred_label = {sid: _top_axis(pred_proj[sid]) for sid in common}
    truth = {sid: labels[sid] for sid in common}
    cm = _confusion(truth, pred_label)
    cls = _metrics(cm)

    # proxy clinical score: convert predicted axis to risk prior
    axis_risk = {"TY": 0.30, "SY": 0.70, "TE": 0.45, "SE": 0.55}
    y_true: list[float] = []
    y_pred: list[float] = []
    for sid in common:
        rv = risks.get(sid)
        if rv is None:
            continue
        y_true.append(rv)
        y_pred.append(axis_risk[pred_label[sid]])
    risk_corr = _pearson(y_true, y_pred)
    mae = (sum(abs(a - b) for a, b in zip(y_true, y_pred)) / len(y_true)) if y_true else None

    payload = {
        "schema": "agct_biovalidity_clinical_proxy_eval_v1",
        "generated_at_utc": _utc_now(),
        "track": "B_TRACK",
        "governance": {"research_only": True, "non_gating": True, "human_review_required": True},
        "inputs": {
            "cohort_csv": str(ns.cohort_csv.resolve()),
            "genotype_csv": str(ns.genotype_csv.resolve()),
            "weights_json": str(ns.weights_json.resolve()),
        },
        "summary": {
            "n_overlap": len(common),
            "classification_accuracy": cls["accuracy"],
            "classification_macro_f1": cls["macro_f1"],
            "risk_corr_proxy": risk_corr,
            "risk_mae_proxy": mae,
        },
        "notes": [
            "This is proxy biological/clinical evaluation, not clinical proof.",
            "Use independent real cohort for final blind validation.",
        ],
    }
    ns.output_json.parent.mkdir(parents=True, exist_ok=True)
    ns.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"WROTE: {ns.output_json.resolve()} "
        f"acc={cls['accuracy']:.4f} f1={cls['macro_f1']:.4f} risk_corr={risk_corr}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
