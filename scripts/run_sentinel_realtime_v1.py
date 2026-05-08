#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path("C:/workspace")
ART = ROOT / "docs" / "final" / "artifacts"
OUT = ART / "sentinel_realtime_alert_latest.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}


def main() -> int:
    ap = argparse.ArgumentParser(description="Build sentinel realtime alert from current artifacts.")
    ap.add_argument("--severity", default="medium", choices=["low", "medium", "high", "critical"])
    ap.add_argument("--category", default="runtime", choices=["runtime", "cost", "security", "policy", "hardware"])
    ap.add_argument("--signal-key", default="manual_probe")
    ap.add_argument("--observed-value", default="1")
    ap.add_argument("--threshold", default="0")
    ap.add_argument("--level", default="L1", choices=["L1", "L2", "L3"])
    args = ap.parse_args()

    c2 = _read_json(ART / "c2_aegis_guardrail_status_latest.json")
    cost = _read_json(ART / "cost_watch_monitor_latest.json")
    go = _read_json(ART / "a_track_go_nogo_status_latest.json")

    requires_approval = args.level in {"L2", "L3"}
    payload = {
        "schema": "sentinel_realtime_alert_v1",
        "schema_version": "1.0.0",
        "ts_utc": _now_iso(),
        "severity": args.severity,
        "category": args.category,
        "trigger": {
            "signal_key": args.signal_key,
            "observed_value": args.observed_value,
            "threshold": args.threshold,
        },
        "fact_lock": {"track": "ops", "gating": "GATED" if requires_approval else "NON_GATING"},
        "recommended_response": {
            "level": args.level,
            "owner": "Commander" if requires_approval else "Operator",
            "requires_commander_approval": requires_approval,
        },
        "evidence_paths": [
            "docs/final/artifacts/c2_aegis_guardrail_status_latest.json",
            "docs/final/artifacts/cost_watch_monitor_latest.json",
            "docs/final/artifacts/a_track_go_nogo_status_latest.json",
        ],
        "context_snapshot": {
            "c2_status": c2.get("status"),
            "cost_billing_status": (cost.get("billing") or {}).get("status"),
            "a_track_go_no_go": (go.get("result") or {}).get("overall_go_no_go"),
        },
        "correlation_id": str(uuid.uuid4()),
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote: {OUT}")
    print(f"severity={args.severity} level={args.level}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

