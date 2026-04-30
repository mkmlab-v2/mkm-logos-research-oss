#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.8, K:0.4, M:0.8}
# Balance: 89
# Purpose: Build weekly governance scorecard snapshot from KPI/mode/recovery/alerts.
# Keywords: weekly scorecard, governance, kpi, mode, recovery
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
    ap.add_argument("--kpi-json", type=Path, default=ART / "genius_governance_scheduler_kpi_latest.json")
    ap.add_argument("--mode-json", type=Path, default=ART / "genius_governance_scheduler_mode_signal_latest.json")
    ap.add_argument("--recovery-json", type=Path, default=ART / "genius_governance_scheduler_auto_recovery_latest.json")
    ap.add_argument("--alert-dispatch-json", type=Path, default=ART / "genius_governance_scheduler_health_alert_dispatch_latest.json")
    ap.add_argument("--completion-gate-json", type=Path, default=ART / "genius_governance_completion_gate_latest.json")
    ap.add_argument("--output-json", type=Path, default=ART / "genius_governance_weekly_scorecard_latest.json")
    args = ap.parse_args()

    kpi = _read_json(args.kpi_json)
    mode = _read_json(args.mode_json)
    recovery = _read_json(args.recovery_json)
    alert = _read_json(args.alert_dispatch_json)
    completion = _read_json(args.completion_gate_json)
    out = {
        "schema": "genius_governance_weekly_scorecard_v1",
        "generated_at_utc": _iso_now(),
        "inputs": {
            "kpi_json": str(args.kpi_json).replace("\\", "/"),
            "mode_json": str(args.mode_json).replace("\\", "/"),
            "recovery_json": str(args.recovery_json).replace("\\", "/"),
            "alert_dispatch_json": str(args.alert_dispatch_json).replace("\\", "/"),
            "completion_gate_json": str(args.completion_gate_json).replace("\\", "/"),
        },
        "summary": {
            "mode_signal": ((mode.get("mode_signal") or {}).get("mode")),
            "mode_reason": ((mode.get("mode_signal") or {}).get("reason")),
            "kpi_7d_pass_ratio": (((kpi.get("kpi") or {}).get("last_7d") or {}).get("pass_ratio")),
            "kpi_7d_hold_recurrence_rate": (((kpi.get("kpi") or {}).get("last_7d") or {}).get("hold_recurrence_rate")),
            "kpi_7d_recovery_attempts": (((kpi.get("kpi") or {}).get("last_7d") or {}).get("recovery_attempts")),
            "last_recovery_attempted": ((recovery.get("recovery") or {}).get("attempted")),
            "last_recovery_note": ((recovery.get("recovery") or {}).get("note")),
            "last_alert_dispatch_status": ((alert.get("dispatch") or {}).get("status")),
            "completion_gate_status": completion.get("status"),
            "completion_ready": bool(completion.get("completion_ready")),
        },
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output_json": str(args.output_json).replace("\\", "/"), "completion_ready": out["summary"]["completion_ready"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
