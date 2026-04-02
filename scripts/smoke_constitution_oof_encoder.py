# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.82, L:0.88, K:0.4, M:0.45}
# Balance: 85
# Purpose: Compare sentence encoders on Korean synthetic cohort (prototype baseline, not production OOF).
# Keywords: sasang, sentence-transformers, macro-f1, smoke, encoder
#!/usr/bin/env python3
"""Smoke-test Korean vs multilingual encoders on labeled synthetic cohort JSONL.

Method: stratified train/test split → L2-normalized mean embedding prototypes per class
(TY/SY/TE/SE) → cosine similarity argmax on test. **Research/smoke only** — not a clinical claim.

Requires: pip install sentence-transformers numpy
"""

from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
LABELS = ("TY", "SY", "TE", "SE")


def _abs(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def _load_cohort(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                continue
            sid = str(row.get("sample_id", "")).strip()
            text = str(row.get("text", "")).strip()
            lab = str(row.get("expected_parent", "")).strip().upper()
            if sid and text and lab in LABELS:
                rows.append(row)
    return rows


def _stratified_split(
    rows: list[dict[str, Any]],
    test_ratio: float,
    seed: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rng = random.Random(seed)
    by_lab: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        by_lab[str(r["expected_parent"]).strip().upper()].append(r)
    train: list[dict[str, Any]] = []
    test: list[dict[str, Any]] = []
    for lab in LABELS:
        items = by_lab.get(lab, []).copy()
        rng.shuffle(items)
        if not items:
            continue
        n = len(items)
        n_test = max(1, int(round(n * test_ratio))) if n >= 2 else 0
        if n == 1:
            train.extend(items)
            continue
        test.extend(items[:n_test])
        train.extend(items[n_test:])
    return train, test


def _l2_normalize(vecs: Any) -> Any:
    import numpy as np

    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    norms = np.maximum(norms, 1e-12)
    return vecs / norms


def _macro_f1_from_confusion(cm: list[list[int]]) -> tuple[float | None, list[list[int]]]:
    """cm[truth][pred], same LABELS order."""
    f1s: list[float] = []
    for i, c in enumerate(LABELS):
        tp = cm[i][i]
        fp = sum(cm[r][i] for r in range(4) if r != i)
        fn = sum(cm[i][j] for j in range(4) if j != i)
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        if prec + rec <= 0:
            f1s.append(0.0)
        else:
            f1s.append(2.0 * prec * rec / (prec + rec))
    return (sum(f1s) / len(f1s)) if f1s else None, cm


def _evaluate(
    y_true: list[str],
    y_pred: list[str],
) -> tuple[float | None, list[list[int]]]:
    idx = {c: i for i, c in enumerate(LABELS)}
    cm = [[0 for _ in LABELS] for _ in LABELS]
    for t, p in zip(y_true, y_pred):
        if t in idx and p in idx:
            cm[idx[t]][idx[p]] += 1
    return _macro_f1_from_confusion(cm)


@dataclass
class RunResult:
    model_name: str
    f1_macro: float | None
    accuracy: float
    n_test: int
    train_seconds: float
    infer_seconds: float


def _run_one_model(
    model_name: str,
    train_rows: list[dict[str, Any]],
    test_rows: list[dict[str, Any]],
) -> tuple[RunResult, list[dict[str, Any]]]:
    import time
    import numpy as np
    from sentence_transformers import SentenceTransformer

    t0 = time.perf_counter()
    model = SentenceTransformer(model_name)
    train_texts = [str(r["text"]) for r in train_rows]
    test_texts = [str(r["text"]) for r in test_rows]
    train_emb = model.encode(
        train_texts,
        batch_size=32,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    t1 = time.perf_counter()
    prototypes = np.zeros((4, train_emb.shape[1]), dtype=np.float64)
    counts = np.zeros(4, dtype=np.int64)
    idx = {c: i for i, c in enumerate(LABELS)}
    for row, emb in zip(train_rows, train_emb):
        lab = str(row["expected_parent"]).strip().upper()
        prototypes[idx[lab]] += emb
        counts[idx[lab]] += 1
    for i in range(4):
        if counts[i] > 0:
            prototypes[i] /= counts[i]
    prototypes = _l2_normalize(prototypes.astype(np.float64))
    test_emb = model.encode(
        test_texts,
        batch_size=32,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    t2 = time.perf_counter()
    sims = test_emb @ prototypes.T
    pred_idx = np.argmax(sims, axis=1)
    y_pred = [LABELS[i] for i in pred_idx]
    conf = [float(sims[i, pred_idx[i]]) for i in range(len(test_rows))]
    y_true = [str(r["expected_parent"]).strip().upper() for r in test_rows]
    acc = sum(1 for a, b in zip(y_true, y_pred) if a == b) / len(y_true) if y_true else 0.0
    f1_macro, _ = _evaluate(y_true, y_pred)
    preds_jsonl: list[dict[str, Any]] = []
    for r, p, c in zip(test_rows, y_pred, conf):
        preds_jsonl.append(
            {
                "sample_id": r["sample_id"],
                "predicted_parent": p,
                "confidence": round(c, 6),
                "prediction_source": f"encoder_smoke_prototype:{model_name}",
            }
        )
    return (
        RunResult(
            model_name=model_name,
            f1_macro=f1_macro,
            accuracy=acc,
            n_test=len(test_rows),
            train_seconds=t1 - t0,
            infer_seconds=t2 - t1,
        ),
        preds_jsonl,
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Encoder smoke: prototype classifier on synthetic Korean cohort.")
    ap.add_argument(
        "--cohort",
        default="data/constitution/korean_cohort/real_cohort.synthetic.v1.jsonl",
        help="Cohort JSONL with sample_id, text, expected_parent.",
    )
    ap.add_argument("--test-ratio", type=float, default=0.2, help="Fraction per class for test (stratified).")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument(
        "--models",
        nargs="+",
        default=["sentence-transformers/all-MiniLM-L6-v2", "jhgan/ko-sroberta-multitask"],
        help="sentence-transformers model ids to compare.",
    )
    ap.add_argument("--max-samples", type=int, default=0, help="If >0, cap cohort size after shuffle (smoke).")
    ap.add_argument(
        "--out",
        default="reports/constitution/btrack_pilot/sasang_encoder_smoke_latest.json",
        help="Summary JSON report.",
    )
    ap.add_argument(
        "--predictions-dir",
        default="reports/constitution/btrack_pilot",
        help="Where to write per-model predictions JSONL.",
    )
    args = ap.parse_args()

    try:
        import numpy  # noqa: F401
    except ImportError:
        print("ERROR: numpy required (pip install numpy)")
        return 2

    cohort_path = _abs(args.cohort)
    if not cohort_path.is_file():
        print(f"ERROR: cohort not found: {cohort_path}")
        return 2

    rows = _load_cohort(cohort_path)
    if not rows:
        print("ERROR: no valid cohort rows")
        return 3

    if args.max_samples and args.max_samples > 0:
        rng = random.Random(args.seed)
        rows = rows.copy()
        rng.shuffle(rows)
        rows = rows[: args.max_samples]

    train_rows, test_rows = _stratified_split(rows, test_ratio=args.test_ratio, seed=args.seed)
    if not test_rows:
        print("ERROR: empty test split — increase cohort or adjust test-ratio")
        return 4

    out_path = _abs(args.out)
    pred_dir = _abs(args.predictions_dir)
    pred_dir.mkdir(parents=True, exist_ok=True)

    runs: list[dict[str, Any]] = []
    for model_name in args.models:
        safe = model_name.replace("/", "__")
        pred_path = pred_dir / f"sasang_encoder_smoke_predictions_{safe}.jsonl"
        try:
            rr, preds = _run_one_model(model_name, train_rows, test_rows)
            with pred_path.open("w", encoding="utf-8") as f:
                for row in preds:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
            runs.append(
                {
                    "status": "ok",
                    "model": model_name,
                    "f1_macro": rr.f1_macro,
                    "accuracy": rr.accuracy,
                    "n_train": len(train_rows),
                    "n_test": rr.n_test,
                    "train_encode_seconds": round(rr.train_seconds, 3),
                    "infer_encode_seconds": round(rr.infer_seconds, 3),
                    "predictions_jsonl": str(pred_path),
                }
            )
            mf = rr.f1_macro if rr.f1_macro is not None else float("nan")
            print(
                f"OK {model_name}: macro_f1={mf:.4f} acc={rr.accuracy:.4f} "
                f"n_test={rr.n_test} pred={pred_path}"
            )
        except OSError as e:
            err = f"{type(e).__name__}: {e}"
            runs.append(
                {
                    "status": "error",
                    "model": model_name,
                    "error": err,
                    "predictions_jsonl": None,
                }
            )
            print(f"FAIL {model_name}: {err}")
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
            runs.append({"status": "error", "model": model_name, "error": err, "predictions_jsonl": None})
            print(f"FAIL {model_name}: {err}")

    comparison: dict[str, Any] | None = None
    ok_runs = [r for r in runs if r.get("status") == "ok" and isinstance(r.get("f1_macro"), (int, float))]
    if len(ok_runs) >= 2:
        a = ok_runs[0]["f1_macro"]
        b = ok_runs[1]["f1_macro"]
        comparison = {
            "macro_f1_delta_model2_minus_model1": float(b) - float(a),
            "model1": ok_runs[0]["model"],
            "model2": ok_runs[1]["model"],
            "note": "Positive delta means second model higher macro-F1 on this split.",
        }

    report = {
        "schema": "sasang_encoder_smoke_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "purpose": "Research smoke — prototype cosine classifier; not clinical OOF SSOT.",
        "caveats": [
            "Synthetic cohorts may repeat identical `text` lines; duplicates can land in both train and test and inflate metrics.",
            "If Hugging Face download fails with errno 28, set HF_HOME (and TRANSFORMERS_CACHE) to a disk with free space.",
        ],
        "inputs": {
            "cohort_path": str(cohort_path),
            "test_ratio": args.test_ratio,
            "seed": args.seed,
            "max_samples": args.max_samples or None,
        },
        "runs": runs,
        "comparison": comparison,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK: wrote {out_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ImportError as e:
        if "sentence_transformers" in str(e) or "SentenceTransformer" in str(e):
            print("ERROR: sentence-transformers required — pip install sentence-transformers")
            raise SystemExit(2) from e
        raise
