#!/usr/bin/env python3
"""Execute controlled Track A bridge from approved sasang 4-agent gate."""

from __future__ import annotations

import argparse
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
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--shadow-ratio", type=float, default=0.1, help="0~1 rollout shadow ratio")
    ap.add_argument("--max-live-risk-fraction", type=float, default=0.05, help="0~1 risk fraction cap")
    args = ap.parse_args()

    root = Path(__file__).resolve().parents[1]
    art = root / "docs" / "final" / "artifacts"
    gate_path = art / "sasang_4agent_promotion_gate_latest.json"
    protocol_path = art / "sasang_4agent_collision_btrack_protocol_latest.json"
    out_json = art / "sasang_4agent_tracka_bridge_latest.json"
    out_md = art / "sasang_4agent_tracka_bridge_latest.md"

    gate = _safe_json(gate_path)
    protocol = _safe_json(protocol_path)
    if not gate:
        raise SystemExit(f"missing promotion gate: {gate_path}")
    if str(gate.get("decision")) != "A_TRACK_PROMOTED_WITH_HUMAN_APPROVAL":
        raise SystemExit("promotion gate is not approved for bridge")
    if not bool(gate.get("auto_bridge_allowed")):
        raise SystemExit("auto_bridge_allowed is false; bridge is blocked")

    shadow_ratio = max(0.0, min(1.0, float(args.shadow_ratio)))
    risk_fraction = max(0.0, min(1.0, float(args.max_live_risk_fraction)))
    ts = _now_utc()

    payload = {
        "schema": "sasang_4agent_tracka_bridge_v1",
        "executed_at_utc": ts,
        "bridge_mode": "controlled_shadow",
        "status": "ACTIVE",
        "source_refs": {
            "promotion_gate": str(gate_path).replace("\\", "/"),
            "protocol": str(protocol_path).replace("\\", "/"),
        },
        "controls": {
            "shadow_ratio": shadow_ratio,
            "max_live_risk_fraction": risk_fraction,
            "require_hold_on_alert": True,
        },
        "runtime_policy": {
            "fallback_decision": "HOLD",
            "policy_label": "NON_GATING",
            "research_to_prod_bridge": "human_approved_controlled_only",
        },
    }
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md = [
        "# Sasang 4-Agent Track A Bridge",
        "",
        f"- executed_at_utc: `{ts}`",
        f"- status: `{payload['status']}`",
        f"- bridge_mode: `{payload['bridge_mode']}`",
        f"- shadow_ratio: `{shadow_ratio}`",
        f"- max_live_risk_fraction: `{risk_fraction}`",
        "",
        "## Runtime Policy",
        f"- fallback_decision: `{payload['runtime_policy']['fallback_decision']}`",
        f"- policy_label: `{payload['runtime_policy']['policy_label']}`",
        f"- research_to_prod_bridge: `{payload['runtime_policy']['research_to_prod_bridge']}`",
        "",
    ]
    out_md.write_text("\n".join(md), encoding="utf-8")
    print(str(out_json))
    print(str(out_md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

