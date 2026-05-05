#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.8, K:0.3, M:0.9}
# Balance: 91
# Purpose: Decide completion gate for scheduler performance improvement.
# Keywords: completion gate, stable, hold recurrence, recovery attempts
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"


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
    ap.add_argument("--stability-json", type=Path, default=ART / "genius_governance_scheduler_stability_48h_latest.json")
    ap.add_argument("--kpi-json", type=Path, default=ART / "genius_governance_scheduler_kpi_latest.json")
    ap.add_argument("--max-24h-hold-recurrence", type=float, default=0.0)
    ap.add_argument("--max-24h-recovery-attempts", type=int, default=1)
    ap.add_argument("--output-json", type=Path, default=ART / "genius_governance_completion_gate_latest.json")
    args = ap.parse_args()

    stability = _read_json(args.stability_json)
    kpi = _read_json(args.kpi_json)
    stable_48h = bool((stability.get("current") or {}).get("stable_48h"))
    k24 = (kpi.get("kpi") or {}).get("last_24h") or {}
    hold_recur = float(k24.get("hold_recurrence_rate") or 0.0)
    recovery_attempts = int(k24.get("recovery_attempts") or 0)

    done = (
        stable_48h
        and hold_recur <= float(args.max_24h_hold_recurrence)
        and recovery_attempts <= int(args.max_24h_recovery_attempts)
    )
    out = {
        "schema": "genius_governance_completion_gate_v1",
        "generated_at_utc": _iso_now(),
        "inputs": {
            "stability_json": str(args.stability_json).replace("\\", "/"),
            "kpi_json": str(args.kpi_json).replace("\\", "/"),
            "max_24h_hold_recurrence": float(args.max_24h_hold_recurrence),
            "max_24h_recovery_attempts": int(args.max_24h_recovery_attempts),
        },
        "current": {
            "stable_48h": stable_48h,
            "kpi_24h_hold_recurrence_rate": hold_recur,
            "kpi_24h_recovery_attempts": recovery_attempts,
        },
        "status": "PASS" if done else "HOLD",
        "completion_ready": done,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output_json": str(args.output_json).replace("\\", "/"), "status": out["status"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
