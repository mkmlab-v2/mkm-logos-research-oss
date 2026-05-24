#!/usr/bin/env python3
"""[FACT] Read-only triage: live PnL/health vs prophecy gates — no orders, no auto-promote."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/live_vs_prophecy_triage_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _num(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _trade_24h_stats(path: Path) -> dict[str, Any]:
    doc = _load(path)
    rows = list(doc.get("treatment") or []) + list(doc.get("control") or [])
    realized = commission = 0.0
    for r in rows:
        realized += _num(r.get("realized_pnl"))
        commission += _num(r.get("commission"))
    net = realized - commission
    return {
        "trade_count": len(rows),
        "realized_pnl_sum": round(realized, 6),
        "commission_sum": round(commission, 6),
        "net_pnl_usdt": round(net, 6),
        "window_end_utc": doc.get("window_end_utc"),
        "treatment_id": doc.get("treatment_id"),
    }


def _classify(
    *,
    net_pnl: float,
    trade_count: int,
    health_red: bool,
    gate_conflict: bool,
    go_no_go: str,
    frozen_kpi: float | None,
    shadow_hybrid: float | None,
) -> tuple[str, str, list[str]]:
    actions: list[str] = []
    if gate_conflict or health_red:
        actions.append("mode_b: resolve GATE_LIVE_CONFLICT before scaling live or prophecy-routed orders")
        actions.append("do_not: swap live to prophecy-only without human sign-off")
    if trade_count >= 10 and net_pnl < -5:
        primary = "pnl_execution"
        posture = "fix_live_ops_first"
        actions.append("review: sizing, fees, overtrading (24h trade_count high)")
    elif gate_conflict:
        primary = "gate_boundary"
        posture = "shadow_prophecy_only"
    elif trade_count == 0:
        primary = "execution_stale"
        posture = "refresh_live_health_then_decide"
        actions.append("run: projects/bitcoin-trading/ops/windows-rehearsal/check_live_trading_health.ps1")
    elif frozen_kpi is not None and shadow_hybrid is not None and shadow_hybrid - frozen_kpi >= 0.15:
        primary = "direction_layer_research"
        posture = "shadow_prophecy_only"
        actions.append("keep: frozen KPI-A headline; log BBS+MS hybrid as shadow lane only")
    else:
        primary = "mixed_or_unclear"
        posture = "shadow_prophecy_only"
    if go_no_go != "GO":
        actions.append("trading_go_no_go not GO — disk readiness failed; no live scale-up")
    return primary, posture, actions


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    trade_path = ROOT / "projects/bitcoin-trading/exports/cursor_trade_history/cursor_trade_history_latest_24h.json"
    go = _load(ROOT / "docs/final/artifacts/trading_go_no_go_latest.json")
    health = _load(ROOT / "docs/final/artifacts/prophecy_runtime_health_guard_latest.json")
    gates_rec = _load(ROOT / "reports/prophecy_promotion_gates_recommended_chain_v1_latest.json")
    gates_art = _load(ROOT / "docs/final/artifacts/prophecy_promotion_gates_v1_latest.json")
    frozen_eval = _load(ROOT / "reports/prophecy_hit_rate_eval_30d_frozen_kpi_a_v1.json")
    shadow = _load(ROOT / "reports/btrack_bbs_ms_hybrid_shadow_lane_v1_latest.json")
    live_health_path = ROOT / "projects/bitcoin-trading/memory/v2/ops/live_trading_health_latest.json"
    live_health = _load(live_health_path)
    risk = _load(ROOT / "projects/bitcoin-trading/memory/v2/risk/risk_profile_fact_safe_latest.json")

    trade_stats = _trade_24h_stats(trade_path)
    findings = list(health.get("findings") or [])
    gate_conflict = any(
        isinstance(f, dict) and f.get("code") == "GATE_LIVE_CONFLICT" for f in findings
    )
    health_red = str(health.get("status") or "").lower() == "red"

    frozen_kpi = None
    if frozen_eval:
        metrics = frozen_eval.get("metrics") or {}
        pd = frozen_eval.get("price_directional") or {}
        frozen_kpi = _num(
            metrics.get("price_directional_hit_rate")
            or pd.get("hit_rate")
            or pd.get("price_directional_hit_rate")
            or frozen_eval.get("price_directional_hit_rate")
        )
    shadow_rate = _num((shadow.get("metrics") or {}).get("frozen_30d_all_rows")) or None

    primary, posture, actions = _classify(
        net_pnl=_num(trade_stats.get("net_pnl_usdt")),
        trade_count=int(trade_stats.get("trade_count") or 0),
        health_red=health_red,
        gate_conflict=gate_conflict,
        go_no_go=str(go.get("go_no_go") or "UNKNOWN"),
        frozen_kpi=frozen_kpi if frozen_kpi else None,
        shadow_hybrid=shadow_rate,
    )

    report = {
        "schema": "live_vs_prophecy_triage_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[FACT]",
        "verdict_one_liner": (
            "Do not swap live to prophecy-only; fix gate conflict and treat prophecy as shadow."
            if gate_conflict
            else "Prophecy shadow OK; live issues need separate ops review."
        ),
        "primary_axis": primary,
        "recommended_posture": posture,
        "recommended_actions": actions,
        "live_24h": trade_stats,
        "live_health_snapshot": {
            "path": "projects/bitcoin-trading/memory/v2/ops/live_trading_health_latest.json",
            "ts_local": live_health.get("ts_local"),
            "daemon_running": live_health.get("daemon_running"),
            "trading_enabled": live_health.get("trading_enabled"),
            "exchange_fills_24h": live_health.get("exchange_fills_24h"),
            "exchange_net_24h": live_health.get("exchange_net_24h"),
            "stale_warning": bool(
                live_health.get("ts_local")
                and str(live_health.get("ts_local", ""))[:10] < _utc()[:10]
                and _num(live_health.get("exchange_fills_24h")) == 0
                and int(trade_stats.get("trade_count") or 0) > 0
            ),
        },
        "risk": {
            "mode": risk.get("mode"),
            "final_action_allowed": (risk.get("governance_bridge") or {}).get("final_action_allowed"),
            "final_regime": (risk.get("governance_bridge") or {}).get("final_regime"),
        },
        "trading_go_no_go": {
            "go_no_go": go.get("go_no_go"),
            "gate_ok": go.get("gate_ok"),
            "risk_mode": go.get("risk_mode"),
            "note": go.get("notes"),
        },
        "prophecy_runtime_health": {
            "status": health.get("status"),
            "should_pause_trading": health.get("should_pause_trading"),
            "gate_live_conflict": gate_conflict,
            "findings": [f.get("code") for f in findings if isinstance(f, dict)],
        },
        "prophecy_gates": {
            "artifacts_combined_all_passed": gates_art.get("combined_all_passed"),
            "recommended_chain_combined_all_passed": gates_rec.get("combined_all_passed"),
            "auto_promote_ready_artifacts": gates_art.get("auto_promote_ready"),
        },
        "prophecy_research_headlines": {
            "frozen_kpi_a_30d": frozen_kpi,
            "bbs_ms_hybrid_shadow_30d": shadow_rate,
            "shadow_lane": "reports/btrack_bbs_ms_hybrid_shadow_lane_v1_latest.json",
            "do_not_replace_headline": True,
        },
        "constraints": [
            "B-track / 90d freeze: no prophecy→live auto-promotion",
            "trading_go_no_go GO does not place orders",
            "prophecy swap does not fix execution/risk if primary_axis is pnl_execution",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    print(f"primary_axis={primary} posture={posture}")
    print(f"verdict: {report['verdict_one_liner']}")
    for line in actions[:5]:
        print(f"  - {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
