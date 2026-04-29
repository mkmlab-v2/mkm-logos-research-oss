#!/usr/bin/env python3
"""Emit weekly Sasang commercialization operations report (observability only)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

READINESS = ART / "sasang_commercialization_readiness_packet_latest.json"
DRIFT = ART / "sasang_ready_drift_check_latest.json"
ROLLBACK = ART / "sasang_ready_rollback_drill_latest.json"
STATUS_CHAIN = ART / "sasang_commercialization_status_chain_latest.json"
SUPPLEMENTAL = ART / "sasang_supplemental_insight_score_latest.json"

OUT_LATEST = ART / "sasang_weekly_ops_report_latest.json"


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    now = datetime.now(timezone.utc)
    date_utc = now.strftime("%Y-%m-%d")
    iso_year, iso_week, _ = now.isocalendar()
    iso_week_label = f"{iso_year}-W{iso_week:02d}"

    readiness = _load(READINESS)
    drift = _load(DRIFT)
    rollback = _load(ROLLBACK)
    chain = _load(STATUS_CHAIN)
    supplemental = _load(SUPPLEMENTAL)

    warnings = ((readiness.get("go_no_go") or {}).get("warnings")) or []
    blockers = ((readiness.get("go_no_go") or {}).get("blockers")) or []
    supplemental_block = supplemental.get("supplemental_score") if isinstance(supplemental, dict) else {}

    report = {
        "schema": "sasang_weekly_ops_report_v1",
        "generated_at_utc": now.isoformat().replace("+00:00", "Z"),
        "refresh_calendar_date_utc": date_utc,
        "iso_week_label": iso_week_label,
        "sources": {
            "readiness": str(READINESS.resolve()) if READINESS.is_file() else None,
            "drift_check": str(DRIFT.resolve()) if DRIFT.is_file() else None,
            "rollback_drill": str(ROLLBACK.resolve()) if ROLLBACK.is_file() else None,
            "status_chain": str(STATUS_CHAIN.resolve()) if STATUS_CHAIN.is_file() else None,
            "supplemental_score": str(SUPPLEMENTAL.resolve()) if SUPPLEMENTAL.is_file() else None,
        },
        "headline": {
            "decision": readiness.get("decision"),
            "go": ((readiness.get("go_no_go") or {}).get("go")),
            "warning_count": len(warnings),
            "blocker_count": len(blockers),
            "warnings": warnings,
            "blockers": blockers,
        },
        "stability": {
            "drift_status": drift.get("status"),
            "drift_detected": drift.get("drift_detected"),
            "rollback_mode": rollback.get("mode"),
            "all_exit_zero": chain.get("all_exit_zero"),
        },
        "supplemental_insights": {
            "score_value": (supplemental_block or {}).get("value"),
            "score_band": (supplemental_block or {}).get("band"),
            "non_gating_policy": supplemental.get("non_gating_policy"),
        },
        "governance_note": (
            "This weekly report is operational observability only; it does not auto-change gates or "
            "override human signoff requirements."
        ),
        "out_of_scope": "No automatic Track B -> Track A autobind; no live-trading trigger from this JSON.",
    }

    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    OUT_LATEST.write_text(text, encoding="utf-8")
    dated = ART / f"sasang_weekly_ops_report_{date_utc}.json"
    dated.write_text(text, encoding="utf-8")
    print(f"WROTE: {OUT_LATEST}")
    print(f"WROTE: {dated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
