#!/usr/bin/env python3
"""Shared OHLCV prior/feature maps for B-track prophecy walk-forward (Static LUT SSOT).

Mirrors ``run_prophecy_per_date_combo_walkforward_v1._prior_map`` / ``_feature_map`` so
pre-baked LUT JSON matches in-process walk-forward inputs. B-track / research_only only.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LUT = ROOT / "reports" / "btrack_ohlcv_feature_lut_v1_latest.json"
DEFAULT_KOSPI = ROOT / "research" / "market_data" / "kospi_daily_external_yf.csv"
DEFAULT_BTC = ROOT / "research" / "market_data" / "btc_daily_external_yf.csv"


def _ensure_root_on_path() -> None:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))


def prior_map_from_csv(csv_path: Path) -> dict[str, float]:
    """eval_date -> prior return (same as walk-forward ``_prior_map``)."""
    _ensure_root_on_path()
    from scripts.logos_shadow_eval_lib import load_kospi_yf_rows

    rows = load_kospi_yf_rows(csv_path)
    out: dict[str, float] = {}
    for i in range(2, len(rows)):
        ed = str(rows[i]["date"])[:10]
        try:
            c1 = float(rows[i - 1]["close"])
            c2 = float(rows[i - 2]["close"])
        except (TypeError, ValueError):
            continue
        if c2:
            out[ed] = (c1 - c2) / c2
    return out


def feature_map_from_csv(csv_path: Path) -> dict[str, dict[str, float]]:
    """eval_date -> expanded_prior feature dict (same as walk-forward ``_feature_map``)."""
    _ensure_root_on_path()
    from scripts.logos_shadow_eval_lib import load_kospi_yf_rows

    rows = load_kospi_yf_rows(csv_path)
    out: dict[str, dict[str, float]] = {}
    closes: list[float] = []
    dates: list[str] = []
    for r in rows:
        try:
            closes.append(float(r["close"]))
            dates.append(str(r["date"])[:10])
        except (TypeError, ValueError):
            continue

    for i in range(1, len(closes)):
        d = dates[i]
        c0 = closes[i - 1]
        if c0 == 0:
            continue
        ret_1 = (closes[i] - c0) / c0
        ret_3 = 0.0
        ret_5 = 0.0
        ret_10 = 0.0
        if i >= 3 and closes[i - 3] != 0:
            ret_3 = (closes[i - 1] - closes[i - 3]) / closes[i - 3]
        if i >= 5 and closes[i - 5] != 0:
            ret_5 = (closes[i - 1] - closes[i - 5]) / closes[i - 5]
        if i >= 10 and closes[i - 10] != 0:
            ret_10 = (closes[i - 1] - closes[i - 10]) / closes[i - 10]

        def _mean_abs_ret(k: int) -> float:
            if i < k:
                return 0.0
            vals: list[float] = []
            for j in range(i - k + 1, i + 1):
                pc = closes[j - 1]
                cc = closes[j]
                if pc == 0:
                    continue
                vals.append(abs((cc - pc) / pc))
            return (sum(vals) / len(vals)) if vals else 0.0

        out[d] = {
            "ret_1": ret_1,
            "ret_3": ret_3,
            "ret_5": ret_5,
            "ret_10": ret_10,
            "vol_3": _mean_abs_ret(3),
            "vol_10": _mean_abs_ret(10),
        }
    return out


def intersection_trading_dates(kospi_csv: Path, btc_csv: Path) -> list[str]:
    """Calendar dates present in both OHLCV series (dual-leg panel safe)."""
    _ensure_root_on_path()
    from scripts.logos_shadow_eval_lib import load_kospi_yf_rows

    k_dates = {str(r["date"])[:10] for r in load_kospi_yf_rows(kospi_csv)}
    b_dates = {str(r["date"])[:10] for r in load_kospi_yf_rows(btc_csv)}
    return sorted(k_dates & b_dates)


def build_lut_document(
    *,
    kospi_csv: Path,
    btc_csv: Path,
    generated_at_utc: str,
    last_n_intersection: int | None = None,
) -> dict[str, Any]:
    km = prior_map_from_csv(kospi_csv)
    bm = prior_map_from_csv(btc_csv)
    kf = feature_map_from_csv(kospi_csv)
    bf = feature_map_from_csv(btc_csv)
    intersection = intersection_trading_dates(kospi_csv, btc_csv)
    if last_n_intersection is not None and last_n_intersection > 0:
        intersection = intersection[-last_n_intersection:]

    def _slice_map(m: dict[str, Any]) -> dict[str, Any]:
        return {d: m[d] for d in intersection if d in m}

    return {
        "schema": "btrack_ohlcv_feature_lut_v1",
        "generated_at_utc": generated_at_utc,
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "inputs": {
            "kospi_csv": str(kospi_csv),
            "btc_csv": str(btc_csv),
            "calendar_mode": "kospi_btc_intersection",
            "last_n_intersection": last_n_intersection,
        },
        "stats": {
            "n_kospi_prior_dates": len(km),
            "n_btc_prior_dates": len(bm),
            "n_kospi_feature_dates": len(kf),
            "n_btc_feature_dates": len(bf),
            "n_intersection_dates": len(intersection),
        },
        "intersection_dates": intersection,
        "prior_by_instrument": {
            "kospi": _slice_map(km),
            "btc": _slice_map(bm),
        },
        "features_by_instrument": {
            "kospi": _slice_map(kf),
            "btc": _slice_map(bf),
        },
    }


def load_lut_document(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("schema") != "btrack_ohlcv_feature_lut_v1":
        raise ValueError(f"invalid LUT schema: {path}")
    return raw


def prior_and_feature_maps_from_lut(
    doc: dict[str, Any],
) -> tuple[dict[str, float], dict[str, float], dict[str, dict[str, float]], dict[str, dict[str, float]]]:
    prior = doc.get("prior_by_instrument") or {}
    feats = doc.get("features_by_instrument") or {}
    km = {str(k): float(v) for k, v in (prior.get("kospi") or {}).items()}
    bm = {str(k): float(v) for k, v in (prior.get("btc") or {}).items()}
    kf = {str(k): dict(v) for k, v in (feats.get("kospi") or {}).items() if isinstance(v, dict)}
    bf = {str(k): dict(v) for k, v in (feats.get("btc") or {}).items() if isinstance(v, dict)}
    return km, bm, kf, bf


def prior_maps_from_lut(doc: dict[str, Any]) -> tuple[dict[str, float], dict[str, float]]:
    km, bm, _, _ = prior_and_feature_maps_from_lut(doc)
    return km, bm


def ensure_lut_built(
    *,
    output: Path = DEFAULT_LUT,
    kospi_csv: Path = DEFAULT_KOSPI,
    btc_csv: Path = DEFAULT_BTC,
    last_n_intersection: int | None = 180,
) -> Path:
    """Run LUT builder subprocess; return output path on success."""
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "build_btrack_ohlcv_feature_lut_v1.py"),
        "--kospi-csv",
        str(kospi_csv),
        "--btc-csv",
        str(btc_csv),
        "--output",
        str(output),
    ]
    if last_n_intersection is not None and int(last_n_intersection) > 0:
        cmd.extend(["--last-n-intersection", str(int(last_n_intersection))])
    proc = subprocess.run(cmd, cwd=str(ROOT), check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"build_btrack_ohlcv_feature_lut_v1 exit {proc.returncode}")
    return output


FABBA_DIRECTION_CODE = {"bull": 1.0, "bear": -1.0, "neutral": 0.0}


def fabba_sidecar_row_to_numeric_features(row: dict[str, Any]) -> dict[str, float]:
    """Encode sidecar meta as float columns for LUT consumers (non-gating)."""
    out: dict[str, float] = {}
    pred = row.get("fabba_ngram_pred")
    if pred in FABBA_DIRECTION_CODE:
        out["fabba_ngram_pred_code"] = FABBA_DIRECTION_CODE[str(pred)]
    conf = row.get("fabba_ngram_confidence")
    if conf is not None:
        out["fabba_ngram_confidence"] = float(conf)
    slope = row.get("fabba_last_slope")
    if slope is not None:
        out["fabba_last_slope"] = float(slope)
    slope_pred = row.get("fabba_last_slope_pred")
    if slope_pred in FABBA_DIRECTION_CODE:
        out["fabba_last_slope_pred_code"] = FABBA_DIRECTION_CODE[str(slope_pred)]
    return out


def build_fabba_sidecar_maps_for_lut(
    *,
    kospi_csv: Path,
    btc_csv: Path,
    intersection_dates: list[str],
    lookback: int,
    ngram_size: int,
    tol: float,
    neutral_bps: float,
    backend: str,
    alpha: float = 0.1,
) -> dict[str, dict[str, dict[str, Any]]]:
    """Causal fabba sidecar rows keyed by instrument and intersection date."""
    _ensure_root_on_path()
    from scripts.prophecy_fabba_sidecar_lib_v1 import (
        build_causal_sidecar_feature_row,
        load_instrument_closes_series,
    )

    out: dict[str, dict[str, dict[str, Any]]] = {"kospi": {}, "btc": {}}
    for inst_id, csv_path in (("kospi", kospi_csv), ("btc", btc_csv)):
        dates, closes = load_instrument_closes_series(csv_path)
        date_to_idx = {d: i for i, d in enumerate(dates)}
        for d in intersection_dates:
            i = date_to_idx.get(d)
            if i is None:
                continue
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
                out[inst_id][d] = row
    return out


def merge_fabba_sidecar_into_lut_document(
    base_lut: dict[str, Any],
    *,
    sidecar_by_instrument: dict[str, dict[str, dict[str, Any]]],
    sidecar_params: dict[str, Any],
    revalidate_pointer: str | None = None,
    generated_at_utc: str,
) -> dict[str, Any]:
    """Read-only join: base OHLCV features unchanged; fabba numeric cols + sidecar meta added."""
    import copy

    merged = copy.deepcopy(base_lut)
    merged["schema"] = "btrack_ohlcv_feature_lut_with_fabba_sidecar_v1"
    merged["generated_at_utc"] = generated_at_utc
    merged["non_gating"] = True
    merged["send_gate"] = "HOLD"
    merged["base_lut_schema"] = base_lut.get("schema")
    merged["sidecar_params"] = sidecar_params
    merged["sidecar_revalidate_pointer"] = revalidate_pointer
    merged["sidecar_by_instrument"] = sidecar_by_instrument

    feats = merged.setdefault("features_by_instrument", {})
    n_merged = 0
    for inst_id in ("kospi", "btc"):
        inst_feats = feats.setdefault(inst_id, {})
        sidecar_map = sidecar_by_instrument.get(inst_id) or {}
        for d, row in sidecar_map.items():
            if d not in inst_feats:
                continue
            numeric = fabba_sidecar_row_to_numeric_features(row)
            if numeric:
                inst_feats[d] = {**inst_feats[d], **numeric}
                n_merged += 1

    stats = merged.setdefault("stats", {})
    stats["n_sidecar_feature_rows_merged"] = n_merged
    stats["n_sidecar_kospi_dates"] = len(sidecar_by_instrument.get("kospi") or {})
    stats["n_sidecar_btc_dates"] = len(sidecar_by_instrument.get("btc") or {})
    return merged


def load_merged_lut_document(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("schema") != "btrack_ohlcv_feature_lut_with_fabba_sidecar_v1":
        raise ValueError(f"invalid merged LUT schema: {path}")
    return raw


FABBA_FEATURE_KEYS = frozenset(
    {
        "fabba_ngram_pred_code",
        "fabba_ngram_confidence",
        "fabba_last_slope",
        "fabba_last_slope_pred_code",
    }
)


def strip_fabba_feature_keys(feats: dict[str, dict[str, Any]]) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for d, row in feats.items():
        if not isinstance(row, dict):
            continue
        out[str(d)] = {k: float(v) for k, v in row.items() if k not in FABBA_FEATURE_KEYS and isinstance(v, (int, float))}
    return out


def base_feature_parity_ok(base_lut: dict[str, Any], merged_lut: dict[str, Any]) -> tuple[bool, list[str]]:
    """Return (ok, mismatch_samples) comparing non-fabba feature columns on intersection dates."""
    _, _, kf_base, bf_base = prior_and_feature_maps_from_lut(base_lut)
    _, _, kf_m, bf_m = prior_and_feature_maps_from_lut(merged_lut)
    kf_strip = strip_fabba_feature_keys(kf_m)
    bf_strip = strip_fabba_feature_keys(bf_m)
    dates = list(base_lut.get("intersection_dates") or [])
    mismatches: list[str] = []
    for inst, base_map, strip_map in (("kospi", kf_base, kf_strip), ("btc", bf_base, bf_strip)):
        for d in dates:
            b = base_map.get(d)
            s = strip_map.get(d)
            if b is None and s is None:
                continue
            if b != s:
                mismatches.append(f"{inst}:{d}")
                if len(mismatches) >= 5:
                    return False, mismatches
    return len(mismatches) == 0, mismatches
