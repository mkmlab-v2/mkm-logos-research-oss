#!/usr/bin/env python3
"""Emergency rollback switch: force HOLD for sasang 4-agent Track A bridge."""

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
    ap.add_argument("--reason", default="manual_emergency_switch")
    args = ap.parse_args()

    root = Path(__file__).resolve().parents[1]
    art = root / "docs" / "final" / "artifacts"
    bridge_path = art / "sasang_4agent_tracka_bridge_latest.json"
    gate_path = art / "sasang_4agent_promotion_gate_latest.json"
    out_json = art / "sasang_4agent_force_hold_latest.json"
    out_md = art / "sasang_4agent_force_hold_latest.md"
    ts = _now_utc()

    bridge = _safe_json(bridge_path)
    gate = _safe_json(gate_path)

    if bridge:
        bridge["status"] = "FORCE_HOLD"
        bridge["bridge_mode"] = "halted"
        bridge["runtime_policy"] = bridge.get("runtime_policy") or {}
        if isinstance(bridge["runtime_policy"], dict):
            bridge["runtime_policy"]["fallback_decision"] = "HOLD"
            bridge["runtime_policy"]["halt_reason"] = args.reason
        bridge["halted_at_utc"] = ts
        bridge_path.write_text(json.dumps(bridge, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if gate:
        gate["auto_bridge_allowed"] = False
        gate["decision"] = "A_TRACK_FORCE_HOLD"
        gate["force_hold_at_utc"] = ts
        gate["force_hold_reason"] = args.reason
        gate_path.write_text(json.dumps(gate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    payload = {
        "schema": "sasang_4agent_force_hold_v1",
        "executed_at_utc": ts,
        "reason": args.reason,
        "updated_bridge": bool(bridge),
        "updated_gate": bool(gate),
        "status": "FORCE_HOLD_APPLIED",
    }
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out_md.write_text(
        "\n".join(
            [
                "# Sasang 4-Agent Force HOLD",
                "",
                f"- executed_at_utc: `{ts}`",
                f"- reason: `{args.reason}`",
                f"- updated_bridge: `{bool(bridge)}`",
                f"- updated_gate: `{bool(gate)}`",
                f"- status: `{payload['status']}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(str(out_json))
    print(str(out_md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

