# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.8, K:0.4, M:0.6}
# Balance: 90
# Purpose: Generate 2026 monthly KOSPI/BTC fact-safe prophecy draft.
# Keywords: kospi, btc, monthly, prophecy, fact-safe
"""Generate 2026 monthly KOSPI/BTC fact-safe scenario report."""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

try:
    from scripts.core.mkm12_singular_core import CoreInput, compute_core_score
except ModuleNotFoundError:
    from core.mkm12_singular_core import CoreInput, compute_core_score

ROOT = Path(__file__).resolve().parents[1]
ART_DIR = ROOT / "docs" / "final" / "artifacts"
OUT_JSON = ART_DIR / "prophecy_2026_monthly_kospi_btc_fact_safe_v1.json"
OUT_MD = ART_DIR / "prophecy_2026_monthly_kospi_btc_fact_safe_v1.md"

GATE_JSON = ART_DIR / "high_reliability_mode_gate_latest.json"
WAITING_LOG = ART_DIR / "waiting_queue_monthly_check_log.jsonl"
BTC_SWEEP = ART_DIR / "btc_time_machine_sweep_latest.json"
K_SHIELD_SWEEP = ART_DIR / "btc_k_shield_fast_sweep_2025_latest.json"
KPI_JSONL_GLOB = ROOT / "projects" / "bitcoin-trading" / "memory" / "kpi" / "kpi_snapshot_*.jsonl"
KOSPI_CSV = ROOT / "research" / "market_data" / "kospi_daily_external_yf.csv"

SCORING_RULE = {
    "label": "trinity_daily_hypothesis_v1",
    "target_metric": "KOSPI_D1_RETURN_PCT",
    "target_condition": "return_pct <= -0.8",
    "falsification_condition": "return_pct >= +1.5",
    "hit_threshold_pct": -0.8,
    "fail_threshold_pct": 1.5,
    "neutral_draw_range_open": (-0.8, 1.5),
    "labels": {
        "hit": "HIT",
        "fail": "FAIL",
        "neutral_draw": "NEUTRAL_DRAW",
    },
    "neutral_draw_policy": "exclude_from_win_loss; keep_or_small_penalty_weight",
}

OBSERVED_LEVER_PRIORITY = [
    "overnight_global_risk",
    "usdkrw_fx",
    "rates_front_end",
    "semiconductor_news",
    "foreign_institutional_flow",
]


def _z_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def _latest_jsonl(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    lines = [x for x in path.read_text(encoding="utf-8", errors="ignore").splitlines() if x.strip()]
    if not lines:
        return {}
    try:
        row = json.loads(lines[-1])
    except Exception:
        return {}
    return row if isinstance(row, dict) else {}


def _tail_jsonl(path: Path, limit: int = 1500) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows[-limit:]


def _kpi_history_stats(days: int = 7) -> tuple[int, float]:
    if KPI_JSONL_GLOB.is_absolute():
        paths = sorted(KPI_JSONL_GLOB.parent.glob(KPI_JSONL_GLOB.name), reverse=True)
    else:
        paths = sorted(ROOT.glob(str(KPI_JSONL_GLOB)), reverse=True)
    if not paths:
        return 0, 0.0
    cutoff = datetime.now(timezone.utc).timestamp() - days * 24 * 60 * 60
    rows: list[dict[str, Any]] = []
    for path in paths:
        for row in reversed(_tail_jsonl(path, limit=1500)):
            ts = row.get("ts_utc")
            if not isinstance(ts, str):
                continue
            try:
                ts_epoch = datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
            except Exception:
                continue
            if ts_epoch < cutoff:
                continue
            rows.append(row)
        if len(rows) >= 500:
            break
    rows.reverse()
    net_series = [float(r.get("exchange_snapshot_24h_net")) for r in rows if isinstance(r.get("exchange_snapshot_24h_net"), (int, float))]
    net_delta = (net_series[-1] - net_series[0]) if len(net_series) >= 2 else 0.0
    return len(rows), net_delta


def _compute_badge(engine_id: str, samples: int, net_delta: float) -> str:
    if engine_id == "V1_Approx_Stub" or samples < 10:
        return "LOW"
    if engine_id == "V2_Precision_MCP" and 10 <= samples <= 49:
        return "MID"
    if engine_id == "V2_Precision_MCP" and samples >= 50 and net_delta > 0:
        return "HIGH"
    return "MID"


def _month_phase(month: int) -> str:
    if month in (1, 2, 3):
        return "기준선/탐색"
    if month in (4, 5, 6):
        return "압박/방어"
    if month in (7, 8, 9):
        return "재정비/경쟁"
    return "성과 회수/정리"


def _logos_regime_score(year: int, month: int) -> float:
    """
    Heuristic regime pressure score (0..1).
    7-year cycle is treated as a risk governor signal, not a price trigger.
    """
    cycle_idx = year % 7
    cycle_pressure = {
        0: 0.75,
        1: 0.55,
        2: 0.45,
        3: 0.50,
        4: 0.60,
        5: 0.70,
        6: 0.80,
    }.get(cycle_idx, 0.60)
    month_pressure = 0.70 if month in (4, 5, 9) else 0.50
    return round((cycle_pressure * 0.7) + (month_pressure * 0.3), 4)


def _myeongri_timing_score(phase: str) -> float:
    return {
        "기준선/탐색": 0.48,
        "압박/방어": 0.72,
        "재정비/경쟁": 0.58,
        "성과 회수/정리": 0.42,
    }.get(phase, 0.55)


def _sasang_response_score(phase: str) -> float:
    return {
        "기준선/탐색": 0.50,
        "압박/방어": 0.68,
        "재정비/경쟁": 0.56,
        "성과 회수/정리": 0.46,
    }.get(phase, 0.55)


def _build_risk_profile(phase: str, hold_mode: bool, year: int, month: int) -> dict[str, Any]:
    logos_regime_score = _logos_regime_score(year=year, month=month)
    myeongri_timing_score = _myeongri_timing_score(phase)
    sasang_response_score = _sasang_response_score(phase)
    fused_risk_pressure = round(
        (logos_regime_score * 0.5) + (myeongri_timing_score * 0.3) + (sasang_response_score * 0.2),
        4,
    )
    # Up to 80% quantity reduction at high pressure.
    position_scale_cap = round(max(0.2, 1.0 - (fused_risk_pressure * 0.8)), 4)
    if hold_mode:
        position_scale_cap = min(position_scale_cap, 0.2)
    daily_loss_cap_pct = round(max(0.6, 1.8 - (fused_risk_pressure * 1.2)), 4)
    return {
        "logos_regime_score": logos_regime_score,
        "myeongri_timing_score": myeongri_timing_score,
        "sasang_response_score": sasang_response_score,
        "fused_risk_pressure": fused_risk_pressure,
        "position_scale_cap": position_scale_cap,
        "daily_loss_cap_pct": daily_loss_cap_pct,
        "mode": "LOCKED_MODE" if hold_mode else "ACTIVE_MODE",
        "governance_note": (
            "Trinity scores are risk governors only; they cannot unlock direct price-level output."
        ),
    }


def _mechanism_score(best_metrics: dict[str, Any], net_delta_7d: float) -> float:
    pf = float(best_metrics.get("profit_factor") or 0.0)
    net = float(best_metrics.get("net_return_pct") or 0.0)
    pf_norm = max(0.0, min(1.0, pf / 2.0))
    net_norm = max(0.0, min(1.0, (net + 10.0) / 20.0))
    net_delta_norm = max(0.0, min(1.0, (net_delta_7d + 10.0) / 20.0))
    return round((pf_norm * 0.4) + (net_norm * 0.4) + (net_delta_norm * 0.2), 4)


def _merge_gate_decision(base_decision: str, core_decision: str) -> tuple[str, str]:
    if str(base_decision).upper() == "HOLD":
        return "HOLD", "base_gate_hold_preserved"
    if core_decision == "HOLD":
        return "HOLD", "core_forced_hold"
    return "PASS", "base_and_core_pass"


def _base_probs(phase: str) -> tuple[int, int, int]:
    # up, neutral, down
    if phase == "기준선/탐색":
        return (34, 36, 30)
    if phase == "압박/방어":
        return (24, 34, 42)
    if phase == "재정비/경쟁":
        return (33, 35, 32)
    return (38, 34, 28)


def _adjust_for_hold(
    up: int,
    neutral: int,
    down: int,
    hold_mode: bool,
    *,
    momentum_score: float,
) -> tuple[int, int, int]:
    if not hold_mode:
        return up, neutral, down
    if momentum_score >= 0.62:
        # In HOLD, keep slight defense but avoid hard down-bias under strong observed up momentum.
        up2 = max(10, up - 1)
        down2 = min(70, down + 1)
        neutral2 = 100 - up2 - down2
        return up2, neutral2, down2
    # Conservative shift while preserving total 100.
    up2 = max(10, up - 4)
    down2 = min(70, down + 4)
    neutral2 = 100 - up2 - down2
    return up2, neutral2, down2


def _monthly_returns_from_csv(path: Path) -> list[dict[str, Any]]:
    import csv

    rows: list[tuple[date, float]] = []
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        for row in r:
            try:
                d = date.fromisoformat(str(row["Date"])[:10])
                c = float(row["Close"])
            except Exception:
                continue
            rows.append((d, c))
    rows.sort(key=lambda x: x[0])
    by_ym: dict[tuple[int, int], list[float]] = {}
    for d, c in rows:
        by_ym.setdefault((d.year, d.month), []).append(c)
    out: list[dict[str, Any]] = []
    for (y, m), seq in sorted(by_ym.items()):
        if len(seq) < 2 or seq[0] <= 0:
            continue
        out.append({"year": y, "month": m, "return_pct": (seq[-1] / seq[0] - 1.0) * 100.0})
    return out


def _recent_market_momentum(path: Path, *, lookback: int = 3) -> dict[str, Any]:
    months = _monthly_returns_from_csv(path)
    if not months:
        return {"score": 0.5, "avg_return_pct": 0.0, "up_ratio": 0.5, "n": 0}
    tail = months[-max(1, lookback) :]
    vals = [float(r["return_pct"]) for r in tail]
    avg = sum(vals) / len(vals)
    up_ratio = sum(1 for v in vals if v > 0) / len(vals)
    score = max(0.0, min(1.0, 0.5 + avg / 20.0 + (up_ratio - 0.5) * 0.3))
    return {
        "score": round(score, 6),
        "avg_return_pct": round(avg, 6),
        "up_ratio": round(up_ratio, 6),
        "n": len(vals),
    }


def _apply_market_momentum_overlay(
    up: int,
    neutral: int,
    down: int,
    *,
    phase: str,
    momentum_score: float,
) -> tuple[int, int, int]:
    # Fast reactive overlay: strong observed up momentum should reduce mechanical down-bias.
    if momentum_score >= 0.62:
        shift = {"기준선/탐색": 8, "압박/방어": 6, "재정비/경쟁": 5, "성과 회수/정리": 3}.get(phase, 4)
        up2 = min(85, up + shift)
        down2 = max(5, down - shift)
        neutral2 = 100 - up2 - down2
        return up2, neutral2, down2
    if momentum_score <= 0.38:
        shift = {"기준선/탐색": 5, "압박/방어": 6, "재정비/경쟁": 4, "성과 회수/정리": 3}.get(phase, 4)
        up2 = max(5, up - shift)
        down2 = min(85, down + shift)
        neutral2 = 100 - up2 - down2
        return up2, neutral2, down2
    return up, neutral, down


def _sasang_external_profile() -> dict[str, Any]:
    return {
        "schema": "sasang_external_market_profile_v1",
        "shock_abs_return_threshold_pct": 8.0,
        "high_vol_threshold_pct": 4.0,
        "momentum_window": 3,
        "momentum_warn_threshold_pct": 1.0,
        "seongjeong_overlay_enabled": False,
        "seongjeong_overlay_strength": 0.22,
        "seongjeong_activation_mode": "always",
        "phase_bias": {
            "기준선/탐색": 0.1,
            "압박/방어": -0.35,
            "재정비/경쟁": -0.05,
            "성과 회수/정리": 0.2,
        },
        "max_shift_pct": 12,
        "base_shift_pct": 3,
        "high_vol_neutral_guard_enabled": True,
        "high_vol_neutral_guard_threshold_pct": 4.0,
        "high_vol_neutral_min_pct": 40,
        "high_vol_defensive_shock_threshold_pct": 10.0,
        "high_vol_defensive_down_bonus_pct": 3,
        "multi_event_prior_enabled": True,
        "event_streak_days": 2,
        "event_streak_threshold_pct": -3.0,
        "event_vol_break_threshold_pct": 4.5,
        "event_directional_bonus_pct": 4,
    }


def _clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _normalize_probs(up: int, neutral: int, down: int) -> tuple[int, int, int]:
    up2 = int(max(5, min(90, up)))
    down2 = int(max(5, min(90, down)))
    neutral2 = int(max(5, 100 - up2 - down2))
    s = up2 + neutral2 + down2
    if s != 100:
        neutral2 += 100 - s
    return up2, neutral2, down2


def _apply_high_vol_guard(
    up: int,
    neutral: int,
    down: int,
    *,
    prev_ret: float,
    roll_abs_3m: float,
    profile: dict[str, Any],
) -> tuple[int, int, int, dict[str, Any]]:
    guard_enabled = bool(profile.get("high_vol_neutral_guard_enabled", True))
    guard_thr = float(profile.get("high_vol_neutral_guard_threshold_pct", 4.0))
    neutral_min = int(profile.get("high_vol_neutral_min_pct", 40))
    defensive_shock_thr = float(profile.get("high_vol_defensive_shock_threshold_pct", 10.0))
    down_bonus = int(profile.get("high_vol_defensive_down_bonus_pct", 3))
    applied = False
    defensive = False

    if guard_enabled and roll_abs_3m >= guard_thr:
        applied = True
        if neutral < neutral_min:
            shift = neutral_min - neutral
            # Pull from the dominant directional side first.
            if up >= down:
                up -= shift
            else:
                down -= shift
            neutral = neutral_min
        if abs(prev_ret) >= defensive_shock_thr and prev_ret < 0:
            defensive = True
            up -= down_bonus
            down += down_bonus
        up, neutral, down = _normalize_probs(up, neutral, down)

    return up, neutral, down, {"applied": applied, "defensive": defensive}


def _apply_multi_event_prior(
    up: int,
    neutral: int,
    down: int,
    *,
    prev_vals: list[float],
    prev_ret: float,
    roll_abs_3m: float,
    profile: dict[str, Any],
) -> tuple[int, int, int, dict[str, Any]]:
    enabled = bool(profile.get("multi_event_prior_enabled", True))
    streak_days = int(max(1, profile.get("event_streak_days", 2)))
    streak_thr = float(profile.get("event_streak_threshold_pct", -3.0))
    vol_break_thr = float(profile.get("event_vol_break_threshold_pct", 4.5))
    bonus = int(profile.get("event_directional_bonus_pct", 4))
    down_streak = False
    vol_break = False
    shock_event = False
    applied = False

    tail = prev_vals[-streak_days:] if prev_vals else []
    if len(tail) >= streak_days:
        down_streak = all(v <= streak_thr for v in tail)
    vol_break = roll_abs_3m >= vol_break_thr
    shock_event = abs(prev_ret) >= max(6.0, abs(streak_thr) * 1.5)

    if enabled and (down_streak or vol_break or shock_event):
        applied = True
        if prev_ret < 0:
            up -= bonus
            down += bonus
        elif prev_ret > 0 and not down_streak:
            up += max(1, bonus - 1)
            down -= max(1, bonus - 1)
        up, neutral, down = _normalize_probs(up, neutral, down)

    meta = {
        "enabled": enabled,
        "applied": applied,
        "down_streak": down_streak,
        "vol_break": vol_break,
        "shock_event": shock_event,
    }
    return up, neutral, down, meta


def _sasang_external_adjust(
    up: int,
    neutral: int,
    down: int,
    *,
    phase: str,
    prev_ret: float,
    roll_abs_3m: float,
    profile: dict[str, Any],
) -> tuple[int, int, int, dict[str, Any]]:
    """External-reality tilt tuned for sasang stage-like market behavior.

    - Shock regime (|prev_ret| high): mean-reversion tilt
    - Normal regime: momentum-follow tilt
    - Phase bias acts as weak prior (defensive in 압박/방어)
    """
    shock_thr = float(profile.get("shock_abs_return_threshold_pct", 8.0))
    high_vol_thr = float(profile.get("high_vol_threshold_pct", 4.0))
    momentum_window = int(max(1, profile.get("momentum_window", 3)))
    momentum_warn_threshold_pct = float(profile.get("momentum_warn_threshold_pct", 1.0))
    phase_bias = float((profile.get("phase_bias") or {}).get(phase, 0.0))
    use_sj = bool(profile.get("seongjeong_overlay_enabled", False))
    sj_strength = float(profile.get("seongjeong_overlay_strength", 0.0))
    sj_mode = str(profile.get("seongjeong_activation_mode") or "always")
    base_shift = int(profile.get("base_shift_pct", 3))
    max_shift = int(profile.get("max_shift_pct", 12))

    prev_sign = 1.0 if prev_ret > 0 else (-1.0 if prev_ret < 0 else 0.0)
    shock_mode = abs(prev_ret) >= shock_thr
    high_vol_mode = roll_abs_3m >= high_vol_thr
    momentum_mode = False
    if momentum_window > 0:
        momentum_signal_pct = abs(prev_ret)
        momentum_mode = momentum_signal_pct >= momentum_warn_threshold_pct
    trend_component = (-prev_sign if shock_mode else prev_sign) * _clip(abs(prev_ret) / 15.0, 0.0, 1.0)
    vol_component = _clip((roll_abs_3m - 3.0) / 6.0, -1.0, 1.0) * 0.3
    # Seongjeong proxy (애/노/락/희): emotion-led market posture from observable market action.
    # 애(sadness): drawdown grief; 노(anger): high-vol shock response;
    # 락(stability joy): low-vol calm; 희(euphoria): sustained upside.
    ae = _clip(max(0.0, -prev_ret) / 15.0 + _clip((roll_abs_3m - 5.0) / 8.0, 0.0, 1.0) * 0.5, 0.0, 1.0)
    no = _clip(abs(prev_ret) / 12.0 + _clip((roll_abs_3m - 4.0) / 7.0, 0.0, 1.0) * 0.6, 0.0, 1.0)
    rak = _clip(1.0 - _clip(roll_abs_3m / 8.0, 0.0, 1.0), 0.0, 1.0)
    hee = _clip(max(0.0, prev_ret) / 15.0 + _clip((3.0 - roll_abs_3m) / 6.0, 0.0, 1.0) * 0.4, 0.0, 1.0)
    sj_net = _clip((hee + rak) - (ae + no), -1.0, 1.0)
    sj_active = False
    if use_sj:
        if sj_mode == "always":
            sj_active = True
        elif sj_mode == "shock":
            sj_active = shock_mode
        elif sj_mode == "high_vol":
            sj_active = high_vol_mode
        elif sj_mode == "shock_or_high_vol":
            sj_active = shock_mode or high_vol_mode
        elif sj_mode == "shock_or_high_vol_or_momentum":
            sj_active = shock_mode or high_vol_mode or momentum_mode
        else:
            sj_active = True
    sj_term = sj_strength * sj_net if sj_active else 0.0

    tilt = _clip(trend_component - vol_component + phase_bias + sj_term, -1.0, 1.0)

    shift = int(round(base_shift + min(max_shift - base_shift, abs(tilt) * max_shift)))
    if tilt > 0:
        up += shift
        down -= shift
    elif tilt < 0:
        up -= shift
        down += shift
    up, neutral, down = _normalize_probs(up, neutral, down)
    meta = {
        "prev_ret_pct": round(prev_ret, 6),
        "roll_abs_3m_pct": round(roll_abs_3m, 6),
        "shock_mode": shock_mode,
        "high_vol_mode": high_vol_mode,
        "momentum_mode": momentum_mode,
        "momentum_warn_threshold_pct": momentum_warn_threshold_pct,
        "tilt": round(tilt, 6),
        "shift_pct": shift,
        "seongjeong": {
            "ae": round(ae, 6),
            "no": round(no, 6),
            "rak": round(rak, 6),
            "hee": round(hee, 6),
            "net": round(sj_net, 6),
            "enabled": use_sj,
            "activation_mode": sj_mode,
            "active": sj_active,
            "term": round(sj_term, 6),
        },
    }
    return up, neutral, down, meta


def _scoring_rule() -> dict[str, Any]:
    return dict(SCORING_RULE)


def generate(
    *,
    seongjeong_overlay_enabled: bool | None = None,
    seongjeong_overlay_strength: float | None = None,
    seongjeong_activation_mode: str | None = None,
    shock_abs_return_threshold_pct: float | None = None,
    high_vol_threshold_pct: float | None = None,
    momentum_warn_threshold_pct: float | None = None,
    momentum_window: int | None = None,
    high_vol_neutral_guard_enabled: bool | None = None,
    multi_event_prior_enabled: bool | None = None,
) -> dict[str, Any]:
    gate = _safe_json(GATE_JSON)
    waiting = _latest_jsonl(WAITING_LOG)
    sweep = _safe_json(BTC_SWEEP)
    k_shield_sweep = _safe_json(K_SHIELD_SWEEP)

    engine_id = "V2_Precision_MCP"
    samples_7d, net_delta_7d = _kpi_history_stats(days=7)
    reliability_badge = _compute_badge(engine_id=engine_id, samples=samples_7d, net_delta=net_delta_7d)
    gate_decision = str(gate.get("decision") or "").upper()
    base_effective_gate = "HOLD" if reliability_badge == "LOW" else (gate_decision if gate_decision in {"PASS", "HOLD"} else "PASS")
    base_gate_reason = "low_badge_forced_hold" if reliability_badge == "LOW" else "monthly_check_gate"
    best = sweep.get("best") if isinstance(sweep.get("best"), dict) else {}
    best_metrics = best.get("metrics") if isinstance(best.get("metrics"), dict) else {}
    k_shield_best = (
        k_shield_sweep.get("best_by_balanced_score")
        if isinstance(k_shield_sweep.get("best_by_balanced_score"), dict)
        else {}
    )
    k_shield_best_name = k_shield_best.get("name") if isinstance(k_shield_best, dict) else None
    k_shield_best_metrics = k_shield_best.get("metrics") if isinstance(k_shield_best.get("metrics"), dict) else {}
    btc_backtest_bias = "NEUTRAL"
    if float(best_metrics.get("net_return_pct") or 0.0) > 0 and float(best_metrics.get("profit_factor") or 0.0) >= 1.0:
        btc_backtest_bias = "CAUTION_UP"

    month_now = datetime.now(timezone.utc).month
    year_now = datetime.now(timezone.utc).year
    phase_now = _month_phase(month_now)
    s_val = _sasang_response_score(phase_now)
    l_val = _logos_regime_score(year=year_now, month=month_now)
    k_val = _myeongri_timing_score(phase_now)
    m_val = _mechanism_score(best_metrics=best_metrics, net_delta_7d=net_delta_7d)
    core = compute_core_score(CoreInput(s=s_val, l=l_val, k=k_val, m=m_val))
    core_decision = str(core.get("decision") or "HOLD")
    effective_gate, merged_gate_reason = _merge_gate_decision(base_effective_gate, core_decision)
    gate_reason = f"{base_gate_reason}|{merged_gate_reason}"
    hold_mode = effective_gate.upper() == "HOLD" or reliability_badge.upper() == "LOW"
    market_momentum = _recent_market_momentum(KOSPI_CSV, lookback=3)
    momentum_score = float(market_momentum["score"])
    ext_profile = _sasang_external_profile()
    if seongjeong_overlay_enabled is not None:
        ext_profile["seongjeong_overlay_enabled"] = bool(seongjeong_overlay_enabled)
    if seongjeong_overlay_strength is not None:
        ext_profile["seongjeong_overlay_strength"] = float(max(0.0, min(1.0, seongjeong_overlay_strength)))
    if seongjeong_activation_mode:
        ext_profile["seongjeong_activation_mode"] = str(seongjeong_activation_mode)
    if shock_abs_return_threshold_pct is not None:
        ext_profile["shock_abs_return_threshold_pct"] = float(max(0.1, shock_abs_return_threshold_pct))
    if high_vol_threshold_pct is not None:
        ext_profile["high_vol_threshold_pct"] = float(max(0.1, high_vol_threshold_pct))
    if momentum_warn_threshold_pct is not None:
        ext_profile["momentum_warn_threshold_pct"] = float(max(0.01, momentum_warn_threshold_pct))
    if momentum_window is not None:
        ext_profile["momentum_window"] = int(max(1, momentum_window))
    if high_vol_neutral_guard_enabled is not None:
        ext_profile["high_vol_neutral_guard_enabled"] = bool(high_vol_neutral_guard_enabled)
    if multi_event_prior_enabled is not None:
        ext_profile["multi_event_prior_enabled"] = bool(multi_event_prior_enabled)
    monthly_hist = _monthly_returns_from_csv(KOSPI_CSV)
    monthly_ret_map = {f"{int(r['year'])}-{int(r['month']):02d}": float(r["return_pct"]) for r in monthly_hist}
    price_output_locked = hold_mode
    lock_reason = "low_or_hold_mode_price_output_forbidden" if price_output_locked else "price_output_allowed"
    months: list[dict[str, Any]] = []
    sim_ret_map: dict[str, float] = {}
    asof_year = 2026
    for month in range(1, 13):
        phase = _month_phase(month)
        up, neutral, down = _base_probs(phase)
        # Build causal monthly context: prefer observed previous months, then fallback to simulated path.
        prev_vals: list[float] = []
        for pm in range(max(1, month - 3), month):
            pym = f"{asof_year}-{pm:02d}"
            if pym in monthly_ret_map:
                prev_vals.append(float(monthly_ret_map[pym]))
            elif pym in sim_ret_map:
                prev_vals.append(float(sim_ret_map[pym]))
        prev_ret = prev_vals[-1] if prev_vals else 0.0
        roll_abs_3m = (sum(abs(v) for v in prev_vals) / len(prev_vals)) if prev_vals else 2.0

        up, neutral, down = _adjust_for_hold(up, neutral, down, hold_mode, momentum_score=momentum_score)
        up, neutral, down, sasang_meta = _sasang_external_adjust(
            up,
            neutral,
            down,
            phase=phase,
            prev_ret=prev_ret,
            roll_abs_3m=roll_abs_3m,
            profile=ext_profile,
        )
        up, neutral, down, hv_guard_meta = _apply_high_vol_guard(
            up,
            neutral,
            down,
            prev_ret=prev_ret,
            roll_abs_3m=roll_abs_3m,
            profile=ext_profile,
        )
        up, neutral, down, me_prior_meta = _apply_multi_event_prior(
            up,
            neutral,
            down,
            prev_vals=prev_vals,
            prev_ret=prev_ret,
            roll_abs_3m=roll_abs_3m,
            profile=ext_profile,
        )
        up, neutral, down = _apply_market_momentum_overlay(
            up,
            neutral,
            down,
            phase=phase,
            momentum_score=momentum_score,
        )
        kospi_direction = "중립"
        if up > down:
            kospi_direction = "완만상방"
        elif down > up:
            kospi_direction = "방어하방"

        btc_up = up + (3 if btc_backtest_bias == "CAUTION_UP" else 0)
        btc_down = down - (3 if btc_backtest_bias == "CAUTION_UP" else 0)
        btc_neutral = 100 - btc_up - btc_down
        if hold_mode:
            # Keep defensive framing under HOLD.
            if momentum_score >= 0.62:
                btc_up = max(10, btc_up - 1)
                btc_down = min(75, btc_down + 1)
            else:
                btc_up = max(10, btc_up - 4)
                btc_down = min(75, btc_down + 4)
            btc_neutral = 100 - btc_up - btc_down
        btc_direction = "중립"
        if btc_up > btc_down:
            btc_direction = "완만상방"
        elif btc_down > btc_up:
            btc_direction = "방어하방"

        # Simulated return for future months when observed monthly close isn't available yet.
        ym = f"{asof_year}-{month:02d}"
        if ym not in monthly_ret_map:
            sim_ret = 0.0
            if kospi_direction == "완만상방":
                sim_ret = 2.0
            elif kospi_direction == "방어하방":
                sim_ret = -2.0
            sim_ret_map[ym] = sim_ret

        months.append(
            {
                "month": month,
                "phase": phase,
                "kospi": {
                    "up_pct": up,
                    "neutral_pct": neutral,
                    "down_pct": down,
                    "direction": kospi_direction,
                },
                "btc": {
                    "up_pct": btc_up,
                    "neutral_pct": btc_neutral,
                    "down_pct": btc_down,
                    "direction": btc_direction,
                },
                "note": "확정 예언이 아닌 확률 시나리오. HOLD 모드에서는 방어 가중치 적용.",
                "sasang_external_context": {
                    **sasang_meta,
                    "high_vol_guard": hv_guard_meta,
                    "multi_event_prior": me_prior_meta,
                },
            }
        )
    risk_profile_now = _build_risk_profile(
        phase=phase_now,
        hold_mode=hold_mode,
        year=year_now,
        month=month_now,
    )
    risk_profile_now["core_score"] = core.get("score_grid")
    risk_profile_now["core_decision"] = core_decision
    risk_profile_now["core_reason"] = core.get("reason")
    risk_profile_now["core_contract_version"] = core.get("contract_version")

    scoring_rule = _scoring_rule()
    return {
        "schema": "prophecy_2026_monthly_kospi_btc_fact_safe_v1",
        "generated_at_utc": _z_now(),
        "meta": {
            "engine_id": engine_id,
            "engine_scope": "monthly_prophecy_generation_only",
            "boundary_rule": "observatory_ephemeris_v1",
            "myeongri_verification_engine": "project-0-workspace-athena-manseryeok.verify_saju_date",
            "calendar_source_type": "external_standard_required",
            "calendar_source_name": "standard_rabbinic_calendar",
            "reliability_badge": reliability_badge,
            "high_reliability_decision": effective_gate,
            "gate_reason": gate_reason,
            "base_gate_reason": base_gate_reason,
            "price_output_locked": price_output_locked,
            "lock_reason": lock_reason,
            "raw_high_reliability_gate": gate.get("decision"),
            "samples_7d": samples_7d,
            "net_delta_7d": round(net_delta_7d, 8),
            "overlap_drift_alert": waiting.get("overlap_drift_alert"),
            "btc_backtest_best_period": best.get("period"),
            "btc_backtest_best_net_return_pct": best_metrics.get("net_return_pct"),
            "btc_backtest_best_profit_factor": best_metrics.get("profit_factor"),
            "k_shield_candidate_name": k_shield_best_name,
            "k_shield_candidate_net_return_pct": k_shield_best_metrics.get("net_return_pct"),
            "k_shield_candidate_profit_factor": k_shield_best_metrics.get("profit_factor"),
            "k_shield_candidate_max_drawdown_pct": k_shield_best_metrics.get("max_drawdown_pct"),
            "core_score": core.get("score_grid"),
            "core_score_raw": core.get("score_raw"),
            "core_decision": core_decision,
            "core_reason": core.get("reason"),
            "core_contract_version": core.get("contract_version"),
            "scoring_rule": scoring_rule,
            "hypothesis_target_metric": scoring_rule["target_metric"],
            "hypothesis_target_condition": scoring_rule["target_condition"],
            "hypothesis_falsification_condition": scoring_rule["falsification_condition"],
            "observed_lever_priority": OBSERVED_LEVER_PRIORITY,
            "decision_driver_policy": "prefer_observed_lever_over_symbolic_lens",
            "recent_market_momentum": market_momentum,
            "sasang_external_profile": ext_profile,
        },
        "risk_profile": risk_profile_now,
        "months": months,
    }


def to_markdown(doc: dict[str, Any]) -> str:
    meta = doc.get("meta", {})
    lines = [
        "# 2026 Monthly KOSPI/BTC Fact-Safe Prophecy V1",
        "",
        "## 3문장 요약",
        "1) 본 문서는 확정 예언이 아닌 월별 확률 시나리오다.",
        f"2) 현재 신뢰도 배지/게이트는 {meta.get('reliability_badge')} / {meta.get('high_reliability_decision')}다.",
        "3) HOLD 모드에서는 방어 가중치가 자동 적용된다.",
        "",
        "## 메타 고정",
        f"- generated_at_utc: {doc.get('generated_at_utc')}",
        f"- engine_id: {meta.get('engine_id')}",
        f"- engine_scope: {meta.get('engine_scope')}",
        f"- boundary_rule: {meta.get('boundary_rule')}",
        f"- myeongri_verification_engine: {meta.get('myeongri_verification_engine')}",
        f"- calendar_source_type: {meta.get('calendar_source_type')}",
        f"- calendar_source_name: {meta.get('calendar_source_name')}",
        f"- reliability_badge: {meta.get('reliability_badge')}",
        f"- high_reliability_decision: {meta.get('high_reliability_decision')}",
        f"- gate_reason: {meta.get('gate_reason')}",
        f"- price_output_locked: {meta.get('price_output_locked')}",
        f"- lock_reason: {meta.get('lock_reason')}",
        f"- btc_backtest_best_period: {meta.get('btc_backtest_best_period')}",
        f"- k_shield_candidate_name: {meta.get('k_shield_candidate_name')}",
        f"- k_shield_candidate_net_return_pct: {meta.get('k_shield_candidate_net_return_pct')}",
        f"- k_shield_candidate_max_drawdown_pct: {meta.get('k_shield_candidate_max_drawdown_pct')}",
        f"- core_score: {meta.get('core_score')}",
        f"- core_decision: {meta.get('core_decision')}",
        f"- core_reason: {meta.get('core_reason')}",
        f"- hypothesis_target_condition: {meta.get('hypothesis_target_condition')}",
        f"- hypothesis_falsification_condition: {meta.get('hypothesis_falsification_condition')}",
        f"- observed_lever_priority: {meta.get('observed_lever_priority')}",
        "",
        "## 채점 규칙 (HIT/FAIL/NEUTRAL_DRAW)",
        f"- target_metric: {meta.get('scoring_rule', {}).get('target_metric')}",
        f"- HIT: return_pct <= {meta.get('scoring_rule', {}).get('hit_threshold_pct')}",
        f"- FAIL: return_pct >= {meta.get('scoring_rule', {}).get('fail_threshold_pct')}",
        "- NEUTRAL_DRAW: HIT/FAIL 사이 구간(승패 미반영)",
        "",
        "## Risk Profile (Trinity Governor)",
        f"- mode: {doc.get('risk_profile', {}).get('mode')}",
        f"- logos_regime_score: {doc.get('risk_profile', {}).get('logos_regime_score')}",
        f"- myeongri_timing_score: {doc.get('risk_profile', {}).get('myeongri_timing_score')}",
        f"- sasang_response_score: {doc.get('risk_profile', {}).get('sasang_response_score')}",
        f"- fused_risk_pressure: {doc.get('risk_profile', {}).get('fused_risk_pressure')}",
        f"- position_scale_cap: {doc.get('risk_profile', {}).get('position_scale_cap')}",
        f"- daily_loss_cap_pct: {doc.get('risk_profile', {}).get('daily_loss_cap_pct')}",
        "",
        "## 월별 시나리오",
    ]
    for row in doc.get("months", []):
        k = row["kospi"]
        b = row["btc"]
        lines.extend(
            [
                f"- {row['month']}월 ({row['phase']}) | "
                f"KOSPI: {k['direction']} (상/중/하={k['up_pct']}/{k['neutral_pct']}/{k['down_pct']}) | "
                f"BTC: {b['direction']} (상/중/하={b['up_pct']}/{b['neutral_pct']}/{b['down_pct']})",
            ]
        )
    lines.extend(
        [
            "",
            "## 면책",
            "- 본 문서는 투자/법률/의료의 확정 판단 근거가 아니며, Fact-Safe 계약에 따른 확률형 보조 자료다.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=OUT_JSON)
    ap.add_argument("--out-md", type=Path, default=OUT_MD)
    ap.add_argument("--seongjeong-overlay", choices=("auto", "on", "off"), default="auto")
    ap.add_argument("--seongjeong-strength", type=float, default=None)
    ap.add_argument(
        "--seongjeong-activation-mode",
        choices=("always", "shock", "high_vol", "shock_or_high_vol", "shock_or_high_vol_or_momentum"),
        default=None,
    )
    ap.add_argument("--shock-abs-return-threshold-pct", type=float, default=None)
    ap.add_argument("--high-vol-threshold-pct", type=float, default=None)
    ap.add_argument("--momentum-warn-threshold-pct", type=float, default=None)
    ap.add_argument("--momentum-window", type=int, default=None)
    ap.add_argument("--high-vol-neutral-guard", choices=("auto", "on", "off"), default="auto")
    ap.add_argument("--multi-event-prior", choices=("auto", "on", "off"), default="auto")
    args = ap.parse_args()

    sj_enabled: bool | None
    if args.seongjeong_overlay == "on":
        sj_enabled = True
    elif args.seongjeong_overlay == "off":
        sj_enabled = False
    else:
        sj_enabled = None

    hv_guard: bool | None
    if args.high_vol_neutral_guard == "on":
        hv_guard = True
    elif args.high_vol_neutral_guard == "off":
        hv_guard = False
    else:
        hv_guard = None

    me_prior: bool | None
    if args.multi_event_prior == "on":
        me_prior = True
    elif args.multi_event_prior == "off":
        me_prior = False
    else:
        me_prior = None

    doc = generate(
        seongjeong_overlay_enabled=sj_enabled,
        seongjeong_overlay_strength=args.seongjeong_strength,
        seongjeong_activation_mode=args.seongjeong_activation_mode,
        shock_abs_return_threshold_pct=args.shock_abs_return_threshold_pct,
        high_vol_threshold_pct=args.high_vol_threshold_pct,
        momentum_warn_threshold_pct=args.momentum_warn_threshold_pct,
        momentum_window=args.momentum_window,
        high_vol_neutral_guard_enabled=hv_guard,
        multi_event_prior_enabled=me_prior,
    )
    ART_DIR.mkdir(parents=True, exist_ok=True)
    out_json = args.out_json if args.out_json.is_absolute() else ROOT / args.out_json
    out_md = args.out_md if args.out_md.is_absolute() else ROOT / args.out_md
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out_md.write_text(to_markdown(doc), encoding="utf-8")
    print(str(out_json))
    print(str(out_md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
