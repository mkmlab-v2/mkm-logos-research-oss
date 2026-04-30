#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.8, K:0.3, M:0.8}
# Balance: 90
# Purpose: Emit scheduler operating mode signal from 48h stability and current health.
# Keywords: mode signal, observe mode, tuning mode, scheduler governance
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_STABILITY = ART / "genius_governance_scheduler_stability_48h_latest.json"
DEFAULT_HEALTH = ART / "genius_governance_scheduler_health_check_latest.json"
DEFAULT_OUT = ART / "genius_governance_scheduler_mode_signal_latest.json"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stability-48h-json", type=Path, default=DEFAULT_STABILITY)
    ap.add_argument("--health-json", type=Path, default=DEFAULT_HEALTH)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    stability = _read_json(args.stability_48h_json)
    health = _read_json(args.health_json)
    stable_48h = bool((stability.get("current") or {}).get("stable_48h"))
    health_status = str(health.get("status") or "UNKNOWN").upper()

    if stable_48h and health_status == "PASS":
        mode = "OBSERVE_MODE"
        reason = "stable_48h_pass_and_current_health_pass"
    else:
        mode = "TUNING_MODE"
        reason = "stability_or_current_health_not_pass"

    out = {
        "schema": "genius_governance_scheduler_mode_signal_v1",
        "generated_at_utc": _iso_now(),
        "inputs": {
            "stability_48h_json": str(args.stability_48h_json).replace("\\", "/"),
            "health_json": str(args.health_json).replace("\\", "/"),
        },
        "current": {
            "stable_48h": stable_48h,
            "health_status": health_status,
        },
        "mode_signal": {
            "mode": mode,
            "reason": reason,
        },
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output_json": str(args.output_json).replace("\\", "/"), "mode": mode}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
