#!/usr/bin/env python3
"""[HYPO][NON_GATING] RQ-025 GBDT shadow — logistic stub on causal-selected features (no LightGBM dep)."""
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

DEFAULT_WIDE = ROOT / "reports/rq025_flow_fred_wide_join_hypo_v1_latest.json"
DEFAULT_CAUSAL = ROOT / "reports/rq025_causal_feature_filter_poc_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/rq025_gbdt_shadow_hypo_v1_latest.json"
DEFAULT_OUT_INTERSECTION = ROOT / "reports/rq025_intersection_causal_wf_smoke_hypo_v1_latest.json"
SCHEMA = "rq025_gbdt_shadow_hypo_v1"
SCHEMA_INTERSECTION = "rq025_intersection_causal_wf_smoke_hypo_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _feature_vector(row: dict[str, Any], names: list[str]) -> list[float]:
    out: list[float] = []
    daily = row.get("daily_flow") if isinstance(row.get("daily_flow"), dict) else {}
    macro = row.get("macro") if isinstance(row.get("macro"), dict) else {}
    for name in names:
        v = None
        if name in daily:
            v = daily.get(name)
        elif name.startswith("macro_"):
            v = macro.get(name.replace("macro_", "", 1))
        elif name in macro:
            v = macro.get(name)
        elif name in row:
            v = row.get(name)
        else:
            v = None
        try:
            out.append(float(v))
        except (TypeError, ValueError):
            out.append(float("nan"))
    return out


def _standardize(x: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mu = np.nanmean(x, axis=0)
    sd = np.nanstd(x, axis=0)
    sd[sd < 1e-9] = 1.0
    z = (x - mu) / sd
    return z, mu, sd


def _sigmoid(z: np.ndarray) -> np.ndarray:
    z = np.clip(z, -40.0, 40.0)
    return 1.0 / (1.0 + np.exp(-z))


def _fit_logistic(x: np.ndarray, y: np.ndarray, *, steps: int = 400, lr: float = 0.1) -> np.ndarray:
    n, p = x.shape
    w = np.zeros(p + 1)
    for _ in range(steps):
        design = np.hstack([np.ones((n, 1)), x])
        pred = _sigmoid(design @ w)
        grad = design.T @ (pred - y) / max(n, 1)
        w -= lr * grad
    return w


def _predict_proba(x: np.ndarray, w: np.ndarray) -> np.ndarray:
    design = np.hstack([np.ones((x.shape[0], 1)), x])
    return _sigmoid(design @ w)


def _blocked_folds(dates: list[str], n_folds: int) -> list[tuple[list[str], list[str]]]:
    dates = sorted(set(dates))
    if n_folds < 2 or len(dates) < n_folds + 1:
        return []
    chunk = len(dates) // n_folds
    folds: list[tuple[list[str], list[str]]] = []
    for i in range(n_folds):
        test = dates[i * chunk : (i + 1) * chunk if i < n_folds - 1 else len(dates)]
        train = [d for d in dates if d not in test]
        if train and test:
            folds.append((train, test))
    return folds


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--wide-join-json", type=Path, default=DEFAULT_WIDE)
    ap.add_argument("--causal-json", type=Path, default=DEFAULT_CAUSAL)
    ap.add_argument("--cohort", choices=("flow_panel_30d", "hybrid_kospi_252d"), default="flow_panel_30d")
    ap.add_argument(
        "--require-intersection",
        action="store_true",
        help="Only rows with macro_present and daily_flow_present",
    )
    ap.add_argument("--n-folds", type=int, default=3)
    ap.add_argument("--min-rows", type=int, default=8)
    ap.add_argument("--output", type=Path, default=None)
    args = ap.parse_args(argv)

    if args.output is None:
        out_default = (
            DEFAULT_OUT_INTERSECTION if args.require_intersection else DEFAULT_OUT
        )
        args.output = out_default

    wide_path = args.wide_join_json if args.wide_join_json.is_absolute() else ROOT / args.wide_join_json
    causal_path = args.causal_json if args.causal_json.is_absolute() else ROOT / args.causal_json
    out_path = args.output if args.output.is_absolute() else ROOT / args.output

    if not wide_path.is_file():
        raise SystemExit(f"missing wide join: {wide_path}")
    if not causal_path.is_file():
        raise SystemExit(f"missing causal filter: {causal_path}")

    wide = _load(wide_path)
    causal = _load(causal_path)
    key = "rows_flow_panel_30d" if args.cohort == "flow_panel_30d" else "rows_hybrid_kospi_252d"
    rows = [r for r in wide.get(key) or [] if isinstance(r, dict)]
    if args.require_intersection:
        rows = [r for r in rows if r.get("macro_present") and r.get("daily_flow_present")]
    features = list(causal.get("selected_features") or [])
    if not features:
        raise SystemExit("no selected_features in causal json")
    min_rows = max(int(args.min_rows), 4)
    if len(rows) < min_rows:
        raise SystemExit(f"insufficient rows for shadow WF: {len(rows)} < {min_rows}")

    labeled: list[tuple[str, np.ndarray, float]] = []
    for row in rows:
        hit = row.get("panel_hit")
        if hit is None:
            continue
        vec = np.array(_feature_vector(row, features), dtype=float)
        if not np.all(np.isfinite(vec)):
            continue
        labeled.append((str(row.get("eval_date")), vec, 1.0 if bool(hit) else 0.0))

    if len(labeled) < min_rows:
        raise SystemExit(f"insufficient labeled rows: {len(labeled)} < {min_rows}")

    n_folds = int(args.n_folds)
    if len(labeled) < (n_folds + 1) * 2:
        n_folds = max(2, len(labeled) // 4)

    dates = [d for d, _, _ in labeled]
    vec_by_date = {d: v for d, v, _ in labeled}
    y_by_date = {d: y for d, _, y in labeled}

    folds_out: list[dict[str, Any]] = []
    accs: list[float] = []
    base_accs: list[float] = []

    for fi, (train_dates, test_dates) in enumerate(_blocked_folds(dates, n_folds)):
        x_train = np.vstack([vec_by_date[d] for d in train_dates])
        y_train = np.array([y_by_date[d] for d in train_dates])
        x_test = np.vstack([vec_by_date[d] for d in test_dates])
        y_test = np.array([y_by_date[d] for d in test_dates])

        x_train_z, mu, sd = _standardize(x_train)
        x_test_z = (x_test - mu) / sd
        w = _fit_logistic(x_train_z, y_train)
        pred = (_predict_proba(x_test_z, w) >= 0.5).astype(float)
        acc = float(np.mean(pred == y_test)) if y_test.size else 0.0
        base = float(np.mean(y_test))  # always-positive rate proxy
        base_acc = max(base, 1.0 - base)
        folds_out.append(
            {
                "fold_index": fi,
                "n_train": len(train_dates),
                "n_test": len(test_dates),
                "test_accuracy": round(acc, 6),
                "always_majority_baseline": round(base_acc, 6),
            }
        )
        accs.append(acc)
        base_accs.append(base_acc)

    mean_acc = sum(accs) / len(accs) if accs else 0.0
    mean_base = sum(base_accs) / len(base_accs) if base_accs else 0.0

    schema = SCHEMA_INTERSECTION if args.require_intersection else SCHEMA
    payload: dict[str, Any] = {
        "schema": schema,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "gating": "[NON_GATING]",
        "hypothesis_tag": "[HYPO]",
        "rq_id": "RQ-025",
        "implementation": "logistic_regression_stub_v1",
        "inputs": {
            "wide_join_json": str(wide_path.relative_to(ROOT)).replace("\\", "/"),
            "causal_json": str(causal_path.relative_to(ROOT)).replace("\\", "/"),
            "cohort": args.cohort,
            "require_intersection": args.require_intersection,
            "features": features,
            "n_labeled_rows": len(labeled),
            "n_folds": n_folds,
            "small_n_warning": len(labeled) < 40,
        },
        "shadow_metrics": {
            "mean_test_accuracy": round(mean_acc, 6),
            "mean_majority_baseline": round(mean_base, 6),
            "delta_minus_majority": round(mean_acc - mean_base, 6),
        },
        "folds": folds_out,
        "track_wall": {
            "track_a_auto_merge": False,
            "oracle_promotion": False,
            "live_trading": False,
            "headline_uplift_claim_allowed": False,
        },
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"WROTE: {out_path} mean_acc={mean_acc:.4f} baseline={mean_base:.4f} "
        f"delta={mean_acc - mean_base:+.4f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
