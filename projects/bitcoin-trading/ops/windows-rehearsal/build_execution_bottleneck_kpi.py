#!/usr/bin/env python3
"""Build execution bottleneck KPI snapshot (10 metrics)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
WS_ROOT = Path(__file__).resolve().parents[4]
KPI_LATEST = ROOT / "memory" / "kpi" / "latest_kpi.json"
DAEMON_STATUS = ROOT / "memory" / "trading_daemon_status.json"
BROADCAST = ROOT / "memory" / "v2" / "briefs" / "fact_safe_multilens_broadcast_latest.json"
OUT = ROOT / "memory" / "v2" / "ops" / "execution_bottleneck_kpi_latest.json"
POLICY = WS_ROOT / "data" / "regimes" / "regime_fusion_policy.json"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def _f(v: Any, d: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return d


def _i(v: Any, d: int = 0) -> int:
    try:
        return int(v)
    except Exception:
        return d


def main() -> int:
    kpi = _read_json(KPI_LATEST)
    status = _read_json(DAEMON_STATUS)
    brief = _read_json(BROADCAST)
    policy = _read_json(POLICY)

    ex = kpi.get("exchange_snapshot_24h") if isinstance(kpi.get("exchange_snapshot_24h"), dict) else {}
    ex_status = status.get("exchange_snapshot_24h") if isinstance(status.get("exchange_snapshot_24h"), dict) else {}
    singular = kpi.get("mkm_singular_core") if isinstance(kpi.get("mkm_singular_core"), dict) else {}
    dual_state = kpi.get("dual_regime_state_kpi") if isinstance(kpi.get("dual_regime_state_kpi"), dict) else {}
    g = policy.get("global") if isinstance(policy.get("global"), dict) else {}
    default_gate = str(g.get("default_gate_profile", "balanced"))
    gate_profiles = g.get("gate_profiles") if isinstance(g.get("gate_profiles"), dict) else {}
    gate_cfg = gate_profiles.get(default_gate, {}) if isinstance(gate_profiles, dict) else {}
    psi = gate_cfg.get("psi_thresholds") if isinstance(gate_cfg.get("psi_thresholds"), dict) else {}

    fills_24h = _i(ex.get("fills_count", ex_status.get("fills_count", 0)))
    realized_24h = _f(ex.get("realized_pnl", ex_status.get("realized_pnl", 0.0)))
    funding_24h = _f(ex.get("funding_fee", ex_status.get("funding_fee", 0.0)))
    total_signals = _i(singular.get("total_signals", 0))
    buy_count = _i(singular.get("buy_count", 0))
    sell_count = _i(singular.get("sell_count", 0))
    actionable_signals = buy_count + sell_count
    signal_to_fill_ratio = (fills_24h / actionable_signals) if actionable_signals > 0 else 0.0
    hold_mode = str(brief.get("core_decision", "")).upper() == "HOLD"
    position_cap = _f(brief.get("risk_position_scale_cap", 0.0))
    pending_close_rate_d10 = _f((brief.get("dual_regime_state_advisory") or {}).get("pending_close_rate_d10"), 0.0)
    lock_contract_ok = bool(brief.get("lock_contract_ok", False))
    state_present = bool(dual_state.get("state_id_present", False))
    state_clamp_rate = _f(brief.get("dual_regime_state_advisory", {}).get("clamp_rate", 0.0))

    snapshot = {
        "schema": "execution_bottleneck_kpi_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "gate_profile": {
            "default": default_gate,
            "warning": _f(psi.get("warning", 0.0)),
            "crisis": _f(psi.get("crisis", 0.0)),
        },
        "kpis": {
            "fills_24h": fills_24h,
            "realized_pnl_24h": round(realized_24h, 6),
            "funding_fee_24h": round(funding_24h, 6),
            "total_signals": total_signals,
            "actionable_signals": actionable_signals,
            "signal_to_fill_ratio": round(signal_to_fill_ratio, 6),
            "hold_mode": hold_mode,
            "risk_position_scale_cap": round(position_cap, 6),
            "state_id_present": state_present,
            "state_clamp_rate": round(state_clamp_rate, 6),
            "lock_contract_ok": lock_contract_ok,
            "pending_close_rate_d10": round(pending_close_rate_d10, 6),
        },
        "bottleneck_flags": {
            "conversion_low": signal_to_fill_ratio < 0.2,
            "hold_locked": hold_mode,
            "position_cap_tight": position_cap <= 0.2,
            "state_missing": not state_present,
            "pending_close_risk": pending_close_rate_d10 > 0.1,
        },
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {OUT}")
    print(
        "conversion={c} hold={h} cap={p}".format(
            c=snapshot["kpis"]["signal_to_fill_ratio"],
            h=snapshot["kpis"]["hold_mode"],
            p=snapshot["kpis"]["risk_position_scale_cap"],
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

