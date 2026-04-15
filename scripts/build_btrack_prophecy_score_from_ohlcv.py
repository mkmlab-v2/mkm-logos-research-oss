#!/usr/bin/env python3
"""Build a score JSON (predicted vs actual direction) for eval_prophecy_hit_rate_v1 --run-mode price.

Reads B-Track hypothesis JSON and OHLCV CSVs (YFinance-style; same loader as logos KOSPI shadow).
KOSPI SSOT path: research/market_data/kospi_daily_external_yf.csv
BTC: pass --btc-csv when hypothesis instrument is btc or multi (optional file).

Does not fetch live APIs. B-Track / [HYPO] only — not a live trading trigger.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.logos_shadow_eval_lib import load_kospi_yf_rows

DEFAULT_HYPOTHESIS = ROOT / "docs" / "final" / "artifacts" / "btrack_hypothesis_prophecy_latest.json"
DEFAULT_KOSPI_CSV = ROOT / "research" / "market_data" / "kospi_daily_external_yf.csv"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "btrack_prophecy_score_latest.json"
DEFAULT_FLOW_CSV = ROOT / "research" / "market_data" / "kospi_monthly_flow_external.csv"

SCHEMA = "btrack_prophecy_score_v1"


def _rel_to_root(p: Path) -> str:
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return str(p)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_hypothesis(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        o = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return o if isinstance(o, dict) else None


def _predicted_direction(h: dict[str, Any]) -> str | None:
    pred = h.get("prediction") or {}
    d = str(pred.get("direction") or "").strip().lower()
    if d in ("bull", "bear", "neutral"):
        return d
    if d == "abstain":
        return None
    return None


def _instrument(h: dict[str, Any]) -> str:
    pred = h.get("prediction") or {}
    return str(pred.get("instrument") or "multi").strip().lower()


def _daily_return(prev_row: dict[str, Any], cur_row: dict[str, Any]) -> float:
    pc = float(prev_row["close"])
    cc = float(cur_row["close"])
    if pc == 0:
        return 0.0
    return (cc - pc) / pc


def _actual_direction(ret: float, neutral_bps: float) -> str:
    thr = neutral_bps / 10000.0
    if ret > thr:
        return "bull"
    if ret < -thr:
        return "bear"
    return "neutral"


def _row_pair_for_eval_date(rows: list[dict[str, Any]], eval_date: str) -> tuple[dict[str, Any], dict[str, Any]] | None:
    by_date = {r["date"]: r for r in rows}
    if eval_date not in by_date:
        return None
    dates = sorted(by_date.keys())
    idx = dates.index(eval_date)
    if idx == 0:
        return None
    prev_d = dates[idx - 1]
    return by_date[prev_d], by_date[eval_date]


def _rebound_signal_before_eval_date(
    rows: list[dict[str, Any]],
    eval_date: str,
    *,
    lookback_days: int,
    threshold_pct: float,
) -> bool:
    """Check if momentum before eval_date indicates strong rebound.

    Uses only information up to previous trading day (no same-day close leakage).
    """
    if lookback_days <= 0:
        return False
    by_date = {r["date"]: r for r in rows}
    dates = sorted(by_date.keys())
    if eval_date not in by_date:
        return False
    idx = dates.index(eval_date)
    prev_idx = idx - 1
    start_idx = prev_idx - lookback_days
    if prev_idx < 0 or start_idx < 0:
        return False
    start_close = float(by_date[dates[start_idx]]["close"])
    prev_close = float(by_date[dates[prev_idx]]["close"])
    if start_close == 0:
        return False
    momentum_pct = (prev_close / start_close - 1.0) * 100.0
    return momentum_pct >= threshold_pct


def _shock_signal_before_eval_date(
    rows: list[dict[str, Any]],
    eval_date: str,
    *,
    abs_return_pct_cutoff: float,
) -> bool:
    """Detect shock from previous day move before eval_date."""
    by_date = {r["date"]: r for r in rows}
    dates = sorted(by_date.keys())
    if eval_date not in by_date:
        return False
    idx = dates.index(eval_date)
    if idx < 2:
        return False
    prev_close = float(by_date[dates[idx - 1]]["close"])
    prev_prev_close = float(by_date[dates[idx - 2]]["close"])
    if prev_prev_close == 0:
        return False
    prev_ret_pct = (prev_close / prev_prev_close - 1.0) * 100.0
    return abs(prev_ret_pct) >= abs_return_pct_cutoff


def _prev_day_return_pct(rows: list[dict[str, Any]], eval_date: str) -> float:
    by_date = {r["date"]: r for r in rows}
    dates = sorted(by_date.keys())
    if eval_date not in by_date:
        return 0.0
    idx = dates.index(eval_date)
    if idx < 2:
        return 0.0
    prev_close = float(by_date[dates[idx - 1]]["close"])
    prev_prev_close = float(by_date[dates[idx - 2]]["close"])
    if prev_prev_close == 0:
        return 0.0
    return (prev_close / prev_prev_close - 1.0) * 100.0


def _recent_abs_return_mean_pct(rows: list[dict[str, Any]], eval_date: str, lookback_days: int) -> float:
    by_date = {r["date"]: r for r in rows}
    dates = sorted(by_date.keys())
    if eval_date not in by_date:
        return 0.0
    idx = dates.index(eval_date)
    if idx < 2:
        return 0.0
    n = max(1, int(lookback_days))
    vals: list[float] = []
    for j in range(max(1, idx - n), idx):
        c0 = float(by_date[dates[j - 1]]["close"])
        c1 = float(by_date[dates[j]]["close"])
        if c0 == 0:
            continue
        vals.append(abs((c1 / c0 - 1.0) * 100.0))
    if not vals:
        return 0.0
    return sum(vals) / len(vals)


def _load_monthly_flow_context(path: Path | None) -> dict[str, dict[str, float]]:
    if path is None or not path.is_file():
        return {}
    out: dict[str, dict[str, float]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rd = csv.DictReader(f)
        for r in rd:
            ym = str(r.get("ym") or "").strip()
            if not ym:
                continue
            out[ym] = {
                "foreign_net_buy": float(r.get("foreign_net_buy") or 0.0),
                "institution_net_buy": float(r.get("institution_net_buy") or 0.0),
                "program_net_buy": float(r.get("program_net_buy") or 0.0),
            }
    return out


def _flow_score_for_eval_date(
    eval_date: str,
    flow_ctx: dict[str, dict[str, float]],
    *,
    w_foreign: float,
    w_inst: float,
    w_prog: float,
) -> float:
    ym = str(eval_date)[:7]
    row = flow_ctx.get(ym) or {}
    foreign = float(row.get("foreign_net_buy") or 0.0)
    inst = float(row.get("institution_net_buy") or 0.0)
    prog = float(row.get("program_net_buy") or 0.0)
    return (w_foreign * foreign) + (w_inst * inst) + (w_prog * prog)


def _parse_year_rebound_overrides(s: str) -> dict[int, str]:
    # format: "2026:bull,2025:neutral"
    out: dict[int, str] = {}
    if not str(s or "").strip():
        return out
    for chunk in str(s).split(","):
        t = [x.strip() for x in chunk.split(":")]
        if len(t) != 2:
            continue
        try:
            y = int(t[0])
        except Exception:
            continue
        target = str(t[1]).lower()
        if target in ("neutral", "bull"):
            out[y] = target
    return out


def _parse_year_default_overrides(s: str) -> dict[int, str]:
    # format: "2026:neutral,2025:bear"
    out: dict[int, str] = {}
    if not str(s or "").strip():
        return out
    for chunk in str(s).split(","):
        t = [x.strip() for x in chunk.split(":")]
        if len(t) != 2:
            continue
        try:
            y = int(t[0])
        except Exception:
            continue
        d = str(t[1]).lower()
        if d in ("bull", "neutral", "bear"):
            out[y] = d
    return out


def _prev2_day_return_pct(rows: list[dict[str, Any]], eval_date: str) -> float:
    by_date = {r["date"]: r for r in rows}
    dates = sorted(by_date.keys())
    if eval_date not in by_date:
        return 0.0
    idx = dates.index(eval_date)
    if idx < 3:
        return 0.0
    c_prev1 = float(by_date[dates[idx - 2]]["close"])
    c_prev2 = float(by_date[dates[idx - 3]]["close"])
    if c_prev2 == 0:
        return 0.0
    return (c_prev1 / c_prev2 - 1.0) * 100.0


def _recent_down_stress_stats(rows: list[dict[str, Any]], eval_date: str, lookback_days: int) -> tuple[int, float]:
    by_date = {r["date"]: r for r in rows}
    dates = sorted(by_date.keys())
    if eval_date not in by_date:
        return 0, 0.0
    idx = dates.index(eval_date)
    if idx < 2:
        return 0, 0.0
    n = max(1, int(lookback_days))
    neg_cnt = 0
    cum_drop = 0.0
    for j in range(max(1, idx - n), idx):
        c0 = float(by_date[dates[j - 1]]["close"])
        c1 = float(by_date[dates[j]]["close"])
        if c0 == 0:
            continue
        r_pct = (c1 / c0 - 1.0) * 100.0
        if r_pct < 0:
            neg_cnt += 1
            cum_drop += abs(r_pct)
    return neg_cnt, cum_drop


def _default_eval_date(rows: list[dict[str, Any]]) -> str | None:
    """Latest complete bar date: last row with date strictly before UTC today."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    past = [r["date"] for r in rows if r["date"] < today]
    if not past:
        return None
    return max(past)


def _past_sorted_unique_dates(rows: list[dict[str, Any]]) -> list[str]:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return sorted({r["date"] for r in rows if r["date"] < today})


def _last_n_trading_dates(rows: list[dict[str, Any]], n: int) -> list[str]:
    if n < 1:
        return []
    past = _past_sorted_unique_dates(rows)
    if not past:
        return []
    return past[-n:] if len(past) >= n else past


def _build_rows(
    *,
    hypothesis: dict[str, Any],
    eval_date: str,
    neutral_bps: float,
    kospi_rows: list[dict[str, Any]],
    btc_rows: list[dict[str, Any]] | None,
    inst: str,
    predicted: str | None,
    bull_reversal_lookback: int = 0,
    bull_reversal_threshold_pct: float = 6.0,
    bull_reversal_target: str = "neutral",
    flow_ctx: dict[str, dict[str, float]] | None = None,
    bull_reversal_require_flow: bool = False,
    bull_reversal_min_flow_score: float = 0.0,
    bull_reversal_flow_weights: tuple[float, float, float] = (0.5, 0.4, 0.1),
    bull_reversal_enable_shock_cutoff: bool = False,
    bull_reversal_shock_cutoff_pct: float = 8.0,
    bull_reversal_strong_flow_threshold: float = 6000.0,
    bull_reversal_strong_flow_target: str = "bull",
    bull_reversal_two_stage_enable: bool = False,
    bull_reversal_bull_min_prev_ret_pct: float = 0.8,
    bull_reversal_bull_min_flow_score: float = 3000.0,
    bull_reversal_bull_require_non_shock: bool = True,
    bull_reversal_bull_max_recent_abs_return_mean_pct: float = 3.0,
    bull_reversal_bull_recent_vol_lookback: int = 3,
    bull_reversal_down_guard_enable: bool = False,
    bull_reversal_down_guard_mode: str = "always",
    bull_reversal_down_guard_lookback: int = 5,
    bull_reversal_down_guard_max_down_days: int = 3,
    bull_reversal_down_guard_max_cum_down_pct: float = 9.0,
    bull_reversal_down_guard_shock_cutoff_pct: float = 6.0,
    bull_reversal_down_guard_high_vol_pct: float = 2.5,
    bear_relax_enable: bool = False,
    bear_relax_max_prev_drop_pct: float = 1.5,
    bear_relax_min_flow_score: float = 0.0,
    bear_relax_require_non_shock: bool = True,
    bear_relax_max_recent_abs_return_mean_pct: float = 2.0,
    bear_relax_recent_vol_lookback: int = 3,
    year_rebound_overrides: dict[int, str] | None = None,
    year_rebound_min_prev_ret_pct: float = 0.4,
    year_rebound_min_flow_score: float = 0.0,
    year_rebound_require_non_shock: bool = True,
    year_rebound_max_recent_abs_return_mean_pct: float = 2.5,
    year_rebound_recent_vol_lookback: int = 3,
    year_rebound_min_prev2_ret_pct: float = -0.2,
    year_rebound_down_stress_lookback: int = 5,
    year_rebound_max_down_days: int = 3,
    year_rebound_max_cum_down_pct: float = 9.0,
    year_default_overrides: dict[int, str] | None = None,
    downside_force_bear_enable: bool = False,
    downside_force_bear_lookback: int = 5,
    downside_force_bear_min_down_days: int = 3,
    downside_force_bear_min_cum_down_pct: float = 6.0,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    meta: dict[str, Any] = {"warnings": []}
    rows_out: list[dict[str, Any]] = []
    if predicted is None:
        meta["warnings"].append("hypothesis prediction.direction missing or abstain; no score rows.")
        return [], meta

    def one_leg(label: str, ohlc: list[dict[str, Any]]) -> None:
        pair = _row_pair_for_eval_date(ohlc, eval_date)
        if pair is None:
            meta["warnings"].append(f"{label}: no prev/cur row for eval_date={eval_date}")
            return
        prev_r, cur_r = pair
        ret = _daily_return(prev_r, cur_r)
        act = _actual_direction(ret, neutral_bps)
        pred_eff = predicted
        flow_score = 0.0
        flow_ok = True
        fctx = flow_ctx or {}
        wf, wi, wp = bull_reversal_flow_weights
        flow_score = _flow_score_for_eval_date(
            eval_date,
            fctx,
            w_foreign=wf,
            w_inst=wi,
            w_prog=wp,
        )
        if bull_reversal_require_flow:
            flow_ok = flow_score >= bull_reversal_min_flow_score

        # Year-specific default prediction override before reversal logic.
        ydef = year_default_overrides or {}
        try:
            y = int(str(eval_date)[:4])
        except Exception:
            y = 0
        if y in ydef:
            pred_eff = str(ydef[y])

        # Downside-sensitivity routing: force bear in persistent down-stress windows.
        force_bear_active = False
        if downside_force_bear_enable:
            ds_down_days, ds_cum_down_pct = _recent_down_stress_stats(
                ohlc,
                eval_date,
                lookback_days=downside_force_bear_lookback,
            )
            if (
                ds_down_days >= int(downside_force_bear_min_down_days)
                and ds_cum_down_pct >= float(downside_force_bear_min_cum_down_pct)
            ):
                if pred_eff != "bear":
                    meta["warnings"].append(
                        f"{label}: downside_force_bear_applied ({pred_eff}->bear) at eval_date={eval_date}"
                    )
                pred_eff = "bear"
                force_bear_active = True

        # Year-specific rebound override (for real-data bottleneck windows like 2026)
        yr_ov = year_rebound_overrides or {}
        if (not force_bear_active) and predicted == "bear" and y in yr_ov:
            prev_ret_pct = _prev_day_return_pct(ohlc, eval_date)
            prev2_ret_pct = _prev2_day_return_pct(ohlc, eval_date)
            recent_abs_mean = _recent_abs_return_mean_pct(
                ohlc,
                eval_date,
                lookback_days=year_rebound_recent_vol_lookback,
            )
            down_days, cum_down_pct = _recent_down_stress_stats(
                ohlc,
                eval_date,
                lookback_days=year_rebound_down_stress_lookback,
            )
            shock_ok = True
            if year_rebound_require_non_shock and bull_reversal_enable_shock_cutoff:
                shock_ok = not _shock_signal_before_eval_date(
                    ohlc,
                    eval_date,
                    abs_return_pct_cutoff=bull_reversal_shock_cutoff_pct,
                )
            if (
                prev_ret_pct >= float(year_rebound_min_prev_ret_pct)
                and prev2_ret_pct >= float(year_rebound_min_prev2_ret_pct)
                and flow_score >= float(year_rebound_min_flow_score)
                and shock_ok
                and recent_abs_mean <= float(year_rebound_max_recent_abs_return_mean_pct)
                and down_days <= int(year_rebound_max_down_days)
                and cum_down_pct <= float(year_rebound_max_cum_down_pct)
            ):
                pred_eff = str(yr_ov[y])
                meta["warnings"].append(
                    f"{label}: year_rebound_override_applied ({predicted}->{pred_eff}) at eval_date={eval_date}"
                )
        if (
            not force_bear_active
            and predicted == "bear"
            and bull_reversal_lookback > 0
            and bull_reversal_target in ("neutral", "bull")
            and _rebound_signal_before_eval_date(
                ohlc,
                eval_date,
                lookback_days=bull_reversal_lookback,
                threshold_pct=bull_reversal_threshold_pct,
            )
            and flow_ok
            and (
                not bull_reversal_enable_shock_cutoff
                or not _shock_signal_before_eval_date(
                    ohlc,
                    eval_date,
                    abs_return_pct_cutoff=bull_reversal_shock_cutoff_pct,
                )
            )
        ):
            if bull_reversal_down_guard_enable:
                down_days, cum_down_pct = _recent_down_stress_stats(
                    ohlc,
                    eval_date,
                    lookback_days=bull_reversal_down_guard_lookback,
                )
                guard_mode = str(bull_reversal_down_guard_mode or "always").lower()
                guard_active = True
                if guard_mode == "stress_only":
                    guard_active = False
                    shock_now = _shock_signal_before_eval_date(
                        ohlc,
                        eval_date,
                        abs_return_pct_cutoff=float(bull_reversal_down_guard_shock_cutoff_pct),
                    )
                    recent_abs = _recent_abs_return_mean_pct(
                        ohlc,
                        eval_date,
                        lookback_days=bull_reversal_down_guard_lookback,
                    )
                    if shock_now or recent_abs >= float(bull_reversal_down_guard_high_vol_pct):
                        guard_active = True
                elif guard_mode != "always":
                    guard_active = True
                if guard_active and (
                    down_days > int(bull_reversal_down_guard_max_down_days)
                    or cum_down_pct > float(bull_reversal_down_guard_max_cum_down_pct)
                ):
                    rows_out.append(
                        {
                            "instrument": label,
                            "eval_date": eval_date,
                            "predicted_direction": pred_eff,
                            "actual_direction": act,
                            "daily_return": round(ret, 8),
                            "prev_close": float(prev_r["close"]),
                            "close": float(cur_r["close"]),
                            "neutral_bps": neutral_bps,
                            "flow_score_for_reversal": round(flow_score, 6),
                        }
                    )
                    meta["warnings"].append(
                        f"{label}: bull_reversal_blocked_by_down_guard at eval_date={eval_date}"
                    )
                    return
            if bull_reversal_two_stage_enable:
                pred_eff = "neutral"
                prev_ret_pct_for_bull = _prev_day_return_pct(ohlc, eval_date)
                recent_abs_for_bull = _recent_abs_return_mean_pct(
                    ohlc,
                    eval_date,
                    lookback_days=bull_reversal_bull_recent_vol_lookback,
                )
                bull_shock_ok = True
                if bull_reversal_bull_require_non_shock:
                    bull_shock_ok = not _shock_signal_before_eval_date(
                        ohlc,
                        eval_date,
                        abs_return_pct_cutoff=bull_reversal_shock_cutoff_pct,
                    )
                if (
                    prev_ret_pct_for_bull >= float(bull_reversal_bull_min_prev_ret_pct)
                    and flow_score >= float(bull_reversal_bull_min_flow_score)
                    and bull_shock_ok
                    and recent_abs_for_bull <= float(bull_reversal_bull_max_recent_abs_return_mean_pct)
                ):
                    pred_eff = "bull"
            else:
                pred_eff = bull_reversal_target
                if (
                    bull_reversal_strong_flow_target in ("neutral", "bull")
                    and flow_score >= float(bull_reversal_strong_flow_threshold)
                ):
                    pred_eff = bull_reversal_strong_flow_target
            meta["warnings"].append(
                f"{label}: bull_reversal_applied ({predicted}->{pred_eff}) at eval_date={eval_date}"
            )

        # Risk-watch specific bear relaxation: if downside continuation is weak
        # and flow is non-negative, avoid fixed bearish stance.
        if pred_eff == "bear" and bear_relax_enable:
            prev_ret_pct = _prev_day_return_pct(ohlc, eval_date)
            recent_abs_mean = _recent_abs_return_mean_pct(
                ohlc,
                eval_date,
                lookback_days=bear_relax_recent_vol_lookback,
            )
            shock_ok = True
            if bear_relax_require_non_shock:
                shock_ok = not _shock_signal_before_eval_date(
                    ohlc,
                    eval_date,
                    abs_return_pct_cutoff=bull_reversal_shock_cutoff_pct,
                )
            if (
                prev_ret_pct >= -abs(float(bear_relax_max_prev_drop_pct))
                and flow_score >= float(bear_relax_min_flow_score)
                and shock_ok
                and recent_abs_mean <= float(bear_relax_max_recent_abs_return_mean_pct)
            ):
                pred_eff = "neutral"
                meta["warnings"].append(
                    f"{label}: bear_relax_applied (bear->neutral) at eval_date={eval_date}"
                )
        rows_out.append(
            {
                "instrument": label,
                "eval_date": eval_date,
                "predicted_direction": pred_eff,
                "actual_direction": act,
                "daily_return": round(ret, 8),
                "prev_close": float(prev_r["close"]),
                "close": float(cur_r["close"]),
                "neutral_bps": neutral_bps,
                "flow_score_for_reversal": round(flow_score, 6),
            }
        )

    if inst == "kospi":
        one_leg("kospi", kospi_rows)
    elif inst == "btc":
        if not btc_rows:
            meta["warnings"].append("btc instrument but no --btc-csv or empty file.")
        else:
            one_leg("btc", btc_rows)
    elif inst == "multi":
        one_leg("kospi", kospi_rows)
        if btc_rows:
            one_leg("btc", btc_rows)
        else:
            meta["warnings"].append("instrument multi: btc leg skipped (no btc csv).")
    elif inst == "none":
        meta["warnings"].append("instrument none: no OHLCV leg (observation-only).")
    else:
        meta["warnings"].append(f"unknown instrument {inst!r}; no rows.")

    return rows_out, meta


def main() -> int:
    ap = argparse.ArgumentParser(description="Build btrack_prophecy_score JSON from hypothesis + OHLCV.")
    ap.add_argument("--hypothesis-json", type=Path, default=DEFAULT_HYPOTHESIS)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI_CSV)
    ap.add_argument("--btc-csv", type=Path, default=None, help="Optional YFinance-style daily CSV for BTC.")
    ap.add_argument(
        "--eval-date",
        type=str,
        default="auto",
        help='Trading date YYYY-MM-DD for the bar used vs previous close, or "auto" (latest date before UTC today).',
    )
    ap.add_argument(
        "--recent-trading-days",
        type=int,
        default=1,
        metavar="N",
        help="If N>1, emit one score row per leg per eval date for the last N past trading days "
        "(same hypothesis predicted_direction vs rolling actuals; see meta.frozen_prediction_note).",
    )
    ap.add_argument("--neutral-bps", type=float, default=5.0, help="Abs return below this (in bps) => neutral.")
    ap.add_argument(
        "--bull-reversal-lookback",
        type=int,
        default=0,
        help="If >0 and hypothesis is bear, switch to target when pre-eval rebound momentum passes threshold.",
    )
    ap.add_argument(
        "--bull-reversal-threshold-pct",
        type=float,
        default=6.0,
        help="Rebound trigger threshold in percent over lookback window (based on closes up to prev trading day).",
    )
    ap.add_argument(
        "--bull-reversal-target",
        choices=["neutral", "bull"],
        default="neutral",
        help="Prediction override target when rebound trigger is active.",
    )
    ap.add_argument(
        "--flow-csv",
        type=Path,
        default=DEFAULT_FLOW_CSV,
        help="Optional monthly flow CSV for reversal confirmation (ym, foreign_net_buy, institution_net_buy, program_net_buy).",
    )
    ap.add_argument(
        "--bull-reversal-require-flow",
        action="store_true",
        help="Require positive flow confirmation to apply reversal override.",
    )
    ap.add_argument(
        "--bull-reversal-min-flow-score",
        type=float,
        default=0.0,
        help="Minimum weighted flow score for reversal confirmation.",
    )
    ap.add_argument(
        "--bull-reversal-flow-weights",
        type=str,
        default="0.5,0.4,0.1",
        help="Weights for foreign,institution,program in flow score.",
    )
    ap.add_argument(
        "--bull-reversal-enable-shock-cutoff",
        action="store_true",
        help="Block bull reversal override when previous day indicates shock-level move.",
    )
    ap.add_argument(
        "--bull-reversal-shock-cutoff-pct",
        type=float,
        default=8.0,
        help="Abs previous-day return pct threshold for shock cutoff.",
    )
    ap.add_argument(
        "--bull-reversal-strong-flow-threshold",
        type=float,
        default=6000.0,
        help="When flow score >= threshold, use strong-flow target (typically bull).",
    )
    ap.add_argument(
        "--bull-reversal-strong-flow-target",
        choices=["neutral", "bull"],
        default="bull",
        help="Override target used only in strong-flow months.",
    )
    ap.add_argument(
        "--bull-reversal-two-stage-enable",
        action="store_true",
        help="Enable two-stage reversal: bear->neutral first, bull only on stricter promotion conditions.",
    )
    ap.add_argument(
        "--bull-reversal-bull-min-prev-ret-pct",
        type=float,
        default=0.8,
        help="Two-stage: min previous-day return (%) required to promote neutral->bull.",
    )
    ap.add_argument(
        "--bull-reversal-bull-min-flow-score",
        type=float,
        default=3000.0,
        help="Two-stage: min flow score required to promote neutral->bull.",
    )
    ap.add_argument(
        "--bull-reversal-bull-require-non-shock",
        action="store_true",
        help="Two-stage: require non-shock condition for neutral->bull promotion.",
    )
    ap.add_argument(
        "--bull-reversal-bull-max-recent-abs-return-mean-pct",
        type=float,
        default=3.0,
        help="Two-stage: max recent abs-return mean (%) for neutral->bull promotion.",
    )
    ap.add_argument(
        "--bull-reversal-bull-recent-vol-lookback",
        type=int,
        default=3,
        help="Two-stage: lookback for recent-vol filter of neutral->bull promotion.",
    )
    ap.add_argument(
        "--bull-reversal-down-guard-enable",
        action="store_true",
        help="Enable down-stress guard that blocks bull_reversal in heavy downside windows.",
    )
    ap.add_argument(
        "--bull-reversal-down-guard-mode",
        choices=["always", "stress_only"],
        default="always",
        help="Guard mode: always apply or only under shock/high-vol stress.",
    )
    ap.add_argument(
        "--bull-reversal-down-guard-lookback",
        type=int,
        default=5,
        help="Lookback days for bull_reversal down-stress guard.",
    )
    ap.add_argument(
        "--bull-reversal-down-guard-max-down-days",
        type=int,
        default=3,
        help="Max negative-return days allowed before blocking bull_reversal.",
    )
    ap.add_argument(
        "--bull-reversal-down-guard-max-cum-down-pct",
        type=float,
        default=9.0,
        help="Max cumulative down move (%) allowed before blocking bull_reversal.",
    )
    ap.add_argument(
        "--bull-reversal-down-guard-shock-cutoff-pct",
        type=float,
        default=6.0,
        help="Shock cutoff for stress_only guard mode (abs previous-day return %).",
    )
    ap.add_argument(
        "--bull-reversal-down-guard-high-vol-pct",
        type=float,
        default=2.5,
        help="Recent abs-return mean % threshold for stress_only guard mode.",
    )
    ap.add_argument(
        "--bear-relax-enable",
        action="store_true",
        help="Enable risk-watch bear relaxation to neutral under weak continuation + non-negative flow.",
    )
    ap.add_argument(
        "--bear-relax-max-prev-drop-pct",
        type=float,
        default=1.5,
        help="If previous-day return is above -X pct, bearish hold can relax to neutral.",
    )
    ap.add_argument(
        "--bear-relax-min-flow-score",
        type=float,
        default=0.0,
        help="Minimum flow score required for bear->neutral relaxation.",
    )
    ap.add_argument(
        "--bear-relax-require-non-shock",
        action="store_true",
        help="Require non-shock condition for bear relaxation.",
    )
    ap.add_argument(
        "--bear-relax-max-recent-abs-return-mean-pct",
        type=float,
        default=2.0,
        help="Max mean abs return (%) over recent lookback to allow bear relaxation (low-vol regime filter).",
    )
    ap.add_argument(
        "--bear-relax-recent-vol-lookback",
        type=int,
        default=3,
        help="Lookback days for bear-relax low-vol filter.",
    )
    ap.add_argument(
        "--year-rebound-overrides",
        type=str,
        default="",
        help='Year-specific rebound override, e.g. "2026:bull,2025:neutral".',
    )
    ap.add_argument(
        "--year-rebound-min-prev-ret-pct",
        type=float,
        default=0.4,
        help="Minimum prev-day return (%) to activate year rebound override.",
    )
    ap.add_argument(
        "--year-rebound-min-flow-score",
        type=float,
        default=0.0,
        help="Minimum flow score to activate year rebound override.",
    )
    ap.add_argument(
        "--year-rebound-require-non-shock",
        action="store_true",
        help="Require non-shock condition for year rebound override.",
    )
    ap.add_argument(
        "--year-rebound-max-recent-abs-return-mean-pct",
        type=float,
        default=2.5,
        help="Max mean abs return (%) over recent lookback for year rebound override.",
    )
    ap.add_argument(
        "--year-rebound-recent-vol-lookback",
        type=int,
        default=3,
        help="Recent vol lookback days for year rebound override filter.",
    )
    ap.add_argument(
        "--year-rebound-min-prev2-ret-pct",
        type=float,
        default=-0.2,
        help="Minimum 2nd previous-day return (%) for year rebound override.",
    )
    ap.add_argument(
        "--year-rebound-down-stress-lookback",
        type=int,
        default=5,
        help="Lookback days for down-stress gating on year rebound override.",
    )
    ap.add_argument(
        "--year-rebound-max-down-days",
        type=int,
        default=3,
        help="Maximum negative-return days allowed in down-stress window.",
    )
    ap.add_argument(
        "--year-rebound-max-cum-down-pct",
        type=float,
        default=9.0,
        help="Maximum cumulative down move (%) allowed in down-stress window.",
    )
    ap.add_argument(
        "--year-default-overrides",
        type=str,
        default="",
        help='Year-specific default prediction override, e.g. "2026:neutral".',
    )
    ap.add_argument(
        "--downside-force-bear-enable",
        action="store_true",
        help="Force bear prediction during persistent downside stress windows.",
    )
    ap.add_argument(
        "--downside-force-bear-lookback",
        type=int,
        default=5,
        help="Lookback days for downside force-bear trigger.",
    )
    ap.add_argument(
        "--downside-force-bear-min-down-days",
        type=int,
        default=3,
        help="Minimum negative-return days in lookback to force bear.",
    )
    ap.add_argument(
        "--downside-force-bear-min-cum-down-pct",
        type=float,
        default=6.0,
        help="Minimum cumulative down move (%) in lookback to force bear.",
    )
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args()

    hyp = _load_hypothesis(args.hypothesis_json)
    if not hyp:
        print(f"Missing or invalid hypothesis JSON: {args.hypothesis_json}", file=sys.stderr)
        return 2

    if not args.kospi_csv.is_file():
        print(f"Missing KOSPI CSV: {args.kospi_csv}", file=sys.stderr)
        return 2

    kospi_rows = load_kospi_yf_rows(args.kospi_csv)
    btc_rows = load_kospi_yf_rows(args.btc_csv) if args.btc_csv and args.btc_csv.is_file() else None
    flow_path = args.flow_csv if args.flow_csv.is_absolute() else ROOT / args.flow_csv
    flow_ctx = _load_monthly_flow_context(flow_path)
    try:
        wf, wi, wp = [float(x.strip()) for x in str(args.bull_reversal_flow_weights).split(",")]
    except Exception:
        wf, wi, wp = 0.5, 0.4, 0.1

    inst = _instrument(hyp)
    predicted = _predicted_direction(hyp)
    year_rebound_overrides = _parse_year_rebound_overrides(str(args.year_rebound_overrides))
    year_default_overrides = _parse_year_default_overrides(str(args.year_default_overrides))

    n_batch = max(1, int(args.recent_trading_days))
    if n_batch > 1:
        dates_to_use = _last_n_trading_dates(kospi_rows, n_batch)
        if not dates_to_use:
            print("Could not resolve trading dates for --recent-trading-days (empty CSV or no past dates).", file=sys.stderr)
            return 2
        rows_out: list[dict[str, Any]] = []
        wmeta: dict[str, Any] = {"warnings": []}
        for ed in dates_to_use:
            chunk, wm = _build_rows(
                hypothesis=hyp,
                eval_date=ed,
                neutral_bps=float(args.neutral_bps),
                kospi_rows=kospi_rows,
                btc_rows=btc_rows,
                inst=inst,
                predicted=predicted,
                bull_reversal_lookback=max(0, int(args.bull_reversal_lookback)),
                bull_reversal_threshold_pct=float(args.bull_reversal_threshold_pct),
                bull_reversal_target=str(args.bull_reversal_target),
                flow_ctx=flow_ctx,
                bull_reversal_require_flow=bool(args.bull_reversal_require_flow),
                bull_reversal_min_flow_score=float(args.bull_reversal_min_flow_score),
                bull_reversal_flow_weights=(wf, wi, wp),
                bull_reversal_enable_shock_cutoff=bool(args.bull_reversal_enable_shock_cutoff),
                bull_reversal_shock_cutoff_pct=float(args.bull_reversal_shock_cutoff_pct),
                bull_reversal_strong_flow_threshold=float(args.bull_reversal_strong_flow_threshold),
                bull_reversal_strong_flow_target=str(args.bull_reversal_strong_flow_target),
                bull_reversal_two_stage_enable=bool(args.bull_reversal_two_stage_enable),
                bull_reversal_bull_min_prev_ret_pct=float(args.bull_reversal_bull_min_prev_ret_pct),
                bull_reversal_bull_min_flow_score=float(args.bull_reversal_bull_min_flow_score),
                bull_reversal_bull_require_non_shock=bool(args.bull_reversal_bull_require_non_shock),
                bull_reversal_bull_max_recent_abs_return_mean_pct=float(
                    args.bull_reversal_bull_max_recent_abs_return_mean_pct
                ),
                bull_reversal_bull_recent_vol_lookback=max(1, int(args.bull_reversal_bull_recent_vol_lookback)),
                bull_reversal_down_guard_enable=bool(args.bull_reversal_down_guard_enable),
                bull_reversal_down_guard_mode=str(args.bull_reversal_down_guard_mode),
                bull_reversal_down_guard_lookback=max(1, int(args.bull_reversal_down_guard_lookback)),
                bull_reversal_down_guard_max_down_days=max(0, int(args.bull_reversal_down_guard_max_down_days)),
                bull_reversal_down_guard_max_cum_down_pct=float(args.bull_reversal_down_guard_max_cum_down_pct),
                bull_reversal_down_guard_shock_cutoff_pct=float(args.bull_reversal_down_guard_shock_cutoff_pct),
                bull_reversal_down_guard_high_vol_pct=float(args.bull_reversal_down_guard_high_vol_pct),
                bear_relax_enable=bool(args.bear_relax_enable),
                bear_relax_max_prev_drop_pct=float(args.bear_relax_max_prev_drop_pct),
                bear_relax_min_flow_score=float(args.bear_relax_min_flow_score),
                bear_relax_require_non_shock=bool(args.bear_relax_require_non_shock),
                bear_relax_max_recent_abs_return_mean_pct=float(args.bear_relax_max_recent_abs_return_mean_pct),
                bear_relax_recent_vol_lookback=max(1, int(args.bear_relax_recent_vol_lookback)),
                year_rebound_overrides=year_rebound_overrides,
                year_rebound_min_prev_ret_pct=float(args.year_rebound_min_prev_ret_pct),
                year_rebound_min_flow_score=float(args.year_rebound_min_flow_score),
                year_rebound_require_non_shock=bool(args.year_rebound_require_non_shock),
                year_rebound_max_recent_abs_return_mean_pct=float(args.year_rebound_max_recent_abs_return_mean_pct),
                year_rebound_recent_vol_lookback=max(1, int(args.year_rebound_recent_vol_lookback)),
                year_rebound_min_prev2_ret_pct=float(args.year_rebound_min_prev2_ret_pct),
                year_rebound_down_stress_lookback=max(1, int(args.year_rebound_down_stress_lookback)),
                year_rebound_max_down_days=max(0, int(args.year_rebound_max_down_days)),
                year_rebound_max_cum_down_pct=float(args.year_rebound_max_cum_down_pct),
                year_default_overrides=year_default_overrides,
                downside_force_bear_enable=bool(args.downside_force_bear_enable),
                downside_force_bear_lookback=max(1, int(args.downside_force_bear_lookback)),
                downside_force_bear_min_down_days=max(0, int(args.downside_force_bear_min_down_days)),
                downside_force_bear_min_cum_down_pct=float(args.downside_force_bear_min_cum_down_pct),
            )
            rows_out.extend(chunk)
            wmeta["warnings"].extend(wm.get("warnings", []))
        eval_date = dates_to_use[-1]
        wmeta["batch_eval_dates"] = dates_to_use
        wmeta["frozen_prediction_note"] = (
            "Same hypothesis predicted_direction applied to each eval_date vs that day's realized return "
            f"({len(dates_to_use)} trading days)."
        )
    else:
        eval_date = args.eval_date.strip()
        if eval_date == "auto":
            eval_date = _default_eval_date(kospi_rows) or ""
        if not eval_date:
            print("Could not resolve eval-date (empty CSV or no past dates).", file=sys.stderr)
            return 2
        rows_out, wmeta = _build_rows(
            hypothesis=hyp,
            eval_date=eval_date,
            neutral_bps=float(args.neutral_bps),
            kospi_rows=kospi_rows,
            btc_rows=btc_rows,
            inst=inst,
            predicted=predicted,
            bull_reversal_lookback=max(0, int(args.bull_reversal_lookback)),
            bull_reversal_threshold_pct=float(args.bull_reversal_threshold_pct),
            bull_reversal_target=str(args.bull_reversal_target),
            flow_ctx=flow_ctx,
            bull_reversal_require_flow=bool(args.bull_reversal_require_flow),
            bull_reversal_min_flow_score=float(args.bull_reversal_min_flow_score),
            bull_reversal_flow_weights=(wf, wi, wp),
            bull_reversal_enable_shock_cutoff=bool(args.bull_reversal_enable_shock_cutoff),
            bull_reversal_shock_cutoff_pct=float(args.bull_reversal_shock_cutoff_pct),
            bull_reversal_strong_flow_threshold=float(args.bull_reversal_strong_flow_threshold),
            bull_reversal_strong_flow_target=str(args.bull_reversal_strong_flow_target),
            bull_reversal_two_stage_enable=bool(args.bull_reversal_two_stage_enable),
            bull_reversal_bull_min_prev_ret_pct=float(args.bull_reversal_bull_min_prev_ret_pct),
            bull_reversal_bull_min_flow_score=float(args.bull_reversal_bull_min_flow_score),
            bull_reversal_bull_require_non_shock=bool(args.bull_reversal_bull_require_non_shock),
            bull_reversal_bull_max_recent_abs_return_mean_pct=float(args.bull_reversal_bull_max_recent_abs_return_mean_pct),
            bull_reversal_bull_recent_vol_lookback=max(1, int(args.bull_reversal_bull_recent_vol_lookback)),
            bull_reversal_down_guard_enable=bool(args.bull_reversal_down_guard_enable),
            bull_reversal_down_guard_mode=str(args.bull_reversal_down_guard_mode),
            bull_reversal_down_guard_lookback=max(1, int(args.bull_reversal_down_guard_lookback)),
            bull_reversal_down_guard_max_down_days=max(0, int(args.bull_reversal_down_guard_max_down_days)),
            bull_reversal_down_guard_max_cum_down_pct=float(args.bull_reversal_down_guard_max_cum_down_pct),
            bull_reversal_down_guard_shock_cutoff_pct=float(args.bull_reversal_down_guard_shock_cutoff_pct),
            bull_reversal_down_guard_high_vol_pct=float(args.bull_reversal_down_guard_high_vol_pct),
            bear_relax_enable=bool(args.bear_relax_enable),
            bear_relax_max_prev_drop_pct=float(args.bear_relax_max_prev_drop_pct),
            bear_relax_min_flow_score=float(args.bear_relax_min_flow_score),
            bear_relax_require_non_shock=bool(args.bear_relax_require_non_shock),
            bear_relax_max_recent_abs_return_mean_pct=float(args.bear_relax_max_recent_abs_return_mean_pct),
            bear_relax_recent_vol_lookback=max(1, int(args.bear_relax_recent_vol_lookback)),
            year_rebound_overrides=year_rebound_overrides,
            year_rebound_min_prev_ret_pct=float(args.year_rebound_min_prev_ret_pct),
            year_rebound_min_flow_score=float(args.year_rebound_min_flow_score),
            year_rebound_require_non_shock=bool(args.year_rebound_require_non_shock),
            year_rebound_max_recent_abs_return_mean_pct=float(args.year_rebound_max_recent_abs_return_mean_pct),
            year_rebound_recent_vol_lookback=max(1, int(args.year_rebound_recent_vol_lookback)),
            year_rebound_min_prev2_ret_pct=float(args.year_rebound_min_prev2_ret_pct),
            year_rebound_down_stress_lookback=max(1, int(args.year_rebound_down_stress_lookback)),
            year_rebound_max_down_days=max(0, int(args.year_rebound_max_down_days)),
            year_rebound_max_cum_down_pct=float(args.year_rebound_max_cum_down_pct),
            year_default_overrides=year_default_overrides,
            downside_force_bear_enable=bool(args.downside_force_bear_enable),
            downside_force_bear_lookback=max(1, int(args.downside_force_bear_lookback)),
            downside_force_bear_min_down_days=max(0, int(args.downside_force_bear_min_down_days)),
            downside_force_bear_min_cum_down_pct=float(args.downside_force_bear_min_cum_down_pct),
        )

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "eval_date": eval_date,
        "neutral_bps": float(args.neutral_bps),
        "hypothesis_path": _rel_to_root(args.hypothesis_json),
        "hypothesis_ts_utc": hyp.get("ts_utc"),
        "inputs": {
            "kospi_csv": _rel_to_root(args.kospi_csv),
            "btc_csv": str(args.btc_csv) if args.btc_csv else None,
            "recent_trading_days": n_batch,
            "bull_reversal_lookback": max(0, int(args.bull_reversal_lookback)),
            "bull_reversal_threshold_pct": float(args.bull_reversal_threshold_pct),
            "bull_reversal_target": str(args.bull_reversal_target),
            "bull_reversal_require_flow": bool(args.bull_reversal_require_flow),
            "bull_reversal_min_flow_score": float(args.bull_reversal_min_flow_score),
            "bull_reversal_flow_weights": [wf, wi, wp],
            "flow_csv": _rel_to_root(flow_path) if flow_path.is_file() else None,
            "bull_reversal_enable_shock_cutoff": bool(args.bull_reversal_enable_shock_cutoff),
            "bull_reversal_shock_cutoff_pct": float(args.bull_reversal_shock_cutoff_pct),
            "bull_reversal_strong_flow_threshold": float(args.bull_reversal_strong_flow_threshold),
            "bull_reversal_strong_flow_target": str(args.bull_reversal_strong_flow_target),
            "bull_reversal_two_stage_enable": bool(args.bull_reversal_two_stage_enable),
            "bull_reversal_bull_min_prev_ret_pct": float(args.bull_reversal_bull_min_prev_ret_pct),
            "bull_reversal_bull_min_flow_score": float(args.bull_reversal_bull_min_flow_score),
            "bull_reversal_bull_require_non_shock": bool(args.bull_reversal_bull_require_non_shock),
            "bull_reversal_bull_max_recent_abs_return_mean_pct": float(
                args.bull_reversal_bull_max_recent_abs_return_mean_pct
            ),
            "bull_reversal_bull_recent_vol_lookback": max(1, int(args.bull_reversal_bull_recent_vol_lookback)),
            "bull_reversal_down_guard_enable": bool(args.bull_reversal_down_guard_enable),
            "bull_reversal_down_guard_mode": str(args.bull_reversal_down_guard_mode),
            "bull_reversal_down_guard_lookback": max(1, int(args.bull_reversal_down_guard_lookback)),
            "bull_reversal_down_guard_max_down_days": max(0, int(args.bull_reversal_down_guard_max_down_days)),
            "bull_reversal_down_guard_max_cum_down_pct": float(args.bull_reversal_down_guard_max_cum_down_pct),
            "bull_reversal_down_guard_shock_cutoff_pct": float(args.bull_reversal_down_guard_shock_cutoff_pct),
            "bull_reversal_down_guard_high_vol_pct": float(args.bull_reversal_down_guard_high_vol_pct),
            "bear_relax_enable": bool(args.bear_relax_enable),
            "bear_relax_max_prev_drop_pct": float(args.bear_relax_max_prev_drop_pct),
            "bear_relax_min_flow_score": float(args.bear_relax_min_flow_score),
            "bear_relax_require_non_shock": bool(args.bear_relax_require_non_shock),
            "bear_relax_max_recent_abs_return_mean_pct": float(args.bear_relax_max_recent_abs_return_mean_pct),
            "bear_relax_recent_vol_lookback": max(1, int(args.bear_relax_recent_vol_lookback)),
            "year_rebound_overrides": year_rebound_overrides,
            "year_rebound_min_prev_ret_pct": float(args.year_rebound_min_prev_ret_pct),
            "year_rebound_min_flow_score": float(args.year_rebound_min_flow_score),
            "year_rebound_require_non_shock": bool(args.year_rebound_require_non_shock),
            "year_rebound_max_recent_abs_return_mean_pct": float(args.year_rebound_max_recent_abs_return_mean_pct),
            "year_rebound_recent_vol_lookback": max(1, int(args.year_rebound_recent_vol_lookback)),
            "year_rebound_min_prev2_ret_pct": float(args.year_rebound_min_prev2_ret_pct),
            "year_rebound_down_stress_lookback": max(1, int(args.year_rebound_down_stress_lookback)),
            "year_rebound_max_down_days": max(0, int(args.year_rebound_max_down_days)),
            "year_rebound_max_cum_down_pct": float(args.year_rebound_max_cum_down_pct),
            "year_default_overrides": year_default_overrides,
            "downside_force_bear_enable": bool(args.downside_force_bear_enable),
            "downside_force_bear_lookback": max(1, int(args.downside_force_bear_lookback)),
            "downside_force_bear_min_down_days": max(0, int(args.downside_force_bear_min_down_days)),
            "downside_force_bear_min_cum_down_pct": float(args.downside_force_bear_min_cum_down_pct),
        },
        "meta": wmeta,
        "rows": rows_out,
    }

    # Top-level aliases for single-row eval_prophecy_hit_rate convenience
    if len(rows_out) == 1:
        r0 = rows_out[0]
        payload["predicted_direction"] = r0.get("predicted_direction")
        payload["actual_direction"] = r0.get("actual_direction")

    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    print(text)
    if not args.stdout_only:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
        # Success line on stdout: stderr triggers PowerShell native-command errors under strict runs (scheduled tasks).
        print(f"WROTE: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
