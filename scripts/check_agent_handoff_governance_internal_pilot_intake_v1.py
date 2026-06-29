#!/usr/bin/env python3
"""Validate active internal pilot intake JSON (no network)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INTAKE = SCRIPT_ROOT / "reports/agent_handoff_governance_internal_pilot_intake_mkm_internal_v1.json"
KPI_PATH = SCRIPT_ROOT / "docs/final/artifacts/agent_handoff_governance_pilot_kpi_v1_latest.json"


def _fail(msg: str) -> int:
    print(f"FAIL: {msg}", file=sys.stderr)
    return 1


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--intake", type=Path, default=DEFAULT_INTAKE)
    args = ap.parse_args()

    intake_path = args.intake.resolve()
    if not intake_path.is_file():
        return _fail(f"missing intake {intake_path}")

    intake = _load(intake_path)
    if intake.get("schema") != "agent_handoff_governance_internal_pilot_intake_v1":
        return _fail("schema mismatch")
    if not intake.get("research_only"):
        return _fail("must be research_only")
    cid = intake.get("customer_id")
    if not cid or cid == "INTERNAL_PILOT_EXAMPLE":
        return _fail("customer_id must be set to a real internal slug")
    if intake.get("status") not in ("active_internal_pilot", "completed_internal_pilot"):
        return _fail(f"unexpected status: {intake.get('status')}")

    if not KPI_PATH.is_file():
        return _fail(f"missing KPI {KPI_PATH}")
    kpi = _load(KPI_PATH)
    kpi_cid = kpi.get("customer_id")
    if kpi_cid != cid:
        return _fail(f"KPI customer_id {kpi_cid!r} must match intake {cid!r}")

    roi = intake.get("roi_measurement") or {}
    if roi.get("customer_monthly_context_spend_usd") not in (None, 0):
        return _fail("dollar ROI must stay null during pilot start — measure at window end")

    print("OK: agent_handoff_governance_internal_pilot_intake")
    print(f"  intake: {intake_path.relative_to(SCRIPT_ROOT)}")
    print(f"  customer_id: {cid}")
    print(f"  lane: {intake.get('lane')}")
    print(f"  status: {intake.get('status')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
