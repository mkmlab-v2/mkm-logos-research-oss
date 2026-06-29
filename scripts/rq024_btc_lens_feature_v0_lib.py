#!/usr/bin/env python3
"""RQ-024 B-track: BTC lens causal OHLC feature v0/v1 (promotion-legal, no expanded-prior)."""
from __future__ import annotations

import itertools
from pathlib import Path
from typing import Any, Literal

from scripts.btrack_causal_ohlc_features_v1 import (
    build_causal_feature_map,
    load_btc_ohlc_by_date,
)
from scripts.run_prophecy_per_date_combo_walkforward_v1 import (
    _acc,
    _best_params_on_train,
    _feature_map,
    _params_to_dict,
    _predict,
    _prior_map,
    _sign,
)

CEILING_BASELINE_ACCURACY = 0.52
CEILING_VARIANT = "nf6_margin_vs_bull_nosrc"


def causal_feature_map(csv_path: Path) -> dict[str, dict[str, float | bool]]:
    if not csv_path.is_file():
        return {}
    return build_causal_feature_map(load_btc_ohlc_by_date(csv_path))


def _causal_delta(
    row: dict[str, Any],
    causal: dict[str, dict[str, float | bool]],
    *,
    w_ovn: float,
    w_pr: float,
    w_dd: float,
    dz: float = 0.01,
) -> float:
    ed = str(row.get("eval_date") or "").strip()[:10]
    feat = causal.get(ed) or {}
    ovn = float(feat.get("overnight_return") or 0.0)
    pr = float(feat.get("prior_range_position") or 0.5) - 0.5
    dd = float(feat.get("drawdown_20d") or 0.0)
    delta = 0.0
    delta += w_ovn * _sign(ovn, dz)
    delta += w_pr * _sign(pr, 0.05)
    delta += w_dd * _sign(dd, dz)
    if bool(feat.get("vol_regime_high")):
        delta += w_ovn * 0.25
    return delta


def _causal_delta_v1(
    row: dict[str, Any],
    causal: dict[str, dict[str, float | bool]],
    *,
    w_ovn: float,
    w_pr: float,
    w_dd: float,
    w_ldr: float,
    w_vol5: float,
    dz: float = 0.01,
    vol_center: float = 0.03,
) -> float:
    ed = str(row.get("eval_date") or "").strip()[:10]
    feat = causal.get(ed) or {}
    ovn = float(feat.get("overnight_return") or 0.0)
    pr = float(feat.get("prior_range_position") or 0.5) - 0.5
    dd = float(feat.get("drawdown_20d") or 0.0)
    ldr = float(feat.get("last_daily_return") or 0.0)
    vol5 = float(feat.get("realized_vol_5d") or 0.0)
    delta = 0.0
    delta += w_ovn * _sign(ovn, dz)
    delta += w_pr * _sign(pr, 0.05)
    delta += w_dd * _sign(dd, dz)
    delta += w_ldr * _sign(ldr, dz)
    delta += w_vol5 * _sign(vol5 - vol_center, 0.005)
    if bool(feat.get("vol_regime_high")):
        delta += w_ovn * 0.25
    return delta


OverlayVersion = Literal["none", "v0", "v1", "v2"]


def predict_with_causal_overlay(
    row: dict[str, Any],
    params: tuple[float, ...],
    km: dict[str, float],
    bm: dict[str, float],
    kf: dict[str, dict[str, float]],
    bf: dict[str, dict[str, float]],
    causal: dict[str, dict[str, float | bool]],
    *,
    include_source_direction_signal: bool,
    causal_weights: tuple[float, float, float],
) -> str:
    base = _predict(
        row,
        params,
        km,
        bm,
        kf,
        bf,
        include_source_direction_signal=include_source_direction_signal,
        include_expanded_prior_features=False,
    )
    w_ovn, w_pr, w_dd = causal_weights
    if w_ovn == 0.0 and w_pr == 0.0 and w_dd == 0.0:
        return base
    ed = str(row.get("eval_date") or "").strip()[:10]
    inst = str(row.get("instrument") or "").strip().lower()
    if inst != "btc":
        return base
    delta = _causal_delta(row, causal, w_ovn=w_ovn, w_pr=w_pr, w_dd=w_dd)
    if delta > 0.25:
        return "bull"
    if delta < -0.25:
        return "bear"
    return base


def acc_with_causal_overlay(
    rows: list[dict[str, Any]],
    params: tuple[float, ...],
    km: dict[str, float],
    bm: dict[str, float],
    kf: dict[str, dict[str, float]],
    bf: dict[str, dict[str, float]],
    causal: dict[str, dict[str, float | bool]],
    *,
    include_source_direction_signal: bool,
    causal_weights: tuple[float, float, float],
) -> tuple[float, int]:
    hits = 0
    for r in rows:
        pred = predict_with_causal_overlay(
            r,
            params,
            km,
            bm,
            kf,
            bf,
            causal,
            include_source_direction_signal=include_source_direction_signal,
            causal_weights=causal_weights,
        )
        if pred == str(r.get("actual_direction") or "").strip().lower():
            hits += 1
    return (hits / len(rows)) if rows else 0.0, hits


def best_causal_weights_on_train(
    train_rows: list[dict[str, Any]],
    params: tuple[float, ...],
    km: dict[str, float],
    bm: dict[str, float],
    kf: dict[str, dict[str, float]],
    bf: dict[str, dict[str, float]],
    causal: dict[str, dict[str, float | bool]],
    *,
    include_source_direction_signal: bool,
    train_objective: str,
) -> tuple[tuple[float, float, float], float]:
    bull_train = (
        sum(1 for r in train_rows if str(r.get("actual_direction") or "").strip().lower() == "bull")
        / len(train_rows)
        if train_rows
        else 0.0
    )
    weight_grid = [-1.0, 0.0, 1.0]
    best_w: tuple[float, float, float] = (0.0, 0.0, 0.0)
    best_primary = -1.0
    best_secondary = -1.0
    for w in itertools.product(weight_grid, repeat=3):
        a, _ = acc_with_causal_overlay(
            train_rows,
            params,
            km,
            bm,
            kf,
            bf,
            causal,
            include_source_direction_signal=include_source_direction_signal,
            causal_weights=w,
        )
        if train_objective == "margin_vs_bull":
            primary = a - bull_train
            secondary = a
        else:
            primary = a
            secondary = a - bull_train
        if primary > best_primary or (primary == best_primary and secondary > best_secondary):
            best_primary = primary
            best_secondary = secondary
            best_w = w
    return best_w, best_secondary


def predict_with_causal_overlay_v1(
    row: dict[str, Any],
    params: tuple[float, ...],
    km: dict[str, float],
    bm: dict[str, float],
    kf: dict[str, dict[str, float]],
    bf: dict[str, dict[str, float]],
    causal: dict[str, dict[str, float | bool]],
    *,
    include_source_direction_signal: bool,
    causal_weights: tuple[float, float, float, float, float],
) -> str:
    base = _predict(
        row,
        params,
        km,
        bm,
        kf,
        bf,
        include_source_direction_signal=include_source_direction_signal,
        include_expanded_prior_features=False,
    )
    w_ovn, w_pr, w_dd, w_ldr, w_vol5 = causal_weights
    if all(w == 0.0 for w in causal_weights):
        return base
    inst = str(row.get("instrument") or "").strip().lower()
    if inst != "btc":
        return base
    delta = _causal_delta_v1(
        row, causal, w_ovn=w_ovn, w_pr=w_pr, w_dd=w_dd, w_ldr=w_ldr, w_vol5=w_vol5
    )
    if delta > 0.25:
        return "bull"
    if delta < -0.25:
        return "bear"
    return base


def acc_with_causal_overlay_v1(
    rows: list[dict[str, Any]],
    params: tuple[float, ...],
    km: dict[str, float],
    bm: dict[str, float],
    kf: dict[str, dict[str, float]],
    bf: dict[str, dict[str, float]],
    causal: dict[str, dict[str, float | bool]],
    *,
    include_source_direction_signal: bool,
    causal_weights: tuple[float, float, float, float, float],
) -> tuple[float, int]:
    hits = 0
    for r in rows:
        pred = predict_with_causal_overlay_v1(
            r,
            params,
            km,
            bm,
            kf,
            bf,
            causal,
            include_source_direction_signal=include_source_direction_signal,
            causal_weights=causal_weights,
        )
        if pred == str(r.get("actual_direction") or "").strip().lower():
            hits += 1
    return (hits / len(rows)) if rows else 0.0, hits


def best_causal_weights_v1_on_train(
    train_rows: list[dict[str, Any]],
    params: tuple[float, ...],
    km: dict[str, float],
    bm: dict[str, float],
    kf: dict[str, dict[str, float]],
    bf: dict[str, dict[str, float]],
    causal: dict[str, dict[str, float | bool]],
    *,
    include_source_direction_signal: bool,
    train_objective: str,
) -> tuple[tuple[float, float, float, float, float], float]:
    bull_train = (
        sum(1 for r in train_rows if str(r.get("actual_direction") or "").strip().lower() == "bull")
        / len(train_rows)
        if train_rows
        else 0.0
    )
    weight_grid = [-1.0, 0.0, 1.0]
    best_w: tuple[float, float, float, float, float] = (0.0, 0.0, 0.0, 0.0, 0.0)
    best_primary = -1.0
    best_secondary = -1.0
    for w in itertools.product(weight_grid, repeat=5):
        a, _ = acc_with_causal_overlay_v1(
            train_rows,
            params,
            km,
            bm,
            kf,
            bf,
            causal,
            include_source_direction_signal=include_source_direction_signal,
            causal_weights=w,
        )
        if train_objective == "margin_vs_bull":
            primary = a - bull_train
            secondary = a
        else:
            primary = a
            secondary = a - bull_train
        if primary > best_primary or (primary == best_primary and secondary > best_secondary):
            best_primary = primary
            best_secondary = secondary
            best_w = w
    return best_w, best_secondary


def _causal_delta_v2(
    row: dict[str, Any],
    causal: dict[str, dict[str, float | bool]],
    *,
    w_ovn: float,
    w_pr: float,
    w_dd: float,
    w_ldr: float,
    w_vol5: float,
    w_vol_ratio: float,
    w_pir: float,
    dz: float = 0.01,
    vol_center: float = 0.03,
    vol_ratio_center: float = 1.0,
) -> float:
    ed = str(row.get("eval_date") or "").strip()[:10]
    feat = causal.get(ed) or {}
    ovn = float(feat.get("overnight_return") or 0.0)
    pr = float(feat.get("prior_range_position") or 0.5) - 0.5
    dd = float(feat.get("drawdown_20d") or 0.0)
    ldr = float(feat.get("last_daily_return") or 0.0)
    vol5 = float(feat.get("realized_vol_5d") or 0.0)
    vol_ratio = float(feat.get("volume_ratio_5d") or 1.0)
    pir = float(feat.get("prior_intraday_range") or 0.0)
    delta = 0.0
    delta += w_ovn * _sign(ovn, dz)
    delta += w_pr * _sign(pr, 0.05)
    delta += w_dd * _sign(dd, dz)
    delta += w_ldr * _sign(ldr, dz)
    delta += w_vol5 * _sign(vol5 - vol_center, 0.005)
    delta += w_vol_ratio * _sign(vol_ratio - vol_ratio_center, 0.1)
    delta += w_pir * _sign(pir - 0.02, 0.005)
    if bool(feat.get("vol_regime_high")):
        delta += w_ovn * 0.25
    return delta


def predict_with_causal_overlay_v2(
    row: dict[str, Any],
    params: tuple[float, ...],
    km: dict[str, float],
    bm: dict[str, float],
    kf: dict[str, dict[str, float]],
    bf: dict[str, dict[str, float]],
    causal: dict[str, dict[str, float | bool]],
    *,
    include_source_direction_signal: bool,
    causal_weights: tuple[float, float, float, float, float, float, float],
) -> str:
    base = _predict(
        row,
        params,
        km,
        bm,
        kf,
        bf,
        include_source_direction_signal=include_source_direction_signal,
        include_expanded_prior_features=False,
    )
    if all(w == 0.0 for w in causal_weights):
        return base
    inst = str(row.get("instrument") or "").strip().lower()
    if inst != "btc":
        return base
    w_ovn, w_pr, w_dd, w_ldr, w_vol5, w_vol_ratio, w_pir = causal_weights
    delta = _causal_delta_v2(
        row,
        causal,
        w_ovn=w_ovn,
        w_pr=w_pr,
        w_dd=w_dd,
        w_ldr=w_ldr,
        w_vol5=w_vol5,
        w_vol_ratio=w_vol_ratio,
        w_pir=w_pir,
    )
    if delta > 0.25:
        return "bull"
    if delta < -0.25:
        return "bear"
    return base


def acc_with_causal_overlay_v2(
    rows: list[dict[str, Any]],
    params: tuple[float, ...],
    km: dict[str, float],
    bm: dict[str, float],
    kf: dict[str, dict[str, float]],
    bf: dict[str, dict[str, float]],
    causal: dict[str, dict[str, float | bool]],
    *,
    include_source_direction_signal: bool,
    causal_weights: tuple[float, float, float, float, float, float, float],
) -> tuple[float, int]:
    hits = 0
    for r in rows:
        pred = predict_with_causal_overlay_v2(
            r,
            params,
            km,
            bm,
            kf,
            bf,
            causal,
            include_source_direction_signal=include_source_direction_signal,
            causal_weights=causal_weights,
        )
        if pred == str(r.get("actual_direction") or "").strip().lower():
            hits += 1
    return (hits / len(rows)) if rows else 0.0, hits


def best_causal_weights_v2_on_train(
    train_rows: list[dict[str, Any]],
    params: tuple[float, ...],
    km: dict[str, float],
    bm: dict[str, float],
    kf: dict[str, dict[str, float]],
    bf: dict[str, dict[str, float]],
    causal: dict[str, dict[str, float | bool]],
    *,
    include_source_direction_signal: bool,
    train_objective: str,
) -> tuple[tuple[float, float, float, float, float, float, float], float]:
    bull_train = (
        sum(1 for r in train_rows if str(r.get("actual_direction") or "").strip().lower() == "bull")
        / len(train_rows)
        if train_rows
        else 0.0
    )
    weight_grid = [-1.0, 0.0, 1.0]
    best_w: tuple[float, float, float, float, float, float, float] = (0.0,) * 7
    best_primary = -1.0
    best_secondary = -1.0
    for w in itertools.product(weight_grid, repeat=7):
        a, _ = acc_with_causal_overlay_v2(
            train_rows,
            params,
            km,
            bm,
            kf,
            bf,
            causal,
            include_source_direction_signal=include_source_direction_signal,
            causal_weights=w,
        )
        if train_objective == "margin_vs_bull":
            primary = a - bull_train
            secondary = a
        else:
            primary = a
            secondary = a - bull_train
        if primary > best_primary or (primary == best_primary and secondary > best_secondary):
            best_primary = primary
            best_secondary = secondary
            best_w = w
    return best_w, best_secondary


def fit_baseline_nf6_on_train(
    train_rows: list[dict[str, Any]],
    km: dict[str, float],
    bm: dict[str, float],
    kf: dict[str, dict[str, float]],
    bf: dict[str, dict[str, float]],
    *,
    train_objective: str,
) -> tuple[tuple[float, ...] | None, float]:
    """Promotion-legal baseline: source-direction on, expanded-prior off."""
    fitted = _best_params_on_train(
        train_rows,
        km,
        bm,
        kf,
        bf,
        train_objective=train_objective,
        include_source_direction_signal=True,
        include_expanded_prior_features=False,
    )
    if fitted is None:
        return None, 0.0
    train_acc, params = fitted
    return params, train_acc


def run_rq024_blind_variant(
    *,
    slug: str,
    train: list[dict[str, Any]],
    test: list[dict[str, Any]],
    km: dict[str, float],
    bm: dict[str, float],
    kf: dict[str, dict[str, float]],
    bf: dict[str, dict[str, float]],
    causal: dict[str, dict[str, float | bool]],
    train_objective: str,
    overlay_version: OverlayVersion = "none",
    use_causal_overlay: bool | None = None,
) -> dict[str, Any]:
    if use_causal_overlay is not None and overlay_version == "none":
        overlay_version = "v0" if use_causal_overlay else "none"

    params, _ = fit_baseline_nf6_on_train(
        train, km, bm, kf, bf, train_objective=train_objective
    )
    if params is None:
        return {"slug": slug, "error": "no_baseline_train_candidate"}

    causal_w_v0 = (0.0, 0.0, 0.0)
    causal_w_v1 = (0.0, 0.0, 0.0, 0.0, 0.0)
    causal_w_v2 = (0.0,) * 7
    if overlay_version == "v0":
        causal_w_v0, _ = best_causal_weights_on_train(
            train,
            params,
            km,
            bm,
            kf,
            bf,
            causal,
            include_source_direction_signal=True,
            train_objective=train_objective,
        )
    elif overlay_version == "v1":
        causal_w_v1, _ = best_causal_weights_v1_on_train(
            train,
            params,
            km,
            bm,
            kf,
            bf,
            causal,
            include_source_direction_signal=True,
            train_objective=train_objective,
        )
    elif overlay_version == "v2":
        causal_w_v2, _ = best_causal_weights_v2_on_train(
            train,
            params,
            km,
            bm,
            kf,
            bf,
            causal,
            include_source_direction_signal=True,
            train_objective=train_objective,
        )

    def _score(rows: list[dict[str, Any]]) -> tuple[float, int]:
        if overlay_version == "v0":
            return acc_with_causal_overlay(
                rows,
                params,
                km,
                bm,
                kf,
                bf,
                causal,
                include_source_direction_signal=True,
                causal_weights=causal_w_v0,
            )
        if overlay_version == "v1":
            return acc_with_causal_overlay_v1(
                rows,
                params,
                km,
                bm,
                kf,
                bf,
                causal,
                include_source_direction_signal=True,
                causal_weights=causal_w_v1,
            )
        if overlay_version == "v2":
            return acc_with_causal_overlay_v2(
                rows,
                params,
                km,
                bm,
                kf,
                bf,
                causal,
                include_source_direction_signal=True,
                causal_weights=causal_w_v2,
            )
        return _acc(
            rows,
            params,
            km,
            bm,
            kf,
            bf,
            include_source_direction_signal=True,
            include_expanded_prior_features=False,
        )

    train_acc, train_hit = _score(train)
    test_acc, test_hit = _score(test)
    bull_test = (
        sum(1 for r in test if str(r.get("actual_direction") or "").strip().lower() == "bull") / len(test)
        if test
        else 0.0
    )
    out: dict[str, Any] = {
        "slug": slug,
        "baseline_variant": CEILING_VARIANT,
        "include_expanded_prior_features": False,
        "overlay_version": overlay_version,
        "use_causal_overlay_v0": overlay_version == "v0",
        "use_causal_overlay_v1": overlay_version == "v1",
        "use_causal_overlay_v2": overlay_version == "v2",
        "best_baseline_params_from_train": _params_to_dict(
            params,
            include_source_direction_signal=True,
            include_expanded_prior_features=False,
        ),
        "train": {
            "accuracy": round(train_acc, 6),
            "hits": train_hit,
            "n": len(train),
        },
        "test_blind": {
            "accuracy": round(test_acc, 6),
            "hits": test_hit,
            "n": len(test),
            "always_bull_control": round(bull_test, 6),
            "margin_vs_bull": round(test_acc - bull_test, 6),
            "beats_ceiling_052": test_acc > CEILING_BASELINE_ACCURACY,
            "gate_055_pass": test_acc >= 0.55,
        },
    }
    if overlay_version == "v0":
        out["causal_weights_v0"] = {
            "w_overnight": causal_w_v0[0],
            "w_prior_range_centered": causal_w_v0[1],
            "w_drawdown_20d": causal_w_v0[2],
        }
    if overlay_version == "v1":
        out["causal_weights_v1"] = {
            "w_overnight": causal_w_v1[0],
            "w_prior_range_centered": causal_w_v1[1],
            "w_drawdown_20d": causal_w_v1[2],
            "w_last_daily_return": causal_w_v1[3],
            "w_realized_vol_5d": causal_w_v1[4],
        }
    if overlay_version == "v2":
        out["causal_weights_v2"] = {
            "w_overnight": causal_w_v2[0],
            "w_prior_range_centered": causal_w_v2[1],
            "w_drawdown_20d": causal_w_v2[2],
            "w_last_daily_return": causal_w_v2[3],
            "w_realized_vol_5d": causal_w_v2[4],
            "w_volume_ratio_5d": causal_w_v2[5],
            "w_prior_intraday_range": causal_w_v2[6],
        }
    return out


def chronological_cut_splits(
    dates_sorted: list[str],
    *,
    cut_fracs: tuple[float, ...] = (0.25, 0.33, 0.40, 0.50, 0.60, 0.67),
    min_train: int = 30,
    min_test: int = 30,
) -> list[tuple[str, list[str], list[str]]]:
    """Return (split_id, train_dates, test_dates) for each chronological cut fraction."""
    n = len(dates_sorted)
    out: list[tuple[str, list[str], list[str]]] = []
    for frac in cut_fracs:
        k = max(min_train, int(n * frac))
        k = min(k, n - min_test)
        if k < min_train or (n - k) < min_test:
            continue
        train = dates_sorted[:k]
        test = dates_sorted[k:]
        sid = f"cut_{int(frac * 100):02d}pct"
        out.append((sid, train, test))
    return out


def blocked_walkforward_eval(
    rows: list[dict[str, Any]],
    dates_sorted: list[str],
    *,
    n_folds: int,
    km: dict[str, float],
    bm: dict[str, float],
    kf: dict[str, dict[str, float]],
    bf: dict[str, dict[str, float]],
    causal: dict[str, dict[str, float | bool]],
    train_objective: str,
) -> dict[str, Any]:
    from scripts.run_prophecy_per_date_combo_walkforward_v1 import _blocked_walkforward_folds

    fold_specs = _blocked_walkforward_folds(dates_sorted, n_folds)
    baseline_folds: list[dict[str, Any]] = []
    v0_folds: list[dict[str, Any]] = []
    v1_folds: list[dict[str, Any]] = []
    for fi, (train_dates, test_dates) in enumerate(fold_specs):
        train_set = set(train_dates)
        test_set = set(test_dates)
        train = [r for r in rows if str(r.get("eval_date"))[:10] in train_set]
        test = [r for r in rows if str(r.get("eval_date"))[:10] in test_set]
        if not train or not test:
            continue
        common = dict(
            train=train,
            test=test,
            km=km,
            bm=bm,
            kf=kf,
            bf=bf,
            causal=causal,
            train_objective=train_objective,
        )
        b = run_rq024_blind_variant(slug=f"fold{fi}_baseline", overlay_version="none", **common)
        v0 = run_rq024_blind_variant(slug=f"fold{fi}_rq024_v0", overlay_version="v0", **common)
        v1 = run_rq024_blind_variant(slug=f"fold{fi}_rq024_v1", overlay_version="v1", **common)
        baseline_folds.append({"fold_index": fi, **b})
        v0_folds.append({"fold_index": fi, **v0})
        v1_folds.append({"fold_index": fi, **v1})

    def _agg(folds: list[dict[str, Any]]) -> dict[str, Any]:
        accs = [
            float((f.get("test_blind") or {}).get("accuracy"))
            for f in folds
            if isinstance((f.get("test_blind") or {}).get("accuracy"), (int, float))
        ]
        beats = sum(1 for f in folds if (f.get("test_blind") or {}).get("beats_ceiling_052"))
        gate = sum(1 for f in folds if (f.get("test_blind") or {}).get("gate_055_pass"))
        if not accs:
            return {"n_folds": 0}
        mean = sum(accs) / len(accs)
        var = sum((x - mean) ** 2 for x in accs) / len(accs)
        return {
            "n_folds": len(accs),
            "mean_test_accuracy": round(mean, 6),
            "stdev_test_accuracy": round(var**0.5, 6),
            "min_test_accuracy": round(min(accs), 6),
            "max_test_accuracy": round(max(accs), 6),
            "fraction_test_beats_ceiling_052": round(beats / len(accs), 6),
            "fraction_test_gate_055_pass": round(gate / len(accs), 6),
            "gate_055_pass_all_folds": gate == len(accs) and len(accs) > 0,
        }

    return {
        "n_folds_requested": n_folds,
        "n_walkforward_folds": len(baseline_folds),
        "baseline_nf6_srcdir": {"folds": baseline_folds, "aggregate": _agg(baseline_folds)},
        "rq024_causal_lens_v0": {"folds": v0_folds, "aggregate": _agg(v0_folds)},
        "rq024_causal_lens_v1": {"folds": v1_folds, "aggregate": _agg(v1_folds)},
    }
