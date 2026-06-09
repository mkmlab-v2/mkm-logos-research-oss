#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KOSPI open/prior feature maps + bull→bear overlay policies for B-track prophecy spikes [HYPO]."""
from __future__ import annotations

import math
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _load_kospi_rows(csv_path: Path) -> list[dict[str, Any]]:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.logos_shadow_eval_lib import load_kospi_yf_rows

    return load_kospi_yf_rows(csv_path)


def _prior_completed_daily_return_by_eval_date(csv_path: Path) -> dict[str, float]:
    rows = _load_kospi_rows(csv_path)
    if len(rows) < 3:
        return {}
    out: dict[str, float] = {}
    for i in range(2, len(rows)):
        ed = str(rows[i]["date"])[:10]
        try:
            c1 = float(rows[i - 1]["close"])
            c2 = float(rows[i - 2]["close"])
        except (TypeError, ValueError):
            continue
        if c2 == 0.0:
            continue
        out[ed] = (c1 - c2) / c2
    return out


def _overnight_return_by_eval_date(csv_path: Path) -> dict[str, float]:
    """eval_date i: overnight gap (open[i]-close[i-1])/close[i-1] — causal at open."""
    rows = _load_kospi_rows(csv_path)
    out: dict[str, float] = {}
    for i in range(1, len(rows)):
        ed = str(rows[i]["date"])[:10]
        try:
            prev_close = float(rows[i - 1]["close"])
            open_i = float(rows[i]["open"])
        except (TypeError, ValueError):
            continue
        if prev_close == 0.0:
            continue
        out[ed] = (open_i - prev_close) / prev_close
    return out


def _prior_range_position_by_eval_date(csv_path: Path) -> dict[str, float]:
    """eval_date i: (open[i]-low[i-1])/(high[i-1]-low[i-1]) at session open."""
    rows = _load_kospi_rows(csv_path)
    out: dict[str, float] = {}
    for i in range(1, len(rows)):
        ed = str(rows[i]["date"])[:10]
        try:
            hi = float(rows[i - 1]["high"])
            lo = float(rows[i - 1]["low"])
            open_i = float(rows[i]["open"])
        except (TypeError, ValueError):
            continue
        span = hi - lo
        if span <= 0.0:
            continue
        out[ed] = (open_i - lo) / span
    return out


def _realized_vol_5d_by_eval_date(csv_path: Path) -> dict[str, float]:
    """5-day realized vol strictly before eval_date (close-to-close)."""
    rows = _load_kospi_rows(csv_path)
    if len(rows) < 7:
        return {}
    rets: list[float] = []
    dates: list[str] = []
    for i in range(1, len(rows)):
        try:
            c0 = float(rows[i - 1]["close"])
            c1 = float(rows[i]["close"])
        except (TypeError, ValueError):
            rets.append(0.0)
        else:
            rets.append(0.0 if c0 == 0.0 else (c1 - c0) / c0)
        dates.append(str(rows[i]["date"])[:10])
    out: dict[str, float] = {}
    for i, ed in enumerate(dates):
        if i < 5:
            continue
        window = rets[i - 5 : i]
        if not window:
            continue
        mean = sum(window) / len(window)
        var = sum((x - mean) ** 2 for x in window) / len(window)
        out[ed] = math.sqrt(var)
    return out


def _rebound_guard_blocks(prior_ret: float | None, rebound_guard_threshold: float | None) -> bool:
    if prior_ret is None or rebound_guard_threshold is None:
        return False
    return prior_ret <= rebound_guard_threshold


def _composite_conservative_trigger(
    ed: str,
    *,
    prior_map: dict[str, float],
    overnight_map: dict[str, float] | None,
    mild: float,
    ovn_thr: float | None,
) -> bool:
    pr = prior_map.get(ed)
    if pr is not None and pr <= mild:
        return True
    ovn = (overnight_map or {}).get(ed)
    if ovn is not None and ovn_thr is not None and ovn <= ovn_thr:
        return True
    return False


def _range_low_trigger(
    ed: str,
    *,
    range_map: dict[str, float] | None,
    range_thr: float | None,
) -> bool:
    rp = (range_map or {}).get(ed)
    return rp is not None and range_thr is not None and rp <= range_thr


def _mild_prior_trigger(ed: str, *, prior_map: dict[str, float], mild: float) -> bool:
    pr = prior_map.get(ed)
    return pr is not None and pr <= mild


def _apply_bull_to_bear(
    nr: dict[str, Any],
    *,
    overlay_rule: str,
    prior_ret: float | None,
    modified_counter: list[int],
) -> None:
    nr["predicted_direction"] = "bear"
    nr["overlay_rule"] = overlay_rule
    if prior_ret is not None:
        nr["overlay_prior_completed_daily_return"] = round(prior_ret, 8)
    modified_counter[0] += 1


def apply_overlay(
    rows: list[dict[str, Any]],
    *,
    overlay: str,
    stress_years: set[int],
    prior_return_by_date: dict[str, float] | None,
    prior_return_threshold: float,
    rebound_guard_threshold: float | None = None,
    overnight_return_by_date: dict[str, float] | None = None,
    session_open_composite_overnight_threshold: float | None = None,
    intraday_drawdown_by_date: dict[str, float] | None = None,
    realized_vol_by_date: dict[str, float] | None = None,
    vol_regime_threshold: float | None = None,
    prior_range_position_by_date: dict[str, float] | None = None,
    prior_range_low_threshold: float | None = None,
    overnight_gap_rebound_skip_threshold: float | None = None,
    range_soft_cap_for_range_only_leg: float | None = None,
    eval_year_fn: Any = None,
) -> tuple[list[dict[str, Any]], int]:
    """Return new rows (deep copy) and count of modified predictions."""
    modified = [0]
    out: list[dict[str, Any]] = []
    prior_map = prior_return_by_date or {}
    overnight_map = overnight_return_by_date or {}
    range_map = prior_range_position_by_date or {}
    vol_map = realized_vol_by_date or {}
    intraday_map = intraday_drawdown_by_date or {}

    for r in rows:
        nr = deepcopy(r)
        pred = str(nr.get("predicted_direction") or "").strip().lower()
        ed = str(nr.get("eval_date") or "").strip()[:10]
        year = eval_year_fn(ed) if eval_year_fn else None
        pr = prior_map.get(ed)

        if overlay == "none":
            pass
        elif overlay == "stress_bear_to_neutral_v0":
            if year is not None and year in stress_years and pred == "bear":
                nr["predicted_direction"] = "neutral"
                nr["overlay_rule"] = overlay
                modified[0] += 1
        elif overlay == "prior_day_shock_bear_abstain_v0":
            if pr is not None and pred == "bear" and pr <= prior_return_threshold:
                nr["predicted_direction"] = "neutral"
                nr["overlay_rule"] = overlay
                modified[0] += 1
        elif overlay in {
            "prior_day_shock_bull_abstain_v0",
            "prior_day_shock_bull_to_bear_v0",
            "prior_shock_bull_abstain_rebound_guard_v0",
            "prior_shock_bull_to_bear_rebound_guard_v0",
            "overnight_gap_shock_bull_to_bear_v0",
        }:
            use_overnight = overlay == "overnight_gap_shock_bull_to_bear_v0"
            use_rebound = "rebound_guard" in overlay
            signal = (overnight_map.get(ed) if use_overnight else pr)
            thr = (
                session_open_composite_overnight_threshold
                if use_overnight and session_open_composite_overnight_threshold is not None
                else prior_return_threshold
            )
            if use_overnight and thr is None:
                thr = -0.02
            to_bear = overlay.endswith("_to_bear_v0") or "to_bear" in overlay
            if (
                pred == "bull"
                and signal is not None
                and thr is not None
                and signal <= thr
                and not (use_rebound and _rebound_guard_blocks(pr, rebound_guard_threshold))
            ):
                _apply_bull_to_bear(nr, overlay_rule=overlay, prior_ret=pr, modified_counter=modified)
            elif pred == "bull" and not to_bear and pr is not None and pr <= prior_return_threshold:
                if not (use_rebound and _rebound_guard_blocks(pr, rebound_guard_threshold)):
                    nr["predicted_direction"] = "neutral"
                    nr["overlay_rule"] = overlay
                    modified[0] += 1
        elif overlay == "session_open_composite_bull_to_bear_rebound_guard_v0":
            if (
                pred == "bull"
                and not _rebound_guard_blocks(pr, rebound_guard_threshold)
                and _composite_conservative_trigger(
                    ed,
                    prior_map=prior_map,
                    overnight_map=overnight_map,
                    mild=prior_return_threshold,
                    ovn_thr=session_open_composite_overnight_threshold,
                )
            ):
                _apply_bull_to_bear(nr, overlay_rule=overlay, prior_ret=pr, modified_counter=modified)
        elif overlay == "prior_range_low_open_bull_to_bear_rebound_guard_v0":
            if (
                pred == "bull"
                and not _rebound_guard_blocks(pr, rebound_guard_threshold)
                and _range_low_trigger(ed, range_map=range_map, range_thr=prior_range_low_threshold)
            ):
                _apply_bull_to_bear(nr, overlay_rule=overlay, prior_ret=pr, modified_counter=modified)
        elif overlay == "intraday_open_to_low_oracle_bull_to_bear_v0":
            dd = intraday_map.get(ed)
            thr = prior_return_threshold if prior_return_threshold else 0.05
            if pred == "bull" and dd is not None and dd >= thr:
                _apply_bull_to_bear(nr, overlay_rule=overlay, prior_ret=pr, modified_counter=modified)
        elif overlay == "vol_gated_session_open_composite_bull_to_bear_rebound_guard_v0":
            vol = vol_map.get(ed)
            if vol is None or vol_regime_threshold is None or vol < vol_regime_threshold:
                pass
            elif (
                pred == "bull"
                and not _rebound_guard_blocks(pr, rebound_guard_threshold)
                and _composite_conservative_trigger(
                    ed,
                    prior_map=prior_map,
                    overnight_map=overnight_map,
                    mild=prior_return_threshold,
                    ovn_thr=session_open_composite_overnight_threshold,
                )
            ):
                _apply_bull_to_bear(nr, overlay_rule=overlay, prior_ret=pr, modified_counter=modified)
        elif overlay == "range_or_composite_conservative_bull_to_bear_rebound_guard_v0":
            if pred == "bull" and not _rebound_guard_blocks(pr, rebound_guard_threshold):
                if _range_low_trigger(ed, range_map=range_map, range_thr=prior_range_low_threshold) or _composite_conservative_trigger(
                    ed,
                    prior_map=prior_map,
                    overnight_map=overnight_map,
                    mild=prior_return_threshold,
                    ovn_thr=session_open_composite_overnight_threshold,
                ):
                    _apply_bull_to_bear(nr, overlay_rule=overlay, prior_ret=pr, modified_counter=modified)
        elif overlay == "range_or_composite_or_vol_gated_conservative_bull_to_bear_rebound_guard_v0":
            if pred == "bull" and not _rebound_guard_blocks(pr, rebound_guard_threshold):
                vol_ok = (
                    vol_map.get(ed) is not None
                    and vol_regime_threshold is not None
                    and vol_map[ed] >= vol_regime_threshold
                )
                composite = _composite_conservative_trigger(
                    ed,
                    prior_map=prior_map,
                    overnight_map=overnight_map,
                    mild=prior_return_threshold,
                    ovn_thr=session_open_composite_overnight_threshold,
                )
                if _range_low_trigger(ed, range_map=range_map, range_thr=prior_range_low_threshold) or composite or (
                    vol_ok and composite
                ):
                    _apply_bull_to_bear(nr, overlay_rule=overlay, prior_ret=pr, modified_counter=modified)
        elif overlay == "mild_and_range_or_composite_conservative_bull_to_bear_rebound_guard_v0":
            if pred == "bull" and not _rebound_guard_blocks(pr, rebound_guard_threshold):
                if (
                    _mild_prior_trigger(ed, prior_map=prior_map, mild=prior_return_threshold)
                    or _range_low_trigger(ed, range_map=range_map, range_thr=prior_range_low_threshold)
                    or _composite_conservative_trigger(
                        ed,
                        prior_map=prior_map,
                        overnight_map=overnight_map,
                        mild=prior_return_threshold,
                        ovn_thr=session_open_composite_overnight_threshold,
                    )
                ):
                    _apply_bull_to_bear(nr, overlay_rule=overlay, prior_ret=pr, modified_counter=modified)
        elif overlay == "mild_and_range_or_composite_or_vol_gated_conservative_bull_to_bear_rebound_guard_v0":
            if pred == "bull" and not _rebound_guard_blocks(pr, rebound_guard_threshold):
                vol_ok = (
                    vol_map.get(ed) is not None
                    and vol_regime_threshold is not None
                    and vol_map[ed] >= vol_regime_threshold
                )
                composite = _composite_conservative_trigger(
                    ed,
                    prior_map=prior_map,
                    overnight_map=overnight_map,
                    mild=prior_return_threshold,
                    ovn_thr=session_open_composite_overnight_threshold,
                )
                if (
                    _mild_prior_trigger(ed, prior_map=prior_map, mild=prior_return_threshold)
                    or _range_low_trigger(ed, range_map=range_map, range_thr=prior_range_low_threshold)
                    or composite
                    or (vol_ok and composite)
                ):
                    _apply_bull_to_bear(nr, overlay_rule=overlay, prior_ret=pr, modified_counter=modified)
        else:
            raise ValueError(f"unknown overlay: {overlay}")
        out.append(nr)
    return out, modified[0]
