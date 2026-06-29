#!/usr/bin/env python3
"""[HYPO][NON_GATING] RQ-025 causal feature filter — offline stub (not full tigramite PCMCI).

Stages (report-aligned, simplified):
  1) high-|r| collinearity prune
  2) mutual-information rank (binned proxy)
  3) transfer-entropy prefilter (F-PCMCI TE stage proxy)
  4) lag-1 partial-correlation stub (MCI stand-in)

Does not gate Track A, Oracle promotion, or live orders.
"""
from dataclasses import dataclass, field
from typing import Any, Sequence

import numpy as np

SCHEMA = "rq025_causal_feature_filter_poc_v1"
_IMPLEMENTATION = "rq025_causal_filter_stub_v1"


def _as_2d(x: np.ndarray) -> np.ndarray:
    arr = np.asarray(x, dtype=float)
    if arr.ndim == 1:
        return arr.reshape(-1, 1)
    return arr


def _finite_rows(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    x2 = _as_2d(x)
    y1 = np.asarray(y, dtype=float).reshape(-1)
    if x2.shape[0] != y1.shape[0]:
        raise ValueError(f"row mismatch: X {x2.shape[0]} vs y {y1.shape[0]}")
    mask = np.isfinite(y1) & np.all(np.isfinite(x2), axis=1)
    return x2[mask], y1[mask]


def _pearson(a: np.ndarray, b: np.ndarray) -> float:
    if a.size < 3 or b.size < 3:
        return 0.0
    a0 = a - float(np.mean(a))
    b0 = b - float(np.mean(b))
    denom = float(np.linalg.norm(a0) * np.linalg.norm(b0))
    if denom < 1e-12:
        return 0.0
    return float(np.dot(a0, b0) / denom)


def prune_high_correlation(
    x: np.ndarray,
    names: Sequence[str],
    *,
    threshold: float = 0.85,
) -> tuple[np.ndarray, list[str], list[dict[str, Any]]]:
    """Greedy drop: keep higher-variance feature when |r| exceeds threshold."""
    x2 = _as_2d(x)
    n_feat = x2.shape[1]
    if n_feat == 0:
        return x2, list(names), []
    order = sorted(range(n_feat), key=lambda j: float(np.var(x2[:, j])), reverse=True)
    kept_idx: list[int] = []
    dropped: list[dict[str, Any]] = []
    for j in order:
        ok = True
        for k in kept_idx:
            r = abs(_pearson(x2[:, j], x2[:, k]))
            if r >= threshold:
                dropped.append(
                    {
                        "feature": names[j],
                        "dropped_because_correlated_with": names[k],
                        "abs_pearson_r": round(r, 6),
                        "stage": "correlation_prune",
                    }
                )
                ok = False
                break
        if ok:
            kept_idx.append(j)
    kept_idx.sort()
    out_names = [names[i] for i in kept_idx]
    return x2[:, kept_idx], out_names, dropped


def _discretize(v: np.ndarray, bins: int) -> np.ndarray:
    if v.size == 0:
        return v.astype(int)
    qs = np.linspace(0.0, 1.0, bins + 1)
    edges = np.quantile(v, qs)
    edges = np.unique(edges)
    if edges.size < 2:
        return np.zeros_like(v, dtype=int)
    return np.digitize(v, edges[1:-1], right=False)


def mutual_information_proxy(x: np.ndarray, y: np.ndarray, *, bins: int = 5) -> float:
    """Histogram MI proxy on finite aligned vectors."""
    xf = np.asarray(x, dtype=float).reshape(-1)
    yf = np.asarray(y, dtype=float).reshape(-1)
    m = np.isfinite(xf) & np.isfinite(yf)
    xf, yf = xf[m], yf[m]
    if xf.size < 5:
        return 0.0
    bx = _discretize(xf, bins)
    by = _discretize(yf, bins)
    n = bx.size
    mi = 0.0
    for i in range(int(bx.max()) + 1):
        for j in range(int(by.max()) + 1):
            pxy = float(np.mean((bx == i) & (by == j)))
            if pxy < 1e-12:
                continue
            px = float(np.mean(bx == i))
            py = float(np.mean(by == j))
            if px < 1e-12 or py < 1e-12:
                continue
            mi += pxy * np.log(pxy / (px * py) + 1e-12)
    return float(max(mi, 0.0))


def rank_mutual_information(
    x: np.ndarray,
    names: Sequence[str],
    y: np.ndarray,
    *,
    top_k: int | None = None,
    min_mi: float = 0.0,
) -> tuple[list[str], list[dict[str, Any]]]:
    x2 = _as_2d(x)
    scores: list[dict[str, Any]] = []
    for j, name in enumerate(names):
        mi = mutual_information_proxy(x2[:, j], y)
        scores.append({"feature": name, "mi_proxy": round(mi, 6), "stage": "mutual_information"})
    scores.sort(key=lambda r: r["mi_proxy"], reverse=True)
    if top_k is not None:
        scores = scores[: max(int(top_k), 0)]
    selected = [r["feature"] for r in scores if r["mi_proxy"] >= min_mi]
    return selected, scores


def _te_direction_probe(a: np.ndarray, b: np.ndarray, lookback: int = 12) -> float:
    """Lag-direction probe scaled ~[0,5] (aligned with B-track TE stub)."""
    a = np.asarray(a, dtype=float).reshape(-1)
    b = np.asarray(b, dtype=float).reshape(-1)
    n = min(a.size, b.size)
    if n < 4:
        return 0.0
    a, b = a[-n:], b[-n:]
    da = np.diff(a)
    db = np.diff(b)
    m = min(da.size, db.size)
    if m < 3:
        return 0.0
    da, db = da[-m:], db[-m:]
    window = min(lookback, m)
    da, db = da[-window:], db[-window:]
    sa = np.sign(da)
    sb = np.sign(db)
    sa[sa == 0] = 1.0
    sb[sb == 0] = 1.0
    agree = float(np.mean(sa == sb))
    directional = abs(agree - 0.5) * 2.0
    vol = float(np.std(da)) / (float(np.mean(np.abs(da))) + 1e-9)
    return float(np.clip(directional * (1.0 + min(2.0, vol)) * 2.5, 0.0, 5.0))


def te_prefilter(
    x: np.ndarray,
    names: Sequence[str],
    y: np.ndarray,
    *,
    te_min: float = 0.5,
    lookback: int = 12,
) -> tuple[list[str], list[dict[str, Any]]]:
    x2 = _as_2d(x)
    y1 = np.asarray(y, dtype=float).reshape(-1)
    rows: list[dict[str, Any]] = []
    kept: list[str] = []
    for j, name in enumerate(names):
        te = _te_direction_probe(x2[:, j], y1, lookback=lookback)
        row = {"feature": name, "te_probe": round(te, 6), "stage": "te_prefilter"}
        rows.append(row)
        if te >= te_min:
            kept.append(name)
    return kept, rows


def _residual(target: np.ndarray, predictors: np.ndarray) -> np.ndarray:
    t = np.asarray(target, dtype=float).reshape(-1, 1)
    p = np.asarray(predictors, dtype=float)
    if p.size == 0 or p.shape[1] == 0:
        return t.reshape(-1)
    ones = np.ones((p.shape[0], 1))
    design = np.hstack([ones, p])
    beta, _, _, _ = np.linalg.lstsq(design, t, rcond=None)
    return (t - design @ beta).reshape(-1)


def pcmci_stub_lag1(
    x: np.ndarray,
    names: Sequence[str],
    y: np.ndarray,
    *,
    min_abs_partial: float = 0.05,
) -> tuple[list[str], list[dict[str, Any]]]:
    """Lag-1 partial correlation stub (MCI stand-in, not causal sufficiency proof)."""
    x2 = _as_2d(x)
    y1 = np.asarray(y, dtype=float).reshape(-1)
    if x2.shape[0] < 5:
        return [], []
    x_lag = x2[:-1, :]
    y_now = y1[1:]
    n = min(x_lag.shape[0], y_now.size)
    x_lag = x_lag[-n:, :]
    y_now = y_now[-n:]
    kept: list[str] = []
    audit: list[dict[str, Any]] = []
    for j, name in enumerate(names):
        others = [k for k in range(len(names)) if k != j]
        pred = x_lag[:, others] if others else np.empty((n, 0))
        rx = _residual(x_lag[:, j], pred)
        ry = _residual(y_now, pred)
        pc = _pearson(rx, ry)
        row = {
            "feature": name,
            "lag1_partial_corr": round(pc, 6),
            "stage": "pcmci_stub_lag1",
        }
        audit.append(row)
        if abs(pc) >= min_abs_partial:
            kept.append(name)
    return kept, audit


@dataclass
class CausalFilterConfig:
    corr_threshold: float = 0.85
    mi_top_k: int | None = None
    mi_min: float = 0.0
    te_min: float = 0.5
    te_lookback: int = 12
    pcmci_min_abs_partial: float = 0.05


@dataclass
class CausalFilterResult:
    selected_features: list[str] = field(default_factory=list)
    stages: dict[str, Any] = field(default_factory=dict)
    dropped: list[dict[str, Any]] = field(default_factory=list)


def run_causal_feature_filter(
    x: np.ndarray,
    names: Sequence[str],
    y: np.ndarray,
    config: CausalFilterConfig | None = None,
) -> CausalFilterResult:
    cfg = config or CausalFilterConfig()
    x_clean, y_clean = _finite_rows(x, y)
    if x_clean.shape[1] == 0:
        return CausalFilterResult(selected_features=[], stages={"n_rows": int(x_clean.shape[0])})

    x1, n1, drop_corr = prune_high_correlation(
        x_clean, list(names), threshold=cfg.corr_threshold
    )
    mi_names, mi_scores = rank_mutual_information(
        x1, n1, y_clean, top_k=cfg.mi_top_k, min_mi=cfg.mi_min
    )
    idx_mi = [n1.index(n) for n in mi_names if n in n1]
    x2 = x1[:, idx_mi] if idx_mi else x1[:, :0]

    te_names, te_scores = te_prefilter(
        x2, mi_names, y_clean, te_min=cfg.te_min, lookback=cfg.te_lookback
    )
    idx_te = [mi_names.index(n) for n in te_names if n in mi_names]
    x3 = x2[:, idx_te] if idx_te else x2[:, :0]

    pcmci_names, pcmci_scores = pcmci_stub_lag1(
        x3, te_names, y_clean, min_abs_partial=cfg.pcmci_min_abs_partial
    )

    return CausalFilterResult(
        selected_features=pcmci_names,
        dropped=drop_corr,
        stages={
            "n_rows": int(x_clean.shape[0]),
            "after_correlation_prune": n1,
            "mutual_information": mi_scores,
            "after_te_prefilter": te_names,
            "te_prefilter": te_scores,
            "pcmci_stub": pcmci_scores,
            "config": {
                "corr_threshold": cfg.corr_threshold,
                "mi_top_k": cfg.mi_top_k,
                "mi_min": cfg.mi_min,
                "te_min": cfg.te_min,
                "te_lookback": cfg.te_lookback,
                "pcmci_min_abs_partial": cfg.pcmci_min_abs_partial,
            },
            "implementation": _IMPLEMENTATION,
        },
    )
