# -*- coding: utf-8 -*-
"""[HYPO] Shared supplier_tight × sasang veto split rules (research_only)."""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

DEFAULT_JOSEPH_START = "2025-06-01"
DEFAULT_JOSEPH_END = "2028-12-31"
DEFAULT_FIELD_EXIT_HYST_DAYS = 10
DEFAULT_GEUMHWA_MIN_CONSECUTIVE_DAYS = 5
RECOMMENDED_REGIME_ID = "field_hyst_or_joseph_ext"


def load_sasang_rows(path: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        d = str(row.get("eval_date") or "")
        if d:
            out[d] = row
    return out


def load_veto_by_date(path: Path) -> dict[str, bool]:
    out: dict[str, bool] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        d = str(row.get("eval_date") or "")
        snap = row.get("market_sasang_lens_snapshot") or {}
        veto = snap.get("veto") or {}
        if d:
            out[d] = bool(veto.get("force_hold"))
    return out


def veto_for_date(d: str, veto_map: dict[str, bool]) -> bool | None:
    if d in veto_map:
        return veto_map[d]
    cur = date.fromisoformat(d)
    for _ in range(6):
        key = cur.isoformat()
        if key in veto_map:
            return veto_map[key]
        cur -= timedelta(days=1)
    return None


def _sma(closes: dict[str, float], dates: list[str], idx: int, window: int) -> float | None:
    if idx + 1 < window:
        return None
    chunk = [closes[dates[i]] for i in range(idx - window + 1, idx + 1)]
    return sum(chunk) / len(chunk)


def supplier_tight_field_momentum(
    closes: dict[str, float],
    dates: list[str],
    *,
    sma_window: int = 60,
    ret_lookback: int = 20,
) -> dict[str, bool]:
    out: dict[str, bool] = {}
    for i, d in enumerate(dates):
        sma = _sma(closes, dates, i, sma_window)
        if sma is None or i < ret_lookback:
            out[d] = False
            continue
        ret = closes[d] / closes[dates[i - ret_lookback]] - 1.0
        out[d] = closes[d] > sma and ret > 0.0
    return out


def supplier_tight_geumhwa(
    sasang_rows: dict[str, dict[str, Any]],
    dates: list[str],
    *,
    execution_threshold: float = 0.35,
) -> dict[str, bool]:
    out: dict[str, bool] = {}
    for d in dates:
        row = sasang_rows.get(d)
        if row is None:
            cur = date.fromisoformat(d)
            for _ in range(6):
                cur -= timedelta(days=1)
                row = sasang_rows.get(cur.isoformat())
                if row:
                    break
        if not row:
            out[d] = False
            continue
        mr = row.get("machine_readables") or {}
        heat = float(mr.get("heat_proxy") or 0.0)
        cold = float(mr.get("cold_proxy") or 0.0)
        cold_n = min(max(cold, 0.0), 1.0)
        idx = heat * (1.0 - cold_n)
        out[d] = idx >= execution_threshold
    return out


def apply_geumhwa_min_days_gate(
    raw: dict[str, bool],
    dates: list[str],
    *,
    min_consecutive: int = DEFAULT_GEUMHWA_MIN_CONSECUTIVE_DAYS,
) -> dict[str, bool]:
    """Sparse geumhwa: require N consecutive True days before supplier_tight."""
    out: dict[str, bool] = {}
    streak = 0
    for d in dates:
        if raw.get(d):
            streak += 1
        else:
            streak = 0
        out[d] = streak >= min_consecutive
    return out


def apply_supplier_hysteresis(
    raw: dict[str, bool],
    dates: list[str],
    *,
    exit_confirm_days: int = DEFAULT_FIELD_EXIT_HYST_DAYS,
    entry_confirm_days: int = 1,
) -> dict[str, bool]:
    out: dict[str, bool] = {}
    state = False
    exit_streak = 0
    entry_streak = 0
    for d in dates:
        raw_t = raw.get(d, False)
        if state:
            if raw_t:
                exit_streak = 0
            else:
                exit_streak += 1
                if exit_streak >= exit_confirm_days:
                    state = False
                    exit_streak = 0
                    entry_streak = 0
        else:
            if raw_t:
                entry_streak += 1
                if entry_streak >= entry_confirm_days:
                    state = True
                    exit_streak = 0
            else:
                entry_streak = 0
        out[d] = state
    return out


def supplier_tight_joseph_calendar(
    dates: list[str],
    *,
    start: str = DEFAULT_JOSEPH_START,
    end: str = DEFAULT_JOSEPH_END,
) -> dict[str, bool]:
    return {d: start <= d <= end for d in dates}


def merge_supplier_regimes(
    field: dict[str, bool],
    field_hyst: dict[str, bool],
    geumhwa: dict[str, bool],
    geumhwa_gated: dict[str, bool],
    joseph_ext: dict[str, bool],
    joseph_legacy: dict[str, bool],
    dates: list[str],
) -> dict[str, dict[str, bool]]:
    return {
        "field_momentum_sma60": {d: field.get(d, False) for d in dates},
        "field_momentum_sma60_hyst10": {d: field_hyst.get(d, False) for d in dates},
        "geumhwa_execution": {d: geumhwa.get(d, False) for d in dates},
        "geumhwa_execution_gated5": {d: geumhwa_gated.get(d, False) for d in dates},
        "joseph_calendar_2026_2028": {d: joseph_legacy.get(d, False) for d in dates},
        "joseph_calendar_2025_06_2028": {d: joseph_ext.get(d, False) for d in dates},
        "field_or_joseph_legacy": {
            d: field.get(d, False) or joseph_legacy.get(d, False) for d in dates
        },
        "field_hyst_or_joseph_ext": {
            d: field_hyst.get(d, False) or joseph_ext.get(d, False) for d in dates
        },
    }


def build_supplier_regimes_for_dates(
    closes: dict[str, float],
    dates: list[str],
    sasang_rows: dict[str, dict[str, Any]],
) -> dict[str, dict[str, bool]]:
    field = supplier_tight_field_momentum(closes, dates)
    field_hyst = apply_supplier_hysteresis(field, dates, exit_confirm_days=DEFAULT_FIELD_EXIT_HYST_DAYS)
    geumhwa = supplier_tight_geumhwa(sasang_rows, dates)
    geumhwa_gated = apply_geumhwa_min_days_gate(geumhwa, dates)
    joseph_ext = supplier_tight_joseph_calendar(dates)
    joseph_legacy = supplier_tight_joseph_calendar(dates, start="2026-01-01", end=DEFAULT_JOSEPH_END)
    return merge_supplier_regimes(
        field, field_hyst, geumhwa, geumhwa_gated, joseph_ext, joseph_legacy, dates
    )


def regime_mkm_split_v1(
    closes: dict[str, float],
    dates: list[str],
    veto_map: dict[str, bool],
    supplier_map: dict[str, bool],
    *,
    structural_entry: bool = False,
) -> dict[str, Any]:
    if len(dates) < 2:
        return {"status": "insufficient", "total_return_pct": None}
    equity = 1.0
    in_market = False
    entry_price: float | None = None
    trades = 0
    tight_days = 0
    blocked_entry_by_veto = 0
    for d in dates:
        tight = supplier_map.get(d, False)
        if tight:
            tight_days += 1
        v = veto_for_date(d, veto_map)
        if tight:
            if not in_market:
                can_enter = structural_entry or (v is not True)
                if can_enter:
                    entry_price = closes[d]
                    in_market = True
                    trades += 1
                elif v is True:
                    blocked_entry_by_veto += 1
        else:
            if in_market and entry_price is not None:
                equity *= closes[d] / entry_price
                in_market = False
                entry_price = None
                trades += 1
    if in_market and entry_price is not None:
        equity *= closes[dates[-1]] / entry_price
    note = (
        "supplier_tight=구조적 롱; veto=추격 진입만 차단"
        if not structural_entry
        else "supplier_tight 첫날 구조 진입; veto 무시; tight 해제시만 청산"
    )
    return {
        "status": "ok",
        "total_return_pct": round((equity - 1.0) * 100.0, 4),
        "trades": trades,
        "supplier_tight_days": tight_days,
        "blocked_entry_by_veto_days": blocked_entry_by_veto,
        "structural_entry": structural_entry,
        "note_ko": note,
    }


FUSION_POLICY_ARMS = (
    "literal_veto_hold",
    "eternal_wait_on_veto",
    "regime_mkm_split_tactical",
    "regime_mkm_split_structural",
)


def daily_fusion_posture(
    *,
    veto: bool,
    supplier_tight: bool,
    in_market: bool,
    policy: str,
) -> tuple[str, bool]:
    """Return (posture_label, in_market_after). research_only operator hint."""
    if policy == "literal_veto_hold":
        if veto:
            return ("HOLD_CASH_OR_EXIT", False)
        return ("PARTICIPATE", True)
    if policy == "eternal_wait_on_veto":
        if veto:
            return ("ETERNAL_WAIT", False)
        return ("PARTICIPATE", True)
    if policy == "regime_mkm_split_tactical":
        if not supplier_tight:
            return ("EXIT_STRUCTURAL", False)
        if in_market:
            return ("HOLD_THROUGH_VETO" if veto else "HOLD_STRUCTURAL", True)
        if veto:
            return ("BLOCK_NEW_ENTRY", False)
        return ("ENTER_STRUCTURAL", True)
    if policy == "regime_mkm_split_structural":
        if not supplier_tight:
            return ("EXIT_STRUCTURAL", False)
        if in_market:
            return ("HOLD_STRUCTURAL", True)
        return ("ENTER_STRUCTURAL", True)
    raise ValueError(f"unknown policy: {policy}")
