#!/usr/bin/env python3
"""[HYPO] fABBA symbolic sidecar helpers for prophecy blocked-WF shadow (B-track).

Pure-Python ``apca_stub`` runs without optional ``fABBA`` (Cython) dependency.
When ``fABBA`` is importable, ``fabba`` backend uses ``compress`` polygon pieces.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

VALID_DIRECTIONS = {"bull", "bear", "neutral"}


def fabba_dependency_probe() -> dict[str, Any]:
    try:
        ok = bool(importlib.util.find_spec("fABBA"))
    except Exception as exc:  # noqa: BLE001
        return {"status": "skipped_error", "error": str(exc)}
    if not ok:
        return {
            "status": "skipped_missing_dependency",
            "install_hint": "pip install fABBA (requires C++ build tools on Windows); apca_stub used instead",
        }
    return {"status": "dependency_ok"}


def actual_direction(ret: float, neutral_bps: float) -> str:
    thr = neutral_bps / 10000.0
    if ret > thr:
        return "bull"
    if ret < -thr:
        return "bear"
    return "neutral"


def direction_from_slope(slope: float, neutral_bps: float) -> str:
    return actual_direction(slope, neutral_bps)


def apca_pieces(values: list[float], tol: float) -> list[tuple[float, float, int]]:
    """Return list of (start_val, end_val, length) polygon pieces (pure Python APCA)."""
    if len(values) < 2:
        return []
    if tol <= 0:
        tol = 0.01
    pieces: list[tuple[float, float, int]] = []
    start_idx = 0
    n = len(values)
    while start_idx < n - 1:
        end_idx = start_idx + 1
        while end_idx < n:
            seg = values[start_idx : end_idx + 1]
            v0 = seg[0]
            v1 = seg[-1]
            if v0 == 0.0 and v1 == 0.0:
                end_idx += 1
                continue
            span = max(abs(v0), abs(v1), 1e-9)
            max_err = 0.0
            for j, v in enumerate(seg):
                t = j / max(len(seg) - 1, 1)
                interp = v0 + (v1 - v0) * t
                max_err = max(max_err, abs(v - interp) / span)
            if max_err > tol and end_idx > start_idx + 1:
                end_idx -= 1
                break
            if end_idx == n - 1:
                break
            end_idx += 1
        v_start = values[start_idx]
        v_end = values[end_idx]
        pieces.append((v_start, v_end, end_idx - start_idx + 1))
        start_idx = end_idx
    return pieces


def last_piece_slope(values: list[float], *, tol: float, backend: str) -> float | None:
    if len(values) < 2:
        return None
    if backend == "fabba":
        try:
            from fABBA import compress  # type: ignore[import-untyped]
        except Exception:  # noqa: BLE001
            backend = "apca_stub"
        else:
            pieces_raw = compress(list(values), tol=tol)
            if not pieces_raw:
                return None
            last = pieces_raw[-1]
            if isinstance(last, (list, tuple)) and len(last) >= 2:
                v0, v1 = float(last[0]), float(last[1])
            elif hasattr(last, "__getitem__"):
                v0, v1 = float(last[0]), float(last[-1])
            else:
                return None
            if v0 == 0.0:
                return None
            return (v1 - v0) / v0
    pieces = apca_pieces(values, tol)
    if not pieces:
        return None
    v0, v1, _ = pieces[-1]
    if v0 == 0.0:
        return None
    return (v1 - v0) / v0


def fabba_sidecar_pred(
    closes: list[float],
    idx: int,
    *,
    lookback: int,
    tol: float,
    neutral_bps: float,
    backend: str,
) -> str:
    if idx < 1:
        return "neutral"
    start = max(0, idx - lookback)
    window = closes[start:idx]
    if len(window) < 2:
        return "neutral"
    slope = last_piece_slope(window, tol=tol, backend=backend)
    if slope is None:
        return "neutral"
    return direction_from_slope(slope, neutral_bps)


def mom_pred(closes: list[float], idx: int, lookback: int, neutral_bps: float) -> str:
    if idx < lookback:
        return "neutral"
    c0 = closes[idx - lookback]
    c1 = closes[idx - 1]
    if c0 == 0.0:
        return "neutral"
    return actual_direction((c1 - c0) / c0, neutral_bps)


def blocked_folds(dates: list[str], n_folds: int) -> list[tuple[list[str], list[str]]]:
    n = len(dates)
    if n_folds < 2 or n < n_folds:
        return []
    base = n // n_folds
    rem = n % n_folds
    blocks: list[list[str]] = []
    idx = 0
    for b in range(n_folds):
        sz = base + (1 if b < rem else 0)
        blocks.append(dates[idx : idx + sz])
        idx += sz
    folds: list[tuple[list[str], list[str]]] = []
    for f in range(1, n_folds):
        train: list[str] = []
        for b in range(f):
            train.extend(blocks[b])
        test = blocks[f]
        if train and test:
            folds.append((train, test))
    return folds


def eval_direction_arm(
    dates: list[str],
    date_to_idx: dict[str, int],
    closes: list[float],
    *,
    test_dates: list[str],
    neutral_bps: float,
    predict_fn,
) -> dict[str, Any]:
    hits = n = 0
    dist: dict[str, int] = {"bull": 0, "bear": 0, "neutral": 0}
    for d in test_dates:
        i = date_to_idx.get(d)
        if i is None or i < 1:
            continue
        c0 = closes[i - 1]
        c1 = closes[i]
        if c0 == 0.0:
            continue
        ret = (c1 - c0) / c0
        if abs(ret) > 0.15:
            continue
        act = actual_direction(ret, neutral_bps)
        pred = predict_fn(i)
        if act == "neutral" and pred == "neutral":
            continue
        if act == "neutral" or pred == "neutral":
            continue
        n += 1
        dist[pred] = dist.get(pred, 0) + 1
        if pred == act:
            hits += 1
    return {
        "directional_hit_rate": round(hits / n, 6) if n else None,
        "n_evaluated": n,
        "price_hits": hits,
        "pred_distribution": dist,
    }


def aggregate_fold_metrics(fold_metrics: list[dict[str, Any]]) -> dict[str, Any]:
    rates = [f["directional_hit_rate"] for f in fold_metrics if f.get("directional_hit_rate") is not None]
    ns = [f["n_evaluated"] for f in fold_metrics if f.get("n_evaluated")]
    hits = sum(int(f.get("price_hits") or 0) for f in fold_metrics)
    total_n = sum(ns)
    dist: dict[str, int] = {"bull": 0, "bear": 0, "neutral": 0}
    for f in fold_metrics:
        pd = f.get("pred_distribution") or {}
        for k in dist:
            dist[k] += int(pd.get(k) or 0)
    return {
        "mean_test_directional_hit_rate": round(sum(rates) / len(rates), 6) if rates else None,
        "pooled_test_directional_hit_rate": round(hits / total_n, 6) if total_n else None,
        "fold_hit_rates": rates,
        "total_n_evaluated": total_n,
        "total_price_hits": hits,
        "n_folds_scored": len(rates),
        "pred_distribution": dist,
    }


def resolve_backend(requested: str) -> tuple[str, dict[str, Any]]:
    if requested == "apca_stub":
        return "apca_stub", {"backend": "apca_stub", "note": "pure Python APCA polygon stub"}
    if requested == "auto":
        probe = fabba_dependency_probe()
        if probe.get("status") == "dependency_ok":
            return "fabba", {"backend": "fabba", "fabba_probe": probe}
        return "apca_stub", {"backend": "apca_stub", "fabba_probe": probe, "fallback": True}
    if requested == "fabba":
        probe = fabba_dependency_probe()
        if probe.get("status") != "dependency_ok":
            return "apca_stub", {"backend": "apca_stub", "fabba_probe": probe, "fallback": True}
        return "fabba", {"backend": "fabba", "fabba_probe": probe}
    return "apca_stub", {"backend": "apca_stub", "unknown_requested": requested}


def _piece_slope_char(v0: float, v1: float, *, flat_thr: float = 1e-6) -> str:
    if v0 == 0.0:
        return "f"
    slope = (v1 - v0) / v0
    if slope > flat_thr:
        return "u"
    if slope < -flat_thr:
        return "d"
    return "f"


def symbolic_chain(
    values: list[float],
    *,
    tol: float,
    backend: str,
    alpha: float = 0.1,
) -> str:
    """Compress a price window to a symbolic string (fABBA or APCA stub)."""
    if len(values) < 2:
        return ""
    if backend == "fabba":
        try:
            from fABBA import fabba_model  # type: ignore[import-untyped]
        except Exception:  # noqa: BLE001
            backend = "apca_stub"
        else:
            try:
                model = fabba_model(tol=tol, alpha=alpha, sorting="2-norm", scl=1, verbose=0)
                return str(model.fit_transform(list(values)))
            except Exception:  # noqa: BLE001
                backend = "apca_stub"
    pieces = apca_pieces(values, tol)
    return "".join(_piece_slope_char(v0, v1) for v0, v1, _ in pieces)


class NgramPatternLut:
    """Train-only n-gram pattern → direction counts; reset per WF fold."""

    def __init__(self) -> None:
        self.lut: dict[str, dict[str, int]] = {}

    def clear(self) -> None:
        self.lut = {}

    def fit(
        self,
        closes: list[float],
        train_indices: list[int],
        *,
        lookback: int,
        ngram_size: int,
        tol: float,
        backend: str,
        neutral_bps: float,
        alpha: float = 0.1,
    ) -> None:
        self.clear()
        for i in sorted(set(train_indices)):
            if i < max(lookback, 2) or i >= len(closes):
                continue
            window = closes[max(0, i - lookback) : i]
            chain = symbolic_chain(window, tol=tol, backend=backend, alpha=alpha)
            if len(chain) < ngram_size:
                continue
            pattern = chain[-ngram_size:]
            c0 = closes[i - 1]
            c1 = closes[i]
            if c0 == 0.0:
                continue
            ret = (c1 - c0) / c0
            direction = actual_direction(ret, neutral_bps)
            bucket = self.lut.setdefault(pattern, {"bull": 0, "bear": 0, "neutral": 0})
            bucket[direction] = bucket.get(direction, 0) + 1

    def predict(
        self,
        closes: list[float],
        idx: int,
        *,
        lookback: int,
        ngram_size: int,
        tol: float,
        backend: str,
        alpha: float = 0.1,
    ) -> tuple[str, float]:
        if idx < lookback:
            return "neutral", 0.0
        window = closes[max(0, idx - lookback) : idx]
        chain = symbolic_chain(window, tol=tol, backend=backend, alpha=alpha)
        if len(chain) < ngram_size:
            return "neutral", 0.0
        pattern = chain[-ngram_size:]
        counts = self.lut.get(pattern)
        if not counts:
            return "neutral", 0.0
        total = sum(int(v) for v in counts.values())
        if total <= 0:
            return "neutral", 0.0
        pred = max(counts, key=lambda k: int(counts[k]))
        return pred, round(int(counts[pred]) / total, 6)


def build_causal_sidecar_feature_row(
    closes: list[float],
    idx: int,
    *,
    lookback: int,
    ngram_size: int,
    tol: float,
    backend: str,
    neutral_bps: float,
    alpha: float = 0.1,
) -> dict[str, Any]:
    """Per-date sidecar meta features using only ``closes[:idx]`` for LUT fit."""
    if idx < 1:
        return {}
    window = closes[max(0, idx - lookback) : idx] if idx >= lookback else closes[:idx]
    chain = symbolic_chain(window, tol=tol, backend=backend, alpha=alpha) if len(window) >= 2 else ""
    slope = last_piece_slope(window, tol=tol, backend=backend) if len(window) >= 2 else None
    slope_pred = direction_from_slope(slope, neutral_bps) if slope is not None else "neutral"

    lut = NgramPatternLut()
    train_indices = list(range(max(lookback, 2), idx))
    lut.fit(
        closes,
        train_indices,
        lookback=lookback,
        ngram_size=ngram_size,
        tol=tol,
        backend=backend,
        neutral_bps=neutral_bps,
        alpha=alpha,
    )
    ngram_pred, ngram_conf = lut.predict(
        closes,
        idx,
        lookback=lookback,
        ngram_size=ngram_size,
        tol=tol,
        backend=backend,
        alpha=alpha,
    )
    pattern = chain[-ngram_size:] if len(chain) >= ngram_size else chain
    row: dict[str, Any] = {
        "fabba_symbol_tail": chain[-min(8, len(chain)) :] if chain else "",
        "fabba_last_slope": round(slope, 8) if slope is not None else None,
        "fabba_last_slope_pred": slope_pred,
        "fabba_ngram_pattern": pattern,
        "fabba_ngram_pred": ngram_pred,
        "fabba_ngram_confidence": ngram_conf,
        "non_gating": True,
    }
    return row


def build_sidecar_feature_map(
    closes: list[float],
    dates: list[str],
    *,
    lookback: int,
    ngram_size: int,
    tol: float,
    backend: str,
    neutral_bps: float,
    alpha: float = 0.1,
) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for i, d in enumerate(dates):
        row = build_causal_sidecar_feature_row(
            closes,
            i,
            lookback=lookback,
            ngram_size=ngram_size,
            tol=tol,
            backend=backend,
            neutral_bps=neutral_bps,
            alpha=alpha,
        )
        if row:
            out[d] = row
    return out


def load_instrument_closes_series(csv_path: Path) -> tuple[list[str], list[float]]:
    from scripts.logos_shadow_eval_lib import load_kospi_yf_rows

    rows = load_kospi_yf_rows(csv_path)
    dates: list[str] = []
    closes: list[float] = []
    for r in rows:
        try:
            dates.append(str(r["date"])[:10])
            closes.append(float(r["close"]))
        except (TypeError, ValueError, KeyError):
            continue
    return dates, closes


def load_dual_leg_intersection_window(
    kospi_csv: Path,
    btc_csv: Path,
    *,
    last_n_intersection: int,
) -> dict[str, Any]:
    """Align KOSPI/BTC on calendar intersection; eval window = last N intersection dates."""
    from scripts.btrack_ohlcv_feature_lut_lib_v1 import intersection_trading_dates

    intersection = intersection_trading_dates(kospi_csv, btc_csv)
    if last_n_intersection > 0:
        intersection = intersection[-last_n_intersection:]
    if len(intersection) < 10:
        return {"status": "insufficient_intersection", "n_dates": len(intersection)}

    panels: dict[str, Any] = {}
    for inst_id, csv_path in (("kospi", kospi_csv), ("btc", btc_csv)):
        dates, closes = load_instrument_closes_series(csv_path)
        panels[inst_id] = {
            "dates": dates,
            "closes": closes,
            "date_to_idx": {d: i for i, d in enumerate(dates)},
        }
    return {
        "status": "ok",
        "intersection_dates": intersection,
        "eval_date_from": intersection[0],
        "eval_date_to": intersection[-1],
        "n_intersection_dates": len(intersection),
        "panels": panels,
    }


def run_blocked_wf_arms_for_panel(
    *,
    instrument_id: str,
    dates: list[str],
    closes: list[float],
    eval_dates: list[str],
    n_folds: int,
    neutral_bps: float,
    lookback: int,
    ngram_size: int,
    tol: float,
    backend: str,
    alpha: float,
) -> dict[str, Any]:
    """Blocked WF on eval_dates with per-fold LUT reset."""
    date_to_idx = {d: i for i, d in enumerate(dates)}
    eval_set = [d for d in eval_dates if d in date_to_idx]
    if len(eval_set) < n_folds:
        return {"instrument_id": instrument_id, "status": "insufficient_eval_dates", "n_dates": len(eval_set)}

    folds = blocked_folds(eval_set, n_folds)
    resolved_backend, backend_meta = resolve_backend(backend)

    fabba_fold_rows: list[dict[str, Any]] = []
    ngram_fold_rows: list[dict[str, Any]] = []
    mom_fold_rows: list[dict[str, Any]] = []

    for fi, (train, test) in enumerate(folds):
        train_indices = [date_to_idx[d] for d in train if d in date_to_idx]
        ngram_lut = NgramPatternLut()
        ngram_lut.fit(
            closes,
            train_indices,
            lookback=lookback,
            ngram_size=ngram_size,
            tol=tol,
            backend=resolved_backend,
            neutral_bps=neutral_bps,
            alpha=alpha,
        )

        def _fabba_pred(i: int) -> str:
            return fabba_sidecar_pred(
                closes,
                i,
                lookback=lookback,
                tol=tol,
                neutral_bps=neutral_bps,
                backend=resolved_backend,
            )

        def _ngram_pred(i: int) -> str:
            pred, _ = ngram_lut.predict(
                closes,
                i,
                lookback=lookback,
                ngram_size=ngram_size,
                tol=tol,
                backend=resolved_backend,
                alpha=alpha,
            )
            return pred

        def _mom_pred(i: int) -> str:
            return mom_pred(closes, i, lookback, neutral_bps)

        fabba_m = eval_direction_arm(
            dates, date_to_idx, closes, test_dates=test, neutral_bps=neutral_bps, predict_fn=_fabba_pred
        )
        ngram_m = eval_direction_arm(
            dates, date_to_idx, closes, test_dates=test, neutral_bps=neutral_bps, predict_fn=_ngram_pred
        )
        mom_m = eval_direction_arm(
            dates, date_to_idx, closes, test_dates=test, neutral_bps=neutral_bps, predict_fn=_mom_pred
        )
        fabba_fold_rows.append({"fold": fi, "test_dates": [test[0], test[-1]], **fabba_m})
        ngram_fold_rows.append(
            {"fold": fi, "test_dates": [test[0], test[-1]], "n_lut_patterns": len(ngram_lut.lut), **ngram_m}
        )
        mom_fold_rows.append({"fold": fi, "test_dates": [test[0], test[-1]], **mom_m})

    fabba_agg = aggregate_fold_metrics(fabba_fold_rows)
    ngram_agg = aggregate_fold_metrics(ngram_fold_rows)
    mom_agg = aggregate_fold_metrics(mom_fold_rows)
    return {
        "instrument_id": instrument_id,
        "status": "ok",
        "backend_meta": backend_meta,
        "neutral_bps": neutral_bps,
        "arms": [
            {
                "arm_id": "fabba_sidecar_last_slope",
                "model": f"symbolic_last_slope_{resolved_backend}",
                "protocol": "blocked_walkforward_test_only",
                "lookback_days": lookback,
                "tol": tol,
                **fabba_agg,
                "folds": fabba_fold_rows,
            },
            {
                "arm_id": "fabba_sidecar_ngram_lut",
                "model": f"symbolic_ngram_lut_{resolved_backend}",
                "protocol": "blocked_walkforward_test_only",
                "lookback_days": lookback,
                "ngram_size": ngram_size,
                "tol": tol,
                **ngram_agg,
                "folds": ngram_fold_rows,
            },
            {
                "arm_id": f"mom_{lookback}d",
                "model": f"classical_momentum_{lookback}d",
                "protocol": "blocked_walkforward_test_only",
                "lookback_days": lookback,
                **mom_agg,
                "folds": mom_fold_rows,
            },
        ],
    }


def pool_arms_across_instruments(per_inst: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sum hits/n across instruments (dual-leg pooled, apples-to-apples with n=360 style)."""
    by_arm: dict[str, dict[str, Any]] = {}
    for inst in per_inst:
        if inst.get("status") != "ok":
            continue
        for arm in inst.get("arms") or []:
            aid = str(arm.get("arm_id"))
            bucket = by_arm.setdefault(
                aid,
                {
                    "arm_id": aid,
                    "model": arm.get("model"),
                    "protocol": "blocked_walkforward_test_only_dual_leg_pooled",
                    "total_price_hits": 0,
                    "total_n_evaluated": 0,
                    "pred_distribution": {"bull": 0, "bear": 0, "neutral": 0},
                    "per_instrument": [],
                },
            )
            hits = int(arm.get("total_price_hits") or 0)
            n = int(arm.get("total_n_evaluated") or 0)
            bucket["total_price_hits"] += hits
            bucket["total_n_evaluated"] += n
            dist = arm.get("pred_distribution") or {}
            for k in ("bull", "bear", "neutral"):
                bucket["pred_distribution"][k] = bucket["pred_distribution"].get(k, 0) + int(dist.get(k) or 0)
            bucket["per_instrument"].append(
                {
                    "instrument_id": inst.get("instrument_id"),
                    "pooled_test_directional_hit_rate": arm.get("pooled_test_directional_hit_rate"),
                    "total_n_evaluated": n,
                    "total_price_hits": hits,
                }
            )
    out: list[dict[str, Any]] = []
    for _aid, bucket in sorted(by_arm.items()):
        total_n = bucket["total_n_evaluated"]
        total_hits = bucket["total_price_hits"]
        out.append(
            {
                **bucket,
                "pooled_test_directional_hit_rate": round(total_hits / total_n, 6) if total_n else None,
            }
        )
    return out


def build_sidecar_feature_lut_document(
    *,
    instrument_id: str,
    csv_path: Path,
    generated_at_utc: str,
    lookback: int,
    ngram_size: int,
    tol: float,
    backend: str,
    neutral_bps: float,
    eval_days: int = 0,
    alpha: float = 0.1,
) -> dict[str, Any]:
    from scripts.logos_shadow_eval_lib import load_kospi_yf_rows

    rows = load_kospi_yf_rows(csv_path)
    series: list[tuple[str, float]] = []
    for r in rows:
        try:
            series.append((str(r["date"])[:10], float(r["close"])))
        except (TypeError, ValueError, KeyError):
            continue
    if eval_days > 0:
        series = series[-eval_days:]
    dates = [d for d, _ in series]
    closes = [c for _, c in series]
    resolved_backend, backend_meta = resolve_backend(backend)
    features = build_sidecar_feature_map(
        closes,
        dates,
        lookback=lookback,
        ngram_size=ngram_size,
        tol=tol,
        backend=resolved_backend,
        neutral_bps=neutral_bps,
        alpha=alpha,
    )
    return {
        "schema": "prophecy_fabba_sidecar_feature_lut_v1",
        "generated_at_utc": generated_at_utc,
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "non_gating": True,
        "send_gate": "HOLD",
        "instrument_id": instrument_id,
        "inputs": {
            "csv": str(csv_path),
            "lookback": lookback,
            "ngram_size": ngram_size,
            "tol": tol,
            "neutral_bps": neutral_bps,
            "eval_days": eval_days,
            "backend_requested": backend,
        },
        "backend_meta": backend_meta,
        "stats": {
            "n_dates": len(dates),
            "n_feature_rows": len(features),
            "date_from": dates[0] if dates else None,
            "date_to": dates[-1] if dates else None,
        },
        "features_by_date": features,
    }


def compare_symbolic_backends_on_eval_points(
    *,
    dates: list[str],
    closes: list[float],
    eval_dates: list[str],
    lookback: int,
    tol: float,
    alpha: float = 0.1,
) -> dict[str, Any]:
    """Compare apca_stub vs fabba symbolic chains on causal windows (no lookahead)."""
    probe = fabba_dependency_probe()
    fabba_ok = probe.get("status") == "dependency_ok"
    date_to_idx = {d: i for i, d in enumerate(dates)}
    compared = 0
    exact_match = 0
    slope_sign_match = 0
    chain_len_stub: list[int] = []
    chain_len_fabba: list[int] = []
    samples: list[dict[str, Any]] = []

    for ed in eval_dates:
        idx = date_to_idx.get(ed)
        if idx is None or idx < 2:
            continue
        window = closes[max(0, idx - lookback) : idx] if idx >= lookback else closes[:idx]
        if len(window) < 2:
            continue
        chain_stub = symbolic_chain(window, tol=tol, backend="apca_stub", alpha=alpha)
        chain_len_stub.append(len(chain_stub))
        stub_slope = last_piece_slope(window, tol=tol, backend="apca_stub")
        fabba_slope = None
        chain_fabba = None
        if fabba_ok:
            chain_fabba = symbolic_chain(window, tol=tol, backend="fabba", alpha=alpha)
            fabba_slope = last_piece_slope(window, tol=tol, backend="fabba")
            chain_len_fabba.append(len(chain_fabba))
            compared += 1
            if chain_stub == chain_fabba:
                exact_match += 1
            if stub_slope is not None and fabba_slope is not None:
                if (stub_slope > 0) == (fabba_slope > 0) or (stub_slope == 0 and fabba_slope == 0):
                    slope_sign_match += 1
            if len(samples) < 5 and chain_stub != chain_fabba:
                samples.append(
                    {
                        "eval_date": ed,
                        "chain_apca_stub": chain_stub,
                        "chain_fabba": chain_fabba,
                    }
                )

    def _mean(xs: list[int]) -> float | None:
        return round(sum(xs) / len(xs), 4) if xs else None

    return {
        "fabba_probe": probe,
        "fabba_available": fabba_ok,
        "n_eval_points": len(chain_len_stub),
        "n_compared_fabba": compared,
        "exact_chain_match_rate": round(exact_match / compared, 6) if compared else None,
        "last_slope_sign_match_rate": round(slope_sign_match / compared, 6) if compared else None,
        "mean_chain_len_apca_stub": _mean(chain_len_stub),
        "mean_chain_len_fabba": _mean(chain_len_fabba),
        "mismatch_samples": samples,
    }
