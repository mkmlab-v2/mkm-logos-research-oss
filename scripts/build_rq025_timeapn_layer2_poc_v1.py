#!/usr/bin/env python3
"""[HYPO][NON_GATING] RQ-025 layer-2 TimeAPN stub — DWT features + logistic WF vs static macro."""
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
from scripts.rq025_timeapn_dwt_stub_v1 import expand_macro_series_features  # noqa: E402

DEFAULT_WIDE = ROOT / "reports/rq025_flow_fred_wide_join_hypo_v1_latest.json"
DEFAULT_CAUSAL = ROOT / "reports/rq025_causal_feature_filter_hybrid_intersection_hypo_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/rq025_timeapn_layer2_poc_v1_latest.json"
SCHEMA = "rq025_timeapn_layer2_poc_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _eval_wf(
    labeled: list[tuple[str, np.ndarray, float]],
    *,
    n_folds: int,
) -> dict[str, Any]:
    dates = [d for d, _, _ in labeled]
    vec_by_date = {d: v for d, v, _ in labeled}
    y_by_date = {d: y for d, _, y in labeled}
    accs: list[float] = []
    bases: list[float] = []
    folds_out: list[dict[str, Any]] = []
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
        base = max(float(np.mean(y_test)), 1.0 - float(np.mean(y_test)))
        folds_out.append(
            {
                "fold_index": fi,
                "n_train": len(train_dates),
                "n_test": len(test_dates),
                "test_accuracy": round(acc, 6),
                "always_majority_baseline": round(base, 6),
            }
        )
        accs.append(acc)
        bases.append(base)
    mean_acc = sum(accs) / len(accs) if accs else 0.0
    mean_base = sum(bases) / len(bases) if bases else 0.0
    return {
        "mean_test_accuracy": round(mean_acc, 6),
        "mean_majority_baseline": round(mean_base, 6),
        "delta_minus_majority": round(mean_acc - mean_base, 6),
        "folds": folds_out,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--wide-join-json", type=Path, default=DEFAULT_WIDE)
    ap.add_argument("--causal-json", type=Path, default=DEFAULT_CAUSAL)
    ap.add_argument("--dwt-window", type=int, default=8)
    ap.add_argument("--n-folds", type=int, default=3)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    wide_path = args.wide_join_json if args.wide_join_json.is_absolute() else ROOT / args.wide_join_json
    causal_path = args.causal_json if args.causal_json.is_absolute() else ROOT / args.causal_json
    wide = _load(wide_path)
    causal = _load(causal_path)
    base_features = list(causal.get("selected_features") or [])
    if not base_features:
        raise SystemExit("no selected_features in causal json")

    rows = [
        r
        for r in wide.get("rows_hybrid_kospi_252d") or []
        if isinstance(r, dict) and r.get("macro_present") and r.get("daily_flow_present")
    ]
    rows.sort(key=lambda r: str(r.get("eval_date")))
    if len(rows) < 16:
        raise SystemExit(f"insufficient intersection rows: {len(rows)}")

    dates = [str(r.get("eval_date"))[:10] for r in rows]
    macro_keys = sorted(
        {
            f.replace("macro_", "")
            for f in base_features
            if str(f).startswith("macro_")
        }
    )
    values_by_key: dict[str, dict[str, float]] = {}
    for mk in macro_keys:
        vbd: dict[str, float] = {}
        for r in rows:
            dk = str(r.get("eval_date"))[:10]
            macro = r.get("macro") if isinstance(r.get("macro"), dict) else {}
            try:
                vbd[dk] = float(macro.get(mk))
            except (TypeError, ValueError):
                continue
        values_by_key[mk] = vbd

    timeapn_by_date: dict[str, dict[str, float]] = {dk: {} for dk in dates}
    for mk, vbd in values_by_key.items():
        expanded = expand_macro_series_features(
            dates, vbd, window=int(args.dwt_window), prefix=f"ta_{mk}"
        )
        for dk, feats in expanded.items():
            timeapn_by_date.setdefault(dk, {}).update(feats)

    static_labeled: list[tuple[str, np.ndarray, float]] = []
    timeapn_labeled: list[tuple[str, np.ndarray, float]] = []
    for r in rows:
        hit = r.get("panel_hit")
        if hit is None:
            continue
        dk = str(r.get("eval_date"))[:10]
        macro = r.get("macro") if isinstance(r.get("macro"), dict) else {}
        static_vec: list[float] = []
        for name in base_features:
            key = name.replace("macro_", "", 1) if name.startswith("macro_") else name
            try:
                static_vec.append(float(macro.get(key)))
            except (TypeError, ValueError):
                static_vec.append(float("nan"))
        ta_feats = sorted(timeapn_by_date.get(dk, {}))
        ta_vec = [float(timeapn_by_date[dk][k]) for k in ta_feats]
        sv = np.array(static_vec, dtype=float)
        tv = np.array(static_vec + ta_vec, dtype=float)
        if not np.all(np.isfinite(sv)):
            continue
        if not np.all(np.isfinite(tv)):
            continue
        yv = 1.0 if bool(hit) else 0.0
        static_labeled.append((dk, sv, yv))
        timeapn_labeled.append((dk, tv, yv))

    if len(static_labeled) < 16:
        raise SystemExit(f"insufficient labeled rows: {len(static_labeled)}")

    static_wf = _eval_wf(static_labeled, n_folds=int(args.n_folds))
    timeapn_wf = _eval_wf(timeapn_labeled, n_folds=int(args.n_folds))
    delta = round(
        float(timeapn_wf["mean_test_accuracy"]) - float(static_wf["mean_test_accuracy"]), 6
    )

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "gating": "[NON_GATING]",
        "rq_id": "RQ-025",
        "layer": 2,
        "implementation": "haar_dwt_level1_stub_v1",
        "inputs": {
            "wide_join_json": str(wide_path.relative_to(ROOT)).replace("\\", "/"),
            "causal_json": str(causal_path.relative_to(ROOT)).replace("\\", "/"),
            "base_features": base_features,
            "dwt_window": int(args.dwt_window),
            "n_labeled_rows": len(static_labeled),
            "n_timeapn_features_added": len(ta_feats) if static_labeled else 0,
        },
        "static_macro_only": static_wf,
        "static_plus_timeapn": timeapn_wf,
        "delta_timeapn_minus_static": delta,
        "verdict": {
            "timeapn_improves_over_static": delta > 0,
            "beats_majority_baseline": float(timeapn_wf["mean_test_accuracy"])
            > float(timeapn_wf["mean_majority_baseline"]),
            "track_a_promotion": False,
            "note": "TimeAPN stub is not full Mamba-ProbTSF; research_only",
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
        f"WROTE: {out_path} static={static_wf['mean_test_accuracy']} "
        f"timeapn={timeapn_wf['mean_test_accuracy']} delta={delta}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
