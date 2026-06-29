#!/usr/bin/env python3
"""[HYPO] Shared labeling for RQ-025 causal baseline + L2-L4 stub ensemble stacks."""
from __future__ import annotations

from typing import Any

import numpy as np

from scripts.build_rq025_gbdt_shadow_hypo_v1 import _feature_vector
from scripts.rq025_chronos_stub_v1 import expand_chronos_series_features
from scripts.rq025_cmdmamba_stub_v1 import expand_cmdmamba_series_features
from scripts.rq025_timeapn_dwt_stub_v1 import expand_macro_series_features

Labeled = list[tuple[str, np.ndarray, float]]


def build_intersection_labeled(
    wide: dict[str, Any],
    causal: dict[str, Any],
    *,
    dwt_window: int = 8,
    chronos_window: int = 16,
    mamba_window: int = 12,
) -> tuple[Labeled, Labeled, dict[str, Any]]:
    base_features = list(causal.get("selected_features") or [])
    if not base_features:
        raise ValueError("no selected_features in causal json")

    rows = [
        r
        for r in wide.get("rows_hybrid_kospi_252d") or []
        if isinstance(r, dict) and r.get("macro_present") and r.get("daily_flow_present")
    ]
    rows.sort(key=lambda r: str(r.get("eval_date")))

    dates = [str(r.get("eval_date"))[:10] for r in rows]
    macro_keys = sorted(
        {f.replace("macro_", "") for f in base_features if str(f).startswith("macro_")}
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

    extra_by_date: dict[str, dict[str, float]] = {dk: {} for dk in dates}
    for mk, vbd in values_by_key.items():
        for expander, prefix, win in (
            (expand_macro_series_features, f"ta_{mk}", dwt_window),
            (expand_chronos_series_features, f"ch_{mk}", chronos_window),
            (expand_cmdmamba_series_features, f"mb_{mk}", mamba_window),
        ):
            expanded = expander(dates, vbd, window=win, prefix=prefix)
            for dk, feats in expanded.items():
                extra_by_date.setdefault(dk, {}).update(feats)

    baseline: Labeled = []
    ensemble: Labeled = []
    feat_count = 0
    for r in rows:
        hit = r.get("panel_hit")
        if hit is None:
            continue
        dk = str(r.get("eval_date"))[:10]
        base = np.array(_feature_vector(r, base_features), dtype=float)
        extras = sorted(extra_by_date.get(dk, {}))
        if not feat_count and extras:
            feat_count = len(extras)
        ext = np.array([float(extra_by_date[dk][k]) for k in extras], dtype=float)
        full = np.concatenate([base, ext])
        if not (np.all(np.isfinite(base)) and np.all(np.isfinite(full))):
            continue
        yv = 1.0 if bool(hit) else 0.0
        baseline.append((dk, base, yv))
        ensemble.append((dk, full, yv))

    meta = {
        "base_features": base_features,
        "n_baseline_features": len(base_features),
        "n_ensemble_features_added": feat_count,
        "n_labeled_rows": len(baseline),
    }
    return baseline, ensemble, meta
