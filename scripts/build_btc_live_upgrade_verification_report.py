#!/usr/bin/env python3
"""Build BTC live-upgrade verification report from local artifacts/logs.

Observation + readiness report only. No trading side effects.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "btc_live_upgrade_verification_latest.json"
DEFAULT_SITREP = ROOT / "docs" / "final" / "artifacts" / "btc_live_upgrade_verification_latest.md"
LATEST_KPI = ROOT / "projects" / "bitcoin-trading" / "memory" / "kpi" / "latest_kpi.json"
RISK_PROFILE = ROOT / "projects" / "bitcoin-trading" / "memory" / "v2" / "risk" / "risk_profile_fact_safe_latest.json"
BUNDLE = ROOT / "docs" / "final" / "artifacts" / "war_prolongation_benchmark_bundle_20260406.json"
AUTO_STATUS = ROOT / "docs" / "final" / "artifacts" / "war_prolongation_autopilot_status_latest.json"
READINESS = ROOT / "projects" / "bitcoin-trading" / "memory" / "v2" / "ops" / "ops_phase1_readiness_latest.json"
TRADING_CONFIG = ROOT / "projects" / "bitcoin-trading" / "config" / "trading_config.yaml"
KPI_SNAPSHOT_JSONL = ROOT / "projects" / "bitcoin-trading" / "memory" / "kpi" / "kpi_snapshot_20260406.jsonl"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def _load_tail_jsonl(path: Path, max_lines: int = 2000) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    rows: list[dict[str, Any]] = []
    for line in lines[-max_lines:]:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _trading_config_flags(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8", errors="ignore")
    enabled = "insight_observation_gate:\n    enabled: true" in text
    block = "insight_observation_gate:\n    enabled: true\n    log_path: \"\"\n    mode: block" in text
    # Fallback looser checks
    if not block:
        block = ("insight_observation_gate:" in text) and ("mode: block" in text)
    return {"insight_gate_enabled": enabled, "insight_gate_mode_block": block}


@dataclass
class SnapshotAgg:
    n: int
    avg_realized_24h_usdt: float | None
    avg_unrealized_pnl_usdt: float | None
    nonzero_position_ratio: float | None


def _aggregate_snapshots(rows: list[dict[str, Any]]) -> SnapshotAgg:
    if not rows:
        return SnapshotAgg(0, None, None, None)
    realized_vals = [float(r.get("realized_24h_usdt", 0.0)) for r in rows if r.get("realized_24h_usdt") is not None]
    unrealized_vals = [float(r.get("unrealized_pnl_usdt", 0.0)) for r in rows if r.get("unrealized_pnl_usdt") is not None]
    pos_nonzero = 0
    for r in rows:
        size = r.get("position_size")
        try:
            if float(size) != 0.0:
                pos_nonzero += 1
        except Exception:
            continue
    n = len(rows)
    return SnapshotAgg(
        n=n,
        avg_realized_24h_usdt=(sum(realized_vals) / len(realized_vals)) if realized_vals else None,
        avg_unrealized_pnl_usdt=(sum(unrealized_vals) / len(unrealized_vals)) if unrealized_vals else None,
        nonzero_position_ratio=(pos_nonzero / n) if n > 0 else None,
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Build BTC live upgrade verification report.")
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--output-md", type=Path, default=DEFAULT_SITREP)
    args = ap.parse_args()

    latest_kpi = _load_json(LATEST_KPI)
    risk = _load_json(RISK_PROFILE)
    bundle = _load_json(BUNDLE)
    auto = _load_json(AUTO_STATUS)
    readiness = _load_json(READINESS)
    cfg = _trading_config_flags(TRADING_CONFIG)
    snaps = _load_tail_jsonl(KPI_SNAPSHOT_JSONL, max_lines=3000)
    agg = _aggregate_snapshots(snaps)

    gate = ((bundle.get("snapshot") or {}).get("gate_decision")) or "UNKNOWN"
    promotion_ready = bool(auto.get("promotion_ready", False))
    risk_mode = str(risk.get("mode") or "")
    core_decision = str(((risk.get("singular_core") or {}).get("core_decision")) or "")
    readiness_ok = bool(readiness.get("all_ok", False))

    checklist = {
        "gate_go": gate == "GO",
        "promotion_ready": promotion_ready,
        "insight_gate_enabled": bool(cfg.get("insight_gate_enabled")),
        "insight_gate_block_mode": bool(cfg.get("insight_gate_mode_block")),
        "risk_profile_active_mode": risk_mode.lower() in ("n8n_active", "active", "live"),
        "risk_core_not_locked_hold": core_decision.upper() != "HOLD",
        "phase1_readiness_ok": readiness_ok,
    }

    all_checks_pass = all(checklist.values())
    payload = {
        "schema": "btc_live_upgrade_verification_v1",
        "generated_at_utc": _now(),
        "status": "ready_for_cautious_activation" if all_checks_pass else "guarded_activation_only",
        "checklist": checklist,
        "inputs": {
            "latest_kpi": str(LATEST_KPI).replace("\\", "/"),
            "risk_profile": str(RISK_PROFILE).replace("\\", "/"),
            "benchmark_bundle": str(BUNDLE).replace("\\", "/"),
            "autopilot_status": str(AUTO_STATUS).replace("\\", "/"),
            "phase1_readiness": str(READINESS).replace("\\", "/"),
            "kpi_snapshot_jsonl": str(KPI_SNAPSHOT_JSONL).replace("\\", "/"),
        },
        "runtime_snapshot": {
            "status_running": latest_kpi.get("status_running"),
            "status_enable_trading": latest_kpi.get("status_enable_trading"),
            "risk_profile_source": ((latest_kpi.get("risk_profile_pipeline") or {}).get("source")),
            "risk_profile_mode": ((latest_kpi.get("risk_profile_pipeline") or {}).get("mode")),
            "exchange_snapshot_24h_net": latest_kpi.get("exchange_snapshot_24h_net"),
            "kpi_snapshot_samples": agg.n,
            "avg_realized_24h_usdt": round(agg.avg_realized_24h_usdt, 6) if agg.avg_realized_24h_usdt is not None else None,
            "avg_unrealized_pnl_usdt": round(agg.avg_unrealized_pnl_usdt, 6) if agg.avg_unrealized_pnl_usdt is not None else None,
            "nonzero_position_ratio": round(agg.nonzero_position_ratio, 6) if agg.nonzero_position_ratio is not None else None,
        },
        "decision_hint": {
            "recommended_mode": "cautious_live" if all_checks_pass else "shadow_or_block",
            "reason": (
                "All checks pass."
                if all_checks_pass
                else "One or more guardrails still active (notably core HOLD/lock or readiness gate)."
            ),
        },
        "notes": [
            "No direct order execution; reporting only.",
            "Use this report before changing live leverage/risk caps.",
        ],
    }

    args.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md = [
        "# BTC Live Upgrade Verification",
        "",
        f"- generated_at_utc: {payload['generated_at_utc']}",
        f"- status: {payload['status']}",
        f"- recommended_mode: {payload['decision_hint']['recommended_mode']}",
        "",
        "## Checklist",
    ]
    for k, v in checklist.items():
        md.append(f"- {k}: {v}")
    md.extend(
        [
            "",
            "## Runtime Snapshot",
            f"- exchange_snapshot_24h_net: {payload['runtime_snapshot']['exchange_snapshot_24h_net']}",
            f"- kpi_snapshot_samples: {payload['runtime_snapshot']['kpi_snapshot_samples']}",
            f"- avg_realized_24h_usdt: {payload['runtime_snapshot']['avg_realized_24h_usdt']}",
            f"- nonzero_position_ratio: {payload['runtime_snapshot']['nonzero_position_ratio']}",
            "",
            f"Reason: {payload['decision_hint']['reason']}",
            "",
        ]
    )
    args.output_md.write_text("\n".join(md), encoding="utf-8")

    print(f"WROTE: {args.output_json}")
    print(f"WROTE: {args.output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

