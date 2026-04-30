#!/usr/bin/env python3
"""Build monitoring snapshot for promoted sasang 4-agent Track A bridge."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _safe_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    art = root / "docs" / "final" / "artifacts"
    protocol = _safe_json(art / "sasang_4agent_collision_btrack_protocol_latest.json")
    bridge = _safe_json(art / "sasang_4agent_tracka_bridge_latest.json")
    gate = _safe_json(art / "sasang_4agent_promotion_gate_latest.json")
    out_json = art / "sasang_4agent_monitor_snapshot_latest.json"
    out_md = art / "sasang_4agent_monitor_snapshot_latest.md"

    if not protocol:
        raise SystemExit("missing protocol artifact")

    res = protocol.get("results") if isinstance(protocol.get("results"), dict) else {}
    ts = _now_utc()
    alert = False
    reasons: list[str] = []

    mdd_reduction = float(res.get("mdd_reduction_abs") or 0.0)
    hold_ratio = float(res.get("hold_ratio") or 0.0)
    topo_p95 = float(res.get("topological_variance_p95") or 0.0)
    sig = bool(res.get("statistical_significance_pass_p_lt_0_05"))

    if mdd_reduction <= 0:
        alert = True
        reasons.append("mdd_reduction_non_positive")
    if hold_ratio >= 0.95:
        alert = True
        reasons.append("hold_ratio_too_high")
    if topo_p95 >= 1.2:
        alert = True
        reasons.append("topological_variance_p95_too_high")
    if not sig:
        alert = True
        reasons.append("significance_gate_failed")

    payload = {
        "schema": "sasang_4agent_monitor_snapshot_v1",
        "generated_at_utc": ts,
        "source_refs": {
            "protocol": "docs/final/artifacts/sasang_4agent_collision_btrack_protocol_latest.json",
            "bridge": "docs/final/artifacts/sasang_4agent_tracka_bridge_latest.json",
            "gate": "docs/final/artifacts/sasang_4agent_promotion_gate_latest.json",
        },
        "bridge_status": str(bridge.get("status") or "UNKNOWN"),
        "gate_decision": str(gate.get("decision") or "UNKNOWN"),
        "metrics": {
            "mdd_reduction_abs": mdd_reduction,
            "hold_ratio": hold_ratio,
            "topological_variance_p95": topo_p95,
            "significance_pass": sig,
        },
        "alert": alert,
        "alert_reasons": reasons,
        "recommended_action": "FORCE_HOLD" if alert else "KEEP_CONTROLLED_BRIDGE",
    }
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Sasang 4-Agent Monitor Snapshot",
        "",
        f"- generated_at_utc: `{ts}`",
        f"- bridge_status: `{payload['bridge_status']}`",
        f"- gate_decision: `{payload['gate_decision']}`",
        f"- alert: `{alert}`",
        f"- recommended_action: `{payload['recommended_action']}`",
        "",
        "## Metrics",
        f"- mdd_reduction_abs: `{mdd_reduction}`",
        f"- hold_ratio: `{hold_ratio}`",
        f"- topological_variance_p95: `{topo_p95}`",
        f"- significance_pass: `{sig}`",
        "",
    ]
    if reasons:
        lines.append("## Alert Reasons")
        for r in reasons:
            lines.append(f"- {r}")
        lines.append("")
    out_md.write_text("\n".join(lines), encoding="utf-8")
    print(str(out_json))
    print(str(out_md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

