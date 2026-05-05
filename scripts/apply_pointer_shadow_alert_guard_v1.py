#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "docs" / "final" / "artifacts"
DECISION_DEFAULT = ART / "genesis_pointer_routing_decision_latest.json"
ALERT_DEFAULT = ART / "pointer_hash_snapping_router_shadow_alert_latest.json"
OUT_DEFAULT = ART / "genesis_pointer_routing_decision_guarded_latest.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--decision-json", type=Path, default=DECISION_DEFAULT)
    ap.add_argument("--alert-json", type=Path, default=ALERT_DEFAULT)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    decision_path = args.decision_json if args.decision_json.is_absolute() else ROOT / args.decision_json
    alert_path = args.alert_json if args.alert_json.is_absolute() else ROOT / args.alert_json
    out_path = args.out if args.out.is_absolute() else ROOT / args.out

    decision = _read_json(decision_path)
    alert = _read_json(alert_path)
    should_alert = bool(alert.get("should_alert", False))

    guarded = dict(decision)
    guarded["schema"] = "genesis_pointer_routing_decision_guarded_v1"
    guarded["guard_generated_at_utc"] = _now_utc()
    guarded["guard_inputs"] = {
        "decision_json": str(decision_path),
        "alert_json": str(alert_path),
    }
    guarded["guard_applied"] = should_alert
    if should_alert:
        guarded["decision"] = "HOLD_POINTER_ROUTE"
        guarded["route_mode"] = "track_a_primary"
        guarded["guard_reason"] = "shadow_health_alert_triggered"
    else:
        guarded["guard_reason"] = "no_alert"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(guarded, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(out_path),
                "guard_applied": should_alert,
                "decision": guarded.get("decision"),
                "route_mode": guarded.get("route_mode"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
