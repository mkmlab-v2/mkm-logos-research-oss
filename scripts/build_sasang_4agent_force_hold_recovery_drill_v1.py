#!/usr/bin/env python3
"""Build summary artifact for FORCE_HOLD -> recovery drill."""

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
    force_hold = _safe_json(art / "sasang_4agent_force_hold_latest.json")
    gate = _safe_json(art / "sasang_4agent_promotion_gate_latest.json")
    bridge = _safe_json(art / "sasang_4agent_tracka_bridge_latest.json")
    monitor = _safe_json(art / "sasang_4agent_monitor_snapshot_latest.json")

    status = "PASS"
    reasons: list[str] = []
    if str(force_hold.get("status")) != "FORCE_HOLD_APPLIED":
        status = "HOLD"
        reasons.append("force_hold_not_applied")
    if str(gate.get("decision")) != "A_TRACK_PROMOTED_WITH_HUMAN_APPROVAL":
        status = "HOLD"
        reasons.append("gate_not_recovered_to_promoted")
    if str(bridge.get("status")) != "ACTIVE":
        status = "HOLD"
        reasons.append("bridge_not_active_after_recovery")
    if bool(monitor.get("alert")):
        status = "HOLD"
        reasons.append("monitor_alert_after_recovery")

    out_json = art / "sasang_4agent_force_hold_recovery_drill_latest.json"
    out_md = art / "sasang_4agent_force_hold_recovery_drill_latest.md"
    payload = {
        "schema": "sasang_4agent_force_hold_recovery_drill_v1",
        "generated_at_utc": _now_utc(),
        "status": status,
        "checks": {
            "force_hold_applied": str(force_hold.get("status")) == "FORCE_HOLD_APPLIED",
            "gate_recovered_to_promoted": str(gate.get("decision")) == "A_TRACK_PROMOTED_WITH_HUMAN_APPROVAL",
            "bridge_active_after_recovery": str(bridge.get("status")) == "ACTIVE",
            "monitor_alert_false": not bool(monitor.get("alert")),
        },
        "reasons": reasons,
        "refs": {
            "force_hold": "docs/final/artifacts/sasang_4agent_force_hold_latest.json",
            "gate": "docs/final/artifacts/sasang_4agent_promotion_gate_latest.json",
            "bridge": "docs/final/artifacts/sasang_4agent_tracka_bridge_latest.json",
            "monitor": "docs/final/artifacts/sasang_4agent_monitor_snapshot_latest.json",
        },
    }
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Sasang 4-Agent Force Hold Recovery Drill",
        "",
        f"- generated_at_utc: `{payload['generated_at_utc']}`",
        f"- status: `{payload['status']}`",
        "",
        "## Checks",
    ]
    for k, v in payload["checks"].items():
        lines.append(f"- {k}: `{v}`")
    if reasons:
        lines.extend(["", "## Reasons"])
        for r in reasons:
            lines.append(f"- {r}")
    lines.append("")
    out_md.write_text("\n".join(lines), encoding="utf-8")
    print(str(out_json))
    print(str(out_md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

