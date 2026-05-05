#!/usr/bin/env python3
"""Build one-file monthly suite status for genius governance automation."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_MONTHLY_REFRESH = ART / "genius_reasoning_benchmark_report_latest.json"
DEFAULT_CHAOS_DRILL = ART / "genius_dispatch_chaos_drill_latest.json"
DEFAULT_HOLD_REHEARSAL = ART / "genius_human_review_hold_rehearsal_latest.json"
DEFAULT_UNIFIED = ART / "cursor_ai_unified_status_dashboard_latest.json"
DEFAULT_OUT = ART / "genius_governance_monthly_suite_status_latest.json"


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
    ap.add_argument("--monthly-refresh-json", type=Path, default=DEFAULT_MONTHLY_REFRESH)
    ap.add_argument("--chaos-drill-json", type=Path, default=DEFAULT_CHAOS_DRILL)
    ap.add_argument("--hold-rehearsal-json", type=Path, default=DEFAULT_HOLD_REHEARSAL)
    ap.add_argument("--unified-dashboard-json", type=Path, default=DEFAULT_UNIFIED)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    monthly = _read_json(args.monthly_refresh_json)
    chaos = _read_json(args.chaos_drill_json)
    hold = _read_json(args.hold_rehearsal_json)
    unified = _read_json(args.unified_dashboard_json)

    monthly_pass = str((monthly.get("summary") or {}).get("benchmark_status") or "") == "PASS"
    chaos_pass = bool(chaos.get("pass"))
    hold_pass = bool(hold.get("pass"))
    unified_go = str(unified.get("status") or "") == "GO"
    overall = "PASS" if (monthly_pass and chaos_pass and hold_pass and unified_go) else "HOLD"

    out = {
        "schema": "genius_governance_monthly_suite_status_v1",
        "generated_at_utc": _iso_now(),
        "inputs": {
            "monthly_refresh_json": str(args.monthly_refresh_json).replace("\\", "/"),
            "chaos_drill_json": str(args.chaos_drill_json).replace("\\", "/"),
            "hold_rehearsal_json": str(args.hold_rehearsal_json).replace("\\", "/"),
            "unified_dashboard_json": str(args.unified_dashboard_json).replace("\\", "/"),
        },
        "status": overall,
        "components": {
            "monthly_refresh_benchmark_pass": monthly_pass,
            "chaos_drill_pass": chaos_pass,
            "hold_rehearsal_pass": hold_pass,
            "unified_dashboard_go": unified_go,
        },
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "status": overall, "output_json": str(args.output_json).replace("\\", "/")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
