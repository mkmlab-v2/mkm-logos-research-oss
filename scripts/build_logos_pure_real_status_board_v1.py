#!/usr/bin/env python3
"""Build single-file status board for pure-real daily operations."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_OUT = ART / "logos_pure_real_status_board_latest.json"


def _safe_load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Build pure-real operations status board.")
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    go_nogo = _safe_load(ART / "logos_pure_real_daily_go_nogo_latest.json")
    monitor = _safe_load(ART / "logos_backfill_dependence_monitor_latest.json")
    d7 = _safe_load(ART / "logos_pure_real_d7_stability_checklist_latest.json")
    drift = _safe_load(ART / "logos_pure_real_baseline_drift_check_latest.json")

    go_value = str(go_nogo.get("decision") or "MISSING")
    monitor_value = str(monitor.get("status") or "MISSING")
    d7_value = str((d7.get("summary") or {}).get("overall_status") or "MISSING")
    drift_value = str((drift.get("summary") or {}).get("overall_status") or "MISSING")

    checks = [
        {"id": "go_nogo", "expected": "GO", "actual": go_value, "status": "PASS" if go_value == "GO" else "FAIL"},
        {
            "id": "backfill_monitor",
            "expected": "PASS_LOW_BACKFILL_DEPENDENCE",
            "actual": monitor_value,
            "status": "PASS" if monitor_value == "PASS_LOW_BACKFILL_DEPENDENCE" else "FAIL",
        },
        {
            "id": "d7_stability",
            "expected": "PASS_STABLE_D7_READY",
            "actual": d7_value,
            "status": "PASS" if d7_value == "PASS_STABLE_D7_READY" else "FAIL",
        },
        {
            "id": "baseline_drift",
            "expected": "PASS_ALIGNED_WITH_BASELINE",
            "actual": drift_value,
            "status": "PASS" if drift_value == "PASS_ALIGNED_WITH_BASELINE" else "FAIL",
        },
    ]

    fail_count = sum(1 for c in checks if c["status"] == "FAIL")
    overall = "PASS_OPERATIONAL" if fail_count == 0 else "FAIL_ACTION_REQUIRED"

    out = {
        "schema": "logos_pure_real_status_board_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_track": "B",
        "research_only": True,
        "auto_bind_to_atrack_forbidden": True,
        "summary": {
            "overall_status": overall,
            "fail_count": fail_count,
            "pass_count": len(checks) - fail_count,
            "check_count": len(checks),
        },
        "checks": checks,
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"ok": True, "output_json": str(args.output_json), "overall_status": overall, "fail_count": fail_count},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

