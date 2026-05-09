#!/usr/bin/env python3
"""Build machine-readable execution gate status for pure-real daily ops."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_ACTION_PACK = ART / "logos_pure_real_action_pack_latest.json"
DEFAULT_MONITOR = ART / "logos_backfill_dependence_monitor_latest.json"
DEFAULT_OUT = ART / "logos_pure_real_execution_gate_status_latest.json"


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Build pure-real execution gate status.")
    ap.add_argument("--action-pack-json", type=Path, default=DEFAULT_ACTION_PACK)
    ap.add_argument("--monitor-json", type=Path, default=DEFAULT_MONITOR)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    action_pack = _load_json(args.action_pack_json)
    monitor = _load_json(args.monitor_json)

    execution_status = str((action_pack.get("status") or {}).get("execution_status") or "")
    priority = str((action_pack.get("status") or {}).get("priority") or "")
    delta_status = str(monitor.get("status") or "")
    delta = float((monitor.get("metrics") or {}).get("delta_mixed_minus_pure") or 0.0)

    blockers: list[str] = []
    if execution_status == "OFF_TRACK_NEED_CATCHUP":
        blockers.append("OFF_TRACK_DAILY_EXECUTION")
    if delta_status == "FAIL_HIGH_BACKFILL_DEPENDENCE":
        blockers.append("HIGH_BACKFILL_DEPENDENCE")

    if execution_status == "PASS_TARGET_REACHED" and delta_status != "FAIL_HIGH_BACKFILL_DEPENDENCE":
        gate = "PASS_EXECUTION_AND_DELTA_OK"
    elif blockers:
        gate = "FAIL_ACTION_REQUIRED"
    else:
        gate = "WARN_CONTINUE_DAILY_EXECUTION"

    out = {
        "schema": "logos_pure_real_execution_gate_status_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_track": "B",
        "research_only": True,
        "auto_bind_to_atrack_forbidden": True,
        "inputs": {
            "execution_status": execution_status,
            "priority": priority,
            "backfill_dependence_status": delta_status,
            "delta_mixed_minus_pure": delta,
        },
        "blockers": blockers,
        "gate_status": gate,
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "output_json": str(args.output_json),
                "gate_status": gate,
                "blocker_count": len(blockers),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

