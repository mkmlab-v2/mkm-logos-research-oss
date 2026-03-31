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


ROOT = Path(__file__).resolve().parents[1]
ART_DIR = ROOT / "docs" / "final" / "artifacts"
OUT_JSON = ART_DIR / "prophecy_2026_monthly_kospi_btc_fact_safe_v1.json"
OUT_MD = ART_DIR / "prophecy_2026_monthly_kospi_btc_fact_safe_v1.md"

GATE_JSON = ART_DIR / "high_reliability_mode_gate_latest.json"
WAITING_LOG = ART_DIR / "waiting_queue_monthly_check_log.jsonl"
FACT_SAFE_BRIEF = ART_DIR / "fact_safe_multilens_brief_latest.md"
BTC_SWEEP = ART_DIR / "btc_time_machine_sweep_latest.json"


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


def _extract_brief_value(text: str, key: str) -> str | None:
    needle = f"- {key}: "
    for line in text.splitlines():
        if line.startswith(needle):
            return line[len(needle) :].strip()
    return None


def _month_phase(month: int) -> str:
    if month in (1, 2, 3):
        return "기준선/탐색"
    if month in (4, 5, 6):
        return "압박/방어"
    if month in (7, 8, 9):
        return "재정비/경쟁"
    return "성과 회수/정리"


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
    brief_text = FACT_SAFE_BRIEF.read_text(encoding="utf-8", errors="ignore") if FACT_SAFE_BRIEF.exists() else ""

    reliability_badge = _extract_brief_value(brief_text, "reliability_badge") or "LOW"
    effective_gate = _extract_brief_value(brief_text, "high_reliability_decision") or "HOLD"
    gate_reason = _extract_brief_value(brief_text, "gate_reason") or "unknown"
    hold_mode = effective_gate.upper() == "HOLD" or reliability_badge.upper() == "LOW"

    best = sweep.get("best") if isinstance(sweep.get("best"), dict) else {}
    best_metrics = best.get("metrics") if isinstance(best.get("metrics"), dict) else {}
    btc_backtest_bias = "NEUTRAL"
    if float(best_metrics.get("net_return_pct") or 0.0) > 0 and float(best_metrics.get("profit_factor") or 0.0) >= 1.0:
        btc_backtest_bias = "CAUTION_UP"

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

    return {
        "schema": "prophecy_2026_monthly_kospi_btc_fact_safe_v1",
        "generated_at_utc": _z_now(),
        "meta": {
            "engine_id": "V2_Precision_MCP",
            "boundary_rule": "observatory_ephemeris_v1",
            "reliability_badge": reliability_badge,
            "high_reliability_decision": effective_gate,
            "gate_reason": gate_reason,
            "raw_high_reliability_gate": gate.get("decision"),
            "overlap_drift_alert": waiting.get("overlap_drift_alert"),
            "btc_backtest_best_period": best.get("period"),
            "btc_backtest_best_net_return_pct": best_metrics.get("net_return_pct"),
            "btc_backtest_best_profit_factor": best_metrics.get("profit_factor"),
        },
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
        f"- btc_backtest_best_period: {meta.get('btc_backtest_best_period')}",
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
