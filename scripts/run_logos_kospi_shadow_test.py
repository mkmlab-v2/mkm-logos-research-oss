#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run L2 logos KOSPI shadow test (observation only)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "research" / "market_data" / "kospi_crash_samples.json"
DEFAULT_LENS = ROOT / "docs" / "final" / "artifacts" / "logos_independent_lens_latest.json"
DEFAULT_OUT_DIR = ROOT / "reports" / "research" / "logos_shadow_v1"
OBSERVATION_ONLY = True


def _read_json(path: Path) -> dict[str, Any] | list[Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _pct_drop_from_peak(closes: list[float], idx: int, lookback: int) -> float:
    left = max(0, idx - lookback + 1)
    peak = max(closes[left : idx + 1])
    if peak <= 0:
        return 0.0
    return (closes[idx] / peak) - 1.0


def _crash_start_labels(closes: list[float], lookback_peak: int, horizon: int, drop_threshold: float) -> list[bool]:
    n = len(closes)
    labels = [False] * n
    last_marked = -999999
    for t in range(n):
        peak = max(closes[max(0, t - lookback_peak + 1) : t + 1])
        trigger = False
        for k in range(1, horizon + 1):
            j = t + k
            if j >= n:
                break
            if peak > 0 and ((closes[j] / peak) - 1.0) <= drop_threshold:
                trigger = True
                break
        if trigger and (t - last_marked) > horizon:
            labels[t] = True
            last_marked = t
    return labels


def _multi_event_labels(
    closes: list[float],
    lookback_peak: int,
    horizon: int,
    drop_threshold: float,
    streak_days: int,
    streak_threshold: float,
    vol_window: int,
    vol_threshold: float,
) -> list[bool]:
    """Union label of crash/drop, down-streak, and volatility-break events."""
    n = len(closes)
    base = _crash_start_labels(closes, lookback_peak, horizon, drop_threshold)
    labels = base[:]
    for i in range(n):
        # Event B: sustained down-streak over recent N days
        if i >= streak_days:
            ref = closes[i - streak_days]
            if ref > 0:
                ret = (closes[i] / ref) - 1.0
                if ret <= streak_threshold:
                    labels[i] = True
        # Event C: volatility break + local down move
        if i > 1:
            v = _recent_volatility(closes, i, vol_window)
            d1 = (closes[i] / closes[i - 1] - 1.0) if closes[i - 1] > 0 else 0.0
            if v >= vol_threshold and d1 < 0:
                labels[i] = True
    # Debounce adjacent labels to keep event counting stable
    out = [False] * n
    last = -999999
    for i, v in enumerate(labels):
        if not v:
            continue
        if i - last > max(1, horizon // 2):
            out[i] = True
            last = i
    return out


def _cycle_resonance(index: int, cycle_priority: list[int]) -> float:
    # Priority weight decays by order: first cycle strongest.
    total = 0.0
    weight_sum = 0.0
    for rank, c in enumerate(cycle_priority):
        if c <= 0:
            continue
        w = 1.0 / float(rank + 1)
        rem = index % c
        near = rem in (0, 1, c - 1)
        val = 1.0 if near else -0.35
        total += w * val
        weight_sum += w
    if weight_sum <= 0:
        return 0.0
    return max(-1.0, min(1.0, total / weight_sum))


def _recent_volatility(closes: list[float], idx: int, window: int) -> float:
    if window <= 1 or idx <= 0:
        return 0.0
    left = max(1, idx - window + 1)
    rets: list[float] = []
    for j in range(left, idx + 1):
        prev = closes[j - 1]
        cur = closes[j]
        if prev > 0:
            rets.append((cur / prev) - 1.0)
    if not rets:
        return 0.0
    mean = sum(rets) / len(rets)
    var = sum((x - mean) ** 2 for x in rets) / len(rets)
    return var**0.5


def _recent_momentum(closes: list[float], idx: int, window: int) -> float:
    if window <= 0 or idx <= 0:
        return 0.0
    left = max(0, idx - window)
    base = closes[left]
    cur = closes[idx]
    if base <= 0:
        return 0.0
    return (cur / base) - 1.0


def _recent_shock(closes: list[float], idx: int, window: int) -> float:
    """Worst cumulative drop over short horizon ending at idx."""
    if window <= 0 or idx <= 0:
        return 0.0
    worst = 0.0
    left = max(0, idx - window)
    cur = closes[idx]
    for j in range(left, idx):
        base = closes[j]
        if base <= 0:
            continue
        ret = (cur / base) - 1.0
        if ret < worst:
            worst = ret
    return worst


def _vol_expansion(closes: list[float], idx: int, short_window: int, long_window: int) -> float:
    if idx <= 1:
        return 0.0
    s = _recent_volatility(closes, idx, short_window)
    l = _recent_volatility(closes, idx, long_window)
    if l <= 1e-12:
        return 0.0
    return max(0.0, (s / l) - 1.0)


def _gap_risk(closes: list[float], idx: int) -> float:
    if idx <= 0:
        return 0.0
    prev = closes[idx - 1]
    cur = closes[idx]
    if prev <= 0:
        return 0.0
    ret = (cur / prev) - 1.0
    return max(0.0, -ret)


def _safe_div(a: float, b: float) -> float:
    if abs(b) <= 1e-12:
        return 0.0
    return a / b


def _apply_recent_precision_layer(
    warnings: list[dict[str, Any]],
    parsed: list[dict[str, Any]],
    recent_era_start_year: int,
    min_evidence: int,
    density_window: int,
    density_max: int,
) -> list[dict[str, Any]]:
    """Drop weak recent-era alerts and cap local warning density (precision recovery)."""
    if not warnings:
        return warnings
    era_y = int(recent_era_start_year)
    min_ev = max(1, int(min_evidence))
    win = max(1, int(density_window))
    cap = max(1, int(density_max))

    kept: list[dict[str, Any]] = []
    for w in warnings:
        idx = int(w["index"])
        y = int(parsed[idx].get("year", 0)) if 0 <= idx < len(parsed) else 0
        if y >= era_y:
            ev = int(w.get("evidence_count", 1))
            if ev < min_ev:
                continue
        kept.append(w)

    kept.sort(key=lambda z: int(z["index"]))
    out: list[dict[str, Any]] = []
    for w in kept:
        idx = int(w["index"])
        y = int(parsed[idx].get("year", 0)) if 0 <= idx < len(parsed) else 0
        if y < era_y:
            out.append(w)
            continue
        prior = [x for x in out if idx - win <= int(x["index"]) < idx]
        if len(prior) >= cap:
            continue
        out.append(w)
    return out


def _sparsify_warnings(
    warnings: list[dict[str, Any]],
    cluster_merge_days: int,
    refractory_days: int,
    crisis_relax_drawdown: float,
    crisis_refractory_days: int,
) -> list[dict[str, Any]]:
    if not warnings:
        return warnings
    if cluster_merge_days <= 0 and refractory_days <= 0:
        return warnings
    ws = sorted(warnings, key=lambda x: int(x.get("index", 0)))

    # 1) Merge dense clusters by keeping the strongest score event in each cluster window.
    merged: list[dict[str, Any]] = []
    if cluster_merge_days > 0:
        cluster: list[dict[str, Any]] = [ws[0]]
        for w in ws[1:]:
            prev = cluster[-1]
            if int(w["index"]) - int(prev["index"]) <= cluster_merge_days:
                cluster.append(w)
            else:
                best = max(cluster, key=lambda z: abs(float(z.get("direction_score", 0.0))))
                merged.append(best)
                cluster = [w]
        best = max(cluster, key=lambda z: abs(float(z.get("direction_score", 0.0))))
        merged.append(best)
    else:
        merged = ws

    # 2) Refractory period: after one alert, suppress follow-ups for N days.
    if refractory_days <= 0:
        return merged
    out: list[dict[str, Any]] = []
    last_idx = -10**9
    for w in merged:
        idx = int(w["index"])
        dd = float(w.get("drawdown_from_20d_peak", 0.0))
        local_refractory = refractory_days
        if dd <= crisis_relax_drawdown:
            local_refractory = max(1, crisis_refractory_days)
        if idx - last_idx >= local_refractory:
            out.append(w)
            last_idx = idx
    return out


def _run(
    input_json: Path,
    lens_json: Path,
    cycle_priority: list[int],
    out_dir: Path,
    drawdown_warn_threshold: float,
    cycle_near_threshold: float,
    composite_warn_threshold: float,
    composite_down_threshold: float,
    min_rows: int,
    cluster_merge_days: int,
    refractory_days: int,
    crisis_relax_drawdown: float,
    crisis_refractory_days: int,
    cycle_stress_min: float,
    calm_vol_window: int,
    calm_vol_threshold: float,
    calm_cycle_penalty: float,
    crisis_warn_drawdown: float,
    crisis_composite_warn_threshold: float,
    momentum_window: int,
    momentum_weight: float,
    momentum_warn_threshold: float,
    shock_window: int,
    shock_weight: float,
    shock_warn_threshold: float,
    crash_horizon: int,
    crash_drop_threshold: float,
    calm_hard_suppress_vol_threshold: float,
    calm_hard_suppress_shock_threshold: float,
    calm_hard_suppress_drawdown_floor: float,
    recent_era_start_year: int,
    recent_cycle_stress_min: float,
    recent_composite_warn_threshold: float,
    recent_shock_warn_threshold: float,
    recent_vol_exp_weight: float,
    recent_gap_weight: float,
    recent_vol_exp_warn_threshold: float,
    recent_gap_warn_threshold: float,
    ohlcv_range_weight: float,
    ohlcv_body_weight: float,
    ohlcv_volume_weight: float,
    ohlcv_gap_open_weight: float,
    ohlcv_feature_warn_threshold: float,
    use_multi_event_labels: bool,
    streak_days: int,
    streak_threshold: float,
    vol_break_window: int,
    vol_break_threshold: float,
    enable_recent_precision_layer: bool,
    recent_precision_min_evidence: int,
    recent_precision_density_window: int,
    recent_precision_density_max: int,
    precrash_lookback_days: int,
    detail_json: Optional[Path] = None,
) -> dict[str, Any]:
    rows = _read_json(input_json)
    if not isinstance(rows, list):
        raise ValueError("input json must be a list of rows")
    lens = _read_json(lens_json)
    if not isinstance(lens, dict):
        raise ValueError("lens json must be an object")

    parsed: list[dict[str, Any]] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        try:
            d = str(r["date"])
            close = float(r["close"])
            open_ = float(r.get("open", close))
            high = float(r.get("high", close))
            low = float(r.get("low", close))
            vol = float(r.get("volume", 0.0))
        except (KeyError, TypeError, ValueError):
            continue
        year = int(d[:4]) if len(d) >= 4 and d[:4].isdigit() else 0
        parsed.append(
            {
                "date": d,
                "open": open_,
                "high": high,
                "low": low,
                "close": close,
                "volume": vol,
                "year": year,
            }
        )
    if len(parsed) < int(min_rows):
        raise ValueError(f"need at least {int(min_rows)} rows for crash/cycle checks")

    closes = [x["close"] for x in parsed]
    lens_direction_score = float(((lens.get("scores") or {}).get("direction_score")) or 0.0)
    confidence = float(((lens.get("scores") or {}).get("confidence")) or 0.2)

    lookback_peak = 20
    drop_threshold = crash_drop_threshold
    labels = (
        _multi_event_labels(
            closes,
            lookback_peak,
            crash_horizon,
            drop_threshold,
            max(2, int(streak_days)),
            float(streak_threshold),
            max(2, int(vol_break_window)),
            float(vol_break_threshold),
        )
        if use_multi_event_labels
        else _crash_start_labels(closes, lookback_peak, crash_horizon, drop_threshold)
    )
    crash_indices = [i for i, v in enumerate(labels) if v]

    warnings: list[dict[str, Any]] = []
    for i, row in enumerate(parsed):
        drawdown = _pct_drop_from_peak(closes, i, lookback_peak)
        cyc = _cycle_resonance(i, cycle_priority)
        recent_vol = _recent_volatility(closes, i, calm_vol_window)
        momentum = _recent_momentum(closes, i, momentum_window)
        shock = _recent_shock(closes, i, shock_window)
        o = float(row.get("open", row["close"]))
        h = float(row.get("high", row["close"]))
        l = float(row.get("low", row["close"]))
        c = float(row["close"])
        v = float(row.get("volume", 0.0))
        prev_c = closes[i - 1] if i > 0 else c
        range_ratio = max(0.0, _safe_div(h - l, c))
        body_ratio = max(0.0, _safe_div(abs(c - o), max(h - l, 1e-9)))
        # Volume surge against trailing 20-day average (close-only fallback safe).
        v_left = max(0, i - 20)
        v_hist = [float(parsed[j].get("volume", 0.0)) for j in range(v_left, i) if float(parsed[j].get("volume", 0.0)) > 0]
        v_avg = (sum(v_hist) / len(v_hist)) if v_hist else 0.0
        volume_surge = max(0.0, _safe_div(v - v_avg, v_avg)) if v_avg > 0 else 0.0
        gap_open_risk = max(0.0, _safe_div(prev_c - o, prev_c))
        ohlcv_risk = (
            ohlcv_range_weight * range_ratio
            + ohlcv_body_weight * body_ratio
            + ohlcv_volume_weight * volume_surge
            + ohlcv_gap_open_weight * gap_open_risk
        )
        calm_penalty = calm_cycle_penalty if recent_vol < calm_vol_threshold else 0.0
        eff_cyc = max(-1.0, min(1.0, cyc - calm_penalty))
        local_cycle_stress_min = cycle_stress_min
        local_shock_warn_threshold = shock_warn_threshold
        local_composite_warn_threshold = composite_warn_threshold
        local_vol_exp_warn_threshold = recent_vol_exp_warn_threshold
        local_gap_warn_threshold = recent_gap_warn_threshold
        recent_vol_exp = 0.0
        recent_gap = 0.0
        if int(row.get("year", 0)) >= int(recent_era_start_year):
            local_cycle_stress_min = min(local_cycle_stress_min, recent_cycle_stress_min)
            local_shock_warn_threshold = min(local_shock_warn_threshold, recent_shock_warn_threshold)
            local_composite_warn_threshold = min(local_composite_warn_threshold, recent_composite_warn_threshold)
            recent_vol_exp = _vol_expansion(closes, i, short_window=5, long_window=20)
            recent_gap = _gap_risk(closes, i)
        cycle_near = (eff_cyc > cycle_near_threshold) and ((-drawdown) >= local_cycle_stress_min)
        # L2 research-only composite score: cycle resonance + stress drawdown + lens stub signal.
        # Uses only current/past data at index i (look-ahead safe).
        composite_score = (
            0.50 * eff_cyc
            + 0.30 * (-drawdown)
            + 0.10 * lens_direction_score
            + (momentum_weight * (-momentum))
            + (shock_weight * (-shock))
            + (recent_vol_exp_weight * recent_vol_exp)
            + (recent_gap_weight * recent_gap)
            + ohlcv_risk
        )
        direction_sign = (
            "down"
            if composite_score >= composite_down_threshold
            else ("up" if composite_score <= -composite_down_threshold else "neutral")
        )
        local_warn_threshold = local_composite_warn_threshold
        if drawdown <= crisis_warn_drawdown:
            local_warn_threshold = min(local_warn_threshold, crisis_composite_warn_threshold)
        calm_hard_suppress = (
            (recent_vol < calm_hard_suppress_vol_threshold)
            and ((-shock) < calm_hard_suppress_shock_threshold)
            and ((-drawdown) < calm_hard_suppress_drawdown_floor)
        )
        warning = (
            (drawdown <= drawdown_warn_threshold)
            or cycle_near
            or ((-momentum) >= momentum_warn_threshold)
            or ((-shock) >= local_shock_warn_threshold)
            or (recent_vol_exp >= local_vol_exp_warn_threshold)
            or (recent_gap >= local_gap_warn_threshold)
            or (ohlcv_risk >= ohlcv_feature_warn_threshold)
            or (abs(composite_score) >= local_warn_threshold)
        )
        if calm_hard_suppress:
            warning = False
        evidence_channels: list[str] = []
        if drawdown <= drawdown_warn_threshold:
            evidence_channels.append("dd")
        if cycle_near:
            evidence_channels.append("cycle")
        if (-momentum) >= momentum_warn_threshold:
            evidence_channels.append("mom")
        if (-shock) >= local_shock_warn_threshold:
            evidence_channels.append("shock")
        if recent_vol_exp >= local_vol_exp_warn_threshold:
            evidence_channels.append("vol_exp")
        if recent_gap >= local_gap_warn_threshold:
            evidence_channels.append("gap")
        if ohlcv_risk >= ohlcv_feature_warn_threshold:
            evidence_channels.append("ohlcv")
        if abs(composite_score) >= local_warn_threshold:
            evidence_channels.append("comp")
        evidence_count = len(evidence_channels)
        if warning:
            warnings.append(
                {
                    "index": i,
                    "date": row["date"],
                    "evidence_channels": evidence_channels,
                    "evidence_count": evidence_count,
                    "direction_sign": direction_sign,
                    "direction_score": round(composite_score, 6),
                    "cycle_resonance": round(cyc, 6),
                    "effective_cycle_resonance": round(eff_cyc, 6),
                    "recent_volatility": round(recent_vol, 6),
                    "recent_momentum": round(momentum, 6),
                    "recent_shock": round(shock, 6),
                    "recent_vol_expansion": round(recent_vol_exp, 6),
                    "recent_gap_risk": round(recent_gap, 6),
                    "ohlcv_range_ratio": round(range_ratio, 6),
                    "ohlcv_body_ratio": round(body_ratio, 6),
                    "ohlcv_volume_surge": round(volume_surge, 6),
                    "ohlcv_gap_open_risk": round(gap_open_risk, 6),
                    "ohlcv_risk": round(ohlcv_risk, 6),
                    "confidence": round(confidence, 6),
                    "drawdown_from_20d_peak": round(drawdown, 6),
                }
            )

    warnings = _sparsify_warnings(
        warnings=warnings,
        cluster_merge_days=int(cluster_merge_days),
        refractory_days=int(refractory_days),
        crisis_relax_drawdown=float(crisis_relax_drawdown),
        crisis_refractory_days=int(crisis_refractory_days),
    )
    if enable_recent_precision_layer:
        warnings = _apply_recent_precision_layer(
            warnings,
            parsed,
            int(recent_era_start_year),
            int(recent_precision_min_evidence),
            int(recent_precision_density_window),
            int(recent_precision_density_max),
        )

    n_forward = 5
    hits = 0
    valid = 0
    for w in warnings:
        i = int(w["index"])
        j = i + n_forward
        if j >= len(parsed):
            continue
        valid += 1
        delta = closes[j] - closes[i]
        realized = "up" if delta > 0 else ("down" if delta < 0 else "neutral")
        if realized == w["direction_sign"]:
            hits += 1
    hit_rate = (hits / valid) if valid else 0.0

    m_back = max(1, int(precrash_lookback_days))
    recalled = 0
    for ci in crash_indices:
        left = max(0, ci - m_back)
        has_warning = any(left <= int(w["index"]) < ci for w in warnings)
        if has_warning:
            recalled += 1
    crash_recall = (recalled / len(crash_indices)) if crash_indices else 0.0

    warning_indices = [int(w["index"]) for w in warnings]
    precrash_zone: set[int] = set()
    for ci in crash_indices:
        left = max(0, ci - m_back)
        for k in range(left, ci):
            precrash_zone.add(k)
    false_alert_count = 0
    for wi in warning_indices:
        if wi not in precrash_zone:
            false_alert_count += 1
    false_alert_density = (false_alert_count / len(parsed)) if parsed else 0.0
    precrash_zone_true_count = sum(1 for wi in warning_indices if wi in precrash_zone)
    precrash_zone_precision = (precrash_zone_true_count / len(warnings)) if warnings else 0.0
    warning_false_positive_ratio = (false_alert_count / len(warnings)) if warnings else 0.0
    recent_era_warning_indices = [
        int(w["index"])
        for w in warnings
        if 0 <= int(w["index"]) < len(parsed) and int(parsed[int(w["index"])].get("year", 0)) >= int(recent_era_start_year)
    ]
    recent_era_precrash_true = sum(1 for wi in recent_era_warning_indices if wi in precrash_zone)
    recent_era_precrash_precision = (recent_era_precrash_true / len(recent_era_warning_indices)) if recent_era_warning_indices else 0.0

    if detail_json is not None:
        per_warning_summary: list[dict[str, Any]] = []
        for w in warnings:
            wi = int(w["index"])
            in_pz = wi in precrash_zone
            nearest_ci: Optional[int] = None
            days_to: Optional[int] = None
            if crash_indices:
                nearest_ci = min(crash_indices, key=lambda c: abs(c - wi))
                days_to = nearest_ci - wi
            per_warning_summary.append(
                {
                    "date": w.get("date"),
                    "index": wi,
                    "in_precrash_zone": in_pz,
                    "evidence_count": w.get("evidence_count"),
                    "evidence_channels": w.get("evidence_channels"),
                    "nearest_crash_index": nearest_ci,
                    "days_to_nearest_crash": days_to,
                }
            )
        detail_payload: dict[str, Any] = {
            "schema": "logos_kospi_shadow_detail_v1",
            "ts_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "observation_only": OBSERVATION_ONLY,
            "precrash_lookback_days": m_back,
            "period": [parsed[0]["date"], parsed[-1]["date"]],
            "rows": len(parsed),
            "crash_indices": crash_indices,
            "crash_dates": [parsed[i]["date"] for i in crash_indices],
            "crash_event_count": len(crash_indices),
            "precrash_zone_index_count": len(precrash_zone),
            "warnings": warnings,
            "per_warning_summary": per_warning_summary,
            "metrics_snapshot": {
                "crash_warning_recall": round(crash_recall, 6),
                "precrash_zone_precision": round(precrash_zone_precision, 6),
                "warnings_count": len(warnings),
                "false_alert_count": false_alert_count,
            },
        }
        detail_json.parent.mkdir(parents=True, exist_ok=True)
        detail_json.write_text(json.dumps(detail_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_json = out_dir / f"logos_kospi_shadow_202003_v1_{ts}.json"
    out_latest = out_dir / "logos_kospi_shadow_202003_v1_latest.json"
    out_md = out_dir / f"logos_kospi_shadow_202003_v1_{ts}.md"
    out_md_latest = out_dir / "logos_kospi_shadow_202003_v1_latest.md"

    payload: dict[str, Any] = {
        "schema": "logos_kospi_shadow_v1_1",
        "ts_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "observation_only": OBSERVATION_ONLY,
        "period": [parsed[0]["date"], parsed[-1]["date"]],
        "cycle_priority": cycle_priority,
        "metrics_note": {
            "hit_direction_rate": "forward 5d realized move vs direction_sign (not crash precrash zone)",
            "warning_precision": "precrash_zone_true_count / warnings_count (alerts inside precrash window)",
            "recent_era_precrash_zone_precision": "same as warning_precision but only for warnings on/after recent_era_start_year",
            "precrash_zone": f"indices in [crash_index - precrash_lookback_days, crash_index) per labeled crash; affects recall/precision",
        },
        "crash_definition": {
            "peak_lookback_days": lookback_peak,
            "horizon_days": crash_horizon,
            "drop_threshold": drop_threshold,
            "precrash_lookback_days": m_back,
            "use_multi_event_labels": bool(use_multi_event_labels),
            "streak_days": int(streak_days),
            "streak_threshold": float(streak_threshold),
            "vol_break_window": int(vol_break_window),
            "vol_break_threshold": float(vol_break_threshold),
        },
        "signal_thresholds": {
            "drawdown_warn_threshold": drawdown_warn_threshold,
            "cycle_near_threshold": cycle_near_threshold,
            "composite_warn_threshold": composite_warn_threshold,
            "composite_down_threshold": composite_down_threshold,
            "cluster_merge_days": int(cluster_merge_days),
            "refractory_days": int(refractory_days),
            "crisis_relax_drawdown": float(crisis_relax_drawdown),
            "crisis_refractory_days": int(crisis_refractory_days),
            "cycle_stress_min": float(cycle_stress_min),
            "calm_vol_window": int(calm_vol_window),
            "calm_vol_threshold": float(calm_vol_threshold),
            "calm_cycle_penalty": float(calm_cycle_penalty),
            "crisis_warn_drawdown": float(crisis_warn_drawdown),
            "crisis_composite_warn_threshold": float(crisis_composite_warn_threshold),
            "momentum_window": int(momentum_window),
            "momentum_weight": float(momentum_weight),
            "momentum_warn_threshold": float(momentum_warn_threshold),
            "shock_window": int(shock_window),
            "shock_weight": float(shock_weight),
            "shock_warn_threshold": float(shock_warn_threshold),
            "calm_hard_suppress_vol_threshold": float(calm_hard_suppress_vol_threshold),
            "calm_hard_suppress_shock_threshold": float(calm_hard_suppress_shock_threshold),
            "calm_hard_suppress_drawdown_floor": float(calm_hard_suppress_drawdown_floor),
            "recent_era_start_year": int(recent_era_start_year),
            "recent_cycle_stress_min": float(recent_cycle_stress_min),
            "recent_composite_warn_threshold": float(recent_composite_warn_threshold),
            "recent_shock_warn_threshold": float(recent_shock_warn_threshold),
            "recent_vol_exp_weight": float(recent_vol_exp_weight),
            "recent_gap_weight": float(recent_gap_weight),
            "recent_vol_exp_warn_threshold": float(recent_vol_exp_warn_threshold),
            "recent_gap_warn_threshold": float(recent_gap_warn_threshold),
            "ohlcv_range_weight": float(ohlcv_range_weight),
            "ohlcv_body_weight": float(ohlcv_body_weight),
            "ohlcv_volume_weight": float(ohlcv_volume_weight),
            "ohlcv_gap_open_weight": float(ohlcv_gap_open_weight),
            "ohlcv_feature_warn_threshold": float(ohlcv_feature_warn_threshold),
            "enable_recent_precision_layer": bool(enable_recent_precision_layer),
            "recent_precision_min_evidence": int(recent_precision_min_evidence),
            "recent_precision_density_window": int(recent_precision_density_window),
            "recent_precision_density_max": int(recent_precision_density_max),
        },
        "metrics": {
            "hit_direction_rate": round(hit_rate, 6),
            "warning_precision": round(precrash_zone_precision, 6),
            "precrash_zone_precision": round(precrash_zone_precision, 6),
            "precrash_zone_true_count": int(precrash_zone_true_count),
            "warning_false_positive_ratio": round(warning_false_positive_ratio, 6),
            "recent_era_warnings_count": len(recent_era_warning_indices),
            "recent_era_precrash_zone_precision": round(recent_era_precrash_precision, 6),
            "crash_warning_recall": round(crash_recall, 6),
            "warnings_count": len(warnings),
            "warning_load_ratio": round((len(warnings) / len(parsed)) if parsed else 0.0, 6),
            "false_alert_count": false_alert_count,
            "false_alert_density": round(false_alert_density, 6),
            "crash_event_count": len(crash_indices),
            "direction_sign_from_lens": ("down" if lens_direction_score < 0 else ("up" if lens_direction_score > 0 else "neutral")),
            "direction_score_from_lens": round(lens_direction_score, 6),
            "mean_composite_direction_score": round(
                (sum(float(w["direction_score"]) for w in warnings) / len(warnings)) if warnings else 0.0,
                6,
            ),
            "mean_cycle_resonance": round(
                (sum(float(w["cycle_resonance"]) for w in warnings) / len(warnings)) if warnings else 0.0,
                6,
            ),
            "confidence_from_lens": round(confidence, 6),
        },
        "provenance": {
            "input_json": str(input_json.resolve()),
            "lens_json": str(lens_json.resolve()),
        },
        "warnings_preview": warnings[:20],
    }

    md = (
        "# Logos KOSPI Shadow v1\n\n"
        f"- observation_only: `{OBSERVATION_ONLY}`\n"
        f"- period: `{payload['period'][0]} ~ {payload['period'][1]}`\n"
        f"- hit_direction_rate: `{payload['metrics']['hit_direction_rate']}`\n"
        f"- precrash_zone_precision: `{payload['metrics']['precrash_zone_precision']}`\n"
        f"- recent_era_precrash_zone_precision: `{payload['metrics']['recent_era_precrash_zone_precision']}`\n"
        f"- crash_warning_recall: `{payload['metrics']['crash_warning_recall']}`\n"
        f"- warnings_count: `{payload['metrics']['warnings_count']}`\n"
        f"- crash_event_count: `{payload['metrics']['crash_event_count']}`\n"
        f"- lens_direction: `{payload['metrics']['direction_sign_from_lens']}` "
        f"(score={payload['metrics']['direction_score_from_lens']}, conf={payload['metrics']['confidence_from_lens']})\n"
    )

    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    out_json.write_text(text, encoding="utf-8")
    out_latest.write_text(text, encoding="utf-8")
    out_md.write_text(md, encoding="utf-8")
    out_md_latest.write_text(md, encoding="utf-8")

    return {
        "ok": True,
        "json": str(out_json.resolve()),
        "latest_json": str(out_latest.resolve()),
        "md": str(out_md.resolve()),
        "latest_md": str(out_md_latest.resolve()),
        "metrics": payload["metrics"],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Run logos KOSPI shadow test (observation only).")
    ap.add_argument("--input-json", type=Path, default=DEFAULT_INPUT)
    ap.add_argument("--lens-json", type=Path, default=DEFAULT_LENS)
    ap.add_argument("--cycle-priority", nargs="*", type=int, default=[40, 7, 50])
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    ap.add_argument("--drawdown-warn-threshold", type=float, default=-0.06)
    ap.add_argument("--cycle-near-threshold", type=float, default=0.2)
    ap.add_argument("--composite-warn-threshold", type=float, default=0.25)
    ap.add_argument("--composite-down-threshold", type=float, default=0.2)
    ap.add_argument("--min-rows", type=int, default=40)
    ap.add_argument("--cluster-merge-days", type=int, default=0)
    ap.add_argument("--refractory-days", type=int, default=0)
    ap.add_argument("--crisis-relax-drawdown", type=float, default=-0.12)
    ap.add_argument("--crisis-refractory-days", type=int, default=3)
    ap.add_argument("--cycle-stress-min", type=float, default=0.03)
    ap.add_argument("--calm-vol-window", type=int, default=10)
    ap.add_argument("--calm-vol-threshold", type=float, default=0.009)
    ap.add_argument("--calm-cycle-penalty", type=float, default=0.18)
    ap.add_argument("--crisis-warn-drawdown", type=float, default=-0.09)
    ap.add_argument("--crisis-composite-warn-threshold", type=float, default=0.18)
    ap.add_argument("--momentum-window", type=int, default=5)
    ap.add_argument("--momentum-weight", type=float, default=0.25)
    ap.add_argument("--momentum-warn-threshold", type=float, default=0.02)
    ap.add_argument("--shock-window", type=int, default=3)
    ap.add_argument("--shock-weight", type=float, default=0.2)
    ap.add_argument("--shock-warn-threshold", type=float, default=0.025)
    ap.add_argument("--crash-horizon", type=int, default=5)
    ap.add_argument("--crash-drop-threshold", type=float, default=-0.10)
    ap.add_argument("--calm-hard-suppress-vol-threshold", type=float, default=0.008)
    ap.add_argument("--calm-hard-suppress-shock-threshold", type=float, default=0.015)
    ap.add_argument("--calm-hard-suppress-drawdown-floor", type=float, default=0.03)
    ap.add_argument("--recent-era-start-year", type=int, default=2020)
    ap.add_argument("--recent-cycle-stress-min", type=float, default=0.005)
    ap.add_argument("--recent-composite-warn-threshold", type=float, default=0.18)
    ap.add_argument("--recent-shock-warn-threshold", type=float, default=0.015)
    ap.add_argument("--recent-vol-exp-weight", type=float, default=0.25)
    ap.add_argument("--recent-gap-weight", type=float, default=0.2)
    ap.add_argument("--recent-vol-exp-warn-threshold", type=float, default=0.25)
    ap.add_argument("--recent-gap-warn-threshold", type=float, default=0.015)
    ap.add_argument("--ohlcv-range-weight", type=float, default=0.08)
    ap.add_argument("--ohlcv-body-weight", type=float, default=0.05)
    ap.add_argument("--ohlcv-volume-weight", type=float, default=0.06)
    ap.add_argument("--ohlcv-gap-open-weight", type=float, default=0.08)
    ap.add_argument("--ohlcv-feature-warn-threshold", type=float, default=0.05)
    ap.add_argument("--use-multi-event-labels", action="store_true")
    ap.add_argument("--streak-days", type=int, default=5)
    ap.add_argument("--streak-threshold", type=float, default=-0.06)
    ap.add_argument("--vol-break-window", type=int, default=10)
    ap.add_argument("--vol-break-threshold", type=float, default=0.018)
    ap.add_argument("--enable-recent-precision-layer", action="store_true")
    ap.add_argument("--recent-precision-min-evidence", type=int, default=2)
    ap.add_argument("--recent-precision-density-window", type=int, default=40)
    ap.add_argument("--recent-precision-density-max", type=int, default=2)
    ap.add_argument(
        "--detail-json",
        type=Path,
        default=None,
        help="Optional path to write full warnings + crash indices + per-warning flags (research debug).",
    )
    ap.add_argument(
        "--precrash-lookback-days",
        type=int,
        default=20,
        help="Days before each labeled crash index treated as precrash zone; also used for crash_warning_recall window [ci-m_back, ci). Default 20.",
    )
    args = ap.parse_args()

    result = _run(
        args.input_json,
        args.lens_json,
        list(args.cycle_priority),
        args.out_dir,
        args.drawdown_warn_threshold,
        args.cycle_near_threshold,
        args.composite_warn_threshold,
        args.composite_down_threshold,
        args.min_rows,
        args.cluster_merge_days,
        args.refractory_days,
        args.crisis_relax_drawdown,
        args.crisis_refractory_days,
        args.cycle_stress_min,
        args.calm_vol_window,
        args.calm_vol_threshold,
        args.calm_cycle_penalty,
        args.crisis_warn_drawdown,
        args.crisis_composite_warn_threshold,
        args.momentum_window,
        args.momentum_weight,
        args.momentum_warn_threshold,
        args.shock_window,
        args.shock_weight,
        args.shock_warn_threshold,
        args.crash_horizon,
        args.crash_drop_threshold,
        args.calm_hard_suppress_vol_threshold,
        args.calm_hard_suppress_shock_threshold,
        args.calm_hard_suppress_drawdown_floor,
        args.recent_era_start_year,
        args.recent_cycle_stress_min,
        args.recent_composite_warn_threshold,
        args.recent_shock_warn_threshold,
        args.recent_vol_exp_weight,
        args.recent_gap_weight,
        args.recent_vol_exp_warn_threshold,
        args.recent_gap_warn_threshold,
        args.ohlcv_range_weight,
        args.ohlcv_body_weight,
        args.ohlcv_volume_weight,
        args.ohlcv_gap_open_weight,
        args.ohlcv_feature_warn_threshold,
        args.use_multi_event_labels,
        args.streak_days,
        args.streak_threshold,
        args.vol_break_window,
        args.vol_break_threshold,
        args.enable_recent_precision_layer,
        args.recent_precision_min_evidence,
        args.recent_precision_density_window,
        args.recent_precision_density_max,
        args.precrash_lookback_days,
        args.detail_json,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

