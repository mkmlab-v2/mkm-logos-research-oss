# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.8, K:0.5, M:0.6}
# Balance: 91
# Purpose: Build Fact-Safe multi-lens brief from runtime artifacts.
# Keywords: multilens, template, reliability, gate, report
"""Build Fact-Safe multi-lens brief markdown from local runtime artifacts."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "docs" / "final" / "artifacts" / "fact_safe_multilens_brief_latest.md"
DEFAULT_STATUS = ROOT / "projects" / "bitcoin-trading" / "memory" / "trading_daemon_status.json"
DEFAULT_KPI_JSONL = ROOT / "projects" / "bitcoin-trading" / "memory" / "kpi" / "kpi_snapshot_*.jsonl"
DEFAULT_WAITING_LOG = ROOT / "docs" / "final" / "artifacts" / "waiting_queue_monthly_check_log.jsonl"
DEFAULT_BT_BACKTEST = ROOT / "docs" / "final" / "artifacts" / "btc_time_machine_fact_safe_backtest_latest.json"


@dataclass(frozen=True)
class ReliabilityDecision:
    badge: str
    decision: str


@dataclass(frozen=True)
class GateDecision:
    decision: str
    reason: str


def compute_reliability_badge(engine_id: str, samples: int, net_delta: float) -> ReliabilityDecision:
    if engine_id == "V1_Approx_Stub" or samples < 10:
        return ReliabilityDecision(badge="LOW", decision="HOLD")
    if engine_id == "V2_Precision_MCP" and 10 <= samples <= 49:
        return ReliabilityDecision(badge="MID", decision="PASS")
    if engine_id == "V2_Precision_MCP" and samples >= 50 and net_delta > 0:
        return ReliabilityDecision(badge="HIGH", decision="PASS")
    return ReliabilityDecision(badge="MID", decision="PASS")


def _safe_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _tail_jsonl(path: Path, limit: int = 288) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows[-limit:]


def _latest_kpi_jsonl() -> Path | None:
    paths = sorted(ROOT.glob(str(DEFAULT_KPI_JSONL.relative_to(ROOT))), reverse=True)
    return paths[0] if paths else None


def _latest_waiting_log() -> dict[str, Any]:
    if not DEFAULT_WAITING_LOG.exists():
        return {}
    lines = [x for x in DEFAULT_WAITING_LOG.read_text(encoding="utf-8", errors="ignore").splitlines() if x.strip()]
    if not lines:
        return {}
    try:
        doc = json.loads(lines[-1])
        return doc if isinstance(doc, dict) else {}
    except Exception:
        return {}


def _collect_recent_kpi_rows(days: int = 7, max_points: int = 3000) -> list[dict[str, Any]]:
    paths = sorted(ROOT.glob(str(DEFAULT_KPI_JSONL.relative_to(ROOT))), reverse=True)
    if not paths:
        return []
    cutoff = datetime.now(timezone.utc).timestamp() - days * 24 * 60 * 60
    rows: list[dict[str, Any]] = []
    for path in paths:
        if len(rows) >= max_points:
            break
        for row in reversed(_tail_jsonl(path, limit=2000)):
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
            if len(rows) >= max_points:
                break
    rows.reverse()
    return rows


def _kpi_history_stats(days: int = 7) -> tuple[int, float, float | None]:
    rows = _collect_recent_kpi_rows(days=days)
    net_series: list[float] = []
    fills_series: list[float] = []
    for row in rows:
        net = row.get("exchange_snapshot_24h_net")
        fills = row.get("exchange_snapshot_24h_fills_count")
        if isinstance(net, (int, float)):
            net_series.append(float(net))
        if isinstance(fills, (int, float)):
            fills_series.append(float(fills))
    if not net_series:
        return len(rows), 0.0, None
    net_delta = net_series[-1] - net_series[0]
    avg_net_per_fill = None
    if fills_series and fills_series[-1] > 0:
        avg_net_per_fill = net_series[-1] / fills_series[-1]
    return len(rows), net_delta, avg_net_per_fill


def resolve_gate_decision(reliability: ReliabilityDecision, high_reliability_from_ops: str) -> GateDecision:
    # Reliability LOW is always HOLD by contract.
    if reliability.badge == "LOW":
        return GateDecision(decision="HOLD", reason="low_badge_forced_hold")
    if high_reliability_from_ops in {"PASS", "HOLD"}:
        return GateDecision(decision=high_reliability_from_ops, reason="monthly_check_gate")
    return GateDecision(decision=reliability.decision, reason="badge_policy_default")


def _load_backtest_evidence() -> dict[str, Any]:
    if not DEFAULT_BT_BACKTEST.exists():
        return {}
    try:
        doc = json.loads(DEFAULT_BT_BACKTEST.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(doc, dict):
        return {}
    metrics = doc.get("metrics")
    if not isinstance(metrics, dict):
        return {}
    return {
        "available": True,
        "path": str(DEFAULT_BT_BACKTEST),
        "sample_count": metrics.get("sample_count"),
        "win_rate": metrics.get("win_rate"),
        "net_return_pct": metrics.get("net_return_pct"),
        "avg_trade_return_pct": metrics.get("avg_trade_return_pct"),
        "profit_factor": metrics.get("profit_factor"),
        "period": f"{doc.get('start')}..{doc.get('end')}",
        "method": doc.get("method"),
    }


def build_report(engine_id: str, boundary_rule: str) -> str:
    status = _safe_json(DEFAULT_STATUS)
    snapshot = status.get("exchange_snapshot_24h") if isinstance(status.get("exchange_snapshot_24h"), dict) else {}
    waiting = _latest_waiting_log()
    backtest = _load_backtest_evidence()

    samples, net_delta, avg_net_per_fill = _kpi_history_stats(days=7)
    reliability = compute_reliability_badge(engine_id=engine_id, samples=samples, net_delta=net_delta)

    high_reliability_from_ops = str(waiting.get("high_reliability_decision") or "").upper()
    gate = resolve_gate_decision(reliability, high_reliability_from_ops)

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    warning = ""
    if engine_id == "V1_Approx_Stub":
        warning = (
            "> [!WARNING]\n"
            "> 수치 불일치 가능성 경고: 절입/경계 규칙 차이로 외부 만세력/서비스와 결과가 다를 수 있습니다.\n\n"
        )

    return (
        "# Fact-Safe Multi-Lens Brief\n\n"
        "## 메타 고정 헤더\n"
        f"- generated_at_utc: {now_utc}\n"
        f"- engine_id: {engine_id}\n"
        f"- boundary_rule: {boundary_rule}\n"
        f"- reliability_badge: {reliability.badge}\n"
        f"- high_reliability_decision: {gate.decision}\n"
        f"- gate_reason: {gate.reason}\n\n"
        f"{warning}"
        "## 제1~4장 사전 예측 근거 (Pre-Execution)\n"
        "- [FACT] 실물 레짐 베이스라인: waiting queue/verified gate/overlap drift 결과를 기준으로 보수 운영.\n"
        "- [HYPO] 명리 시간 역학: 엔진 메타를 공개하고 절입 경계 리스크를 분리 표기.\n"
        "- [HYPO] 로고스 공명: 상징 해석은 결론 근거가 아닌 보조 렌즈로 제한.\n"
        "- [HYPO][NON-MEDICAL] 사상 방어선: 의료/법률/실거래 트리거로 단정 금지.\n\n"
        "## 제5장 사후 실행 성과 (Post-Execution Evidence)\n"
        f"- exchange_snapshot_24h.available: {snapshot.get('available')}\n"
        f"- fills_count: {snapshot.get('fills_count')}\n"
        f"- realized_pnl: {snapshot.get('realized_pnl')}\n"
        f"- commission: {snapshot.get('commission')}\n"
        f"- funding_fee: {snapshot.get('funding_fee')}\n"
        f"- net: {snapshot.get('net')}\n"
        f"- history samples: {samples}\n"
        f"- history net_delta: {round(net_delta, 8)}\n"
        f"- history avg_net_per_fill_latest: {round(avg_net_per_fill, 8) if avg_net_per_fill is not None else None}\n"
        f"- backtest_available: {backtest.get('available', False)}\n"
        f"- backtest_sample_count: {backtest.get('sample_count')}\n"
        f"- backtest_win_rate: {backtest.get('win_rate')}\n"
        f"- backtest_net_return_pct: {backtest.get('net_return_pct')}\n"
        f"- backtest_profit_factor: {backtest.get('profit_factor')}\n\n"
        "## 운영 게이트 결론\n"
        f"- reliability_badge: {reliability.badge}\n"
        f"- high_reliability_decision_raw(monthly_check): {waiting.get('high_reliability_decision_raw')}\n"
        f"- high_reliability_decision_effective: {gate.decision}\n"
        f"- gate_reason: {gate.reason}\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Fact-Safe multi-lens brief markdown.")
    parser.add_argument(
        "--engine-id",
        default="V2_Precision_MCP",
        choices=["V1_Approx_Stub", "V2_Precision_MCP"],
    )
    parser.add_argument("--boundary-rule", default="observatory_ephemeris_v1")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    content = build_report(engine_id=args.engine_id, boundary_rule=args.boundary_rule)
    output_path.write_text(content, encoding="utf-8")
    print(str(output_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
