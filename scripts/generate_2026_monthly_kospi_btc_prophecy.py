# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.8, K:0.4, M:0.6}
# Balance: 90
# Purpose: Generate 2026 monthly KOSPI/BTC fact-safe prophecy draft.
# Keywords: kospi, btc, monthly, prophecy, fact-safe
"""Generate 2026 monthly KOSPI/BTC fact-safe scenario report."""

from __future__ import annotations

import json
from datetime import datetime, timezone
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


def _adjust_for_hold(up: int, neutral: int, down: int, hold_mode: bool) -> tuple[int, int, int]:
    if not hold_mode:
        return up, neutral, down
    # Conservative shift while preserving total 100.
    up2 = max(10, up - 4)
    down2 = min(70, down + 4)
    return up2, neutral, down2


def generate() -> dict[str, Any]:
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
    price_output_locked = hold_mode
    lock_reason = "low_or_hold_mode_price_output_forbidden" if price_output_locked else "price_output_allowed"
    months: list[dict[str, Any]] = []
    for month in range(1, 13):
        phase = _month_phase(month)
        up, neutral, down = _base_probs(phase)
        up, neutral, down = _adjust_for_hold(up, neutral, down, hold_mode)
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
            btc_up = max(10, btc_up - 4)
            btc_down = min(75, btc_down + 4)
            btc_neutral = 100 - btc_up - btc_down
        btc_direction = "중립"
        if btc_up > btc_down:
            btc_direction = "완만상방"
        elif btc_down > btc_up:
            btc_direction = "방어하방"

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

    return {
        "schema": "prophecy_2026_monthly_kospi_btc_fact_safe_v1",
        "generated_at_utc": _z_now(),
        "meta": {
            "engine_id": engine_id,
            "boundary_rule": "observatory_ephemeris_v1",
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
        f"- boundary_rule: {meta.get('boundary_rule')}",
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
    doc = generate()
    ART_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_MD.write_text(to_markdown(doc), encoding="utf-8")
    print(str(OUT_JSON))
    print(str(OUT_MD))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
