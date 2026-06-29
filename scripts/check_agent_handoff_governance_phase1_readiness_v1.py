#!/usr/bin/env python3
"""Readiness check for Agent Handoff Governance Phase 1 pack (no network)."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

SCRIPT_ROOT = Path(__file__).resolve().parents[1]

KPI_PATH = SCRIPT_ROOT / "docs/final/artifacts/agent_handoff_governance_pilot_kpi_v1_latest.json"
ONEPAGER_JSON = SCRIPT_ROOT / "docs/final/artifacts/agent_handoff_governance_enterprise_onepager_v1_latest.json"
ONEPAGER_MD = SCRIPT_ROOT / "docs/final/artifacts/agent_handoff_governance_enterprise_onepager_v1_latest.md"
SCHEMA_PATH = SCRIPT_ROOT / "docs/final/schemas/agent_handoff_governance_pilot_kpi_v1.schema.json"

FORBIDDEN_MD_PATTERNS = [
    re.compile(r"100%\s*무손실", re.I),
    re.compile(r"guaranteed\s+returns?", re.I),
    re.compile(r"1,?000\s*만\s*원", re.I),
    re.compile(r"상용\s*SLA\s*보장", re.I),
]

REQUIRED_ONEPAGER_KEYS = [
    "distribution",
    "legal_review_status",
    "disclaimers_ko",
    "disclaimers_en",
    "not_included_v1",
    "boundary_ack",
]


def _fail(msg: str) -> int:
    print(f"FAIL: {msg}", file=sys.stderr)
    return 1


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    missing = [p for p in (KPI_PATH, ONEPAGER_JSON, ONEPAGER_MD, SCHEMA_PATH) if not p.is_file()]
    if missing:
        return _fail("missing files: " + ", ".join(str(p) for p in missing))

    kpi = _load(KPI_PATH)
    onepager = _load(ONEPAGER_JSON)
    md_text = ONEPAGER_MD.read_text(encoding="utf-8")

    if kpi.get("schema") != "agent_handoff_governance_pilot_kpi_v1":
        return _fail("kpi schema mismatch")
    if onepager.get("schema") != "agent_handoff_governance_enterprise_onepager_v1":
        return _fail("onepager schema mismatch")
    if not kpi.get("research_only"):
        return _fail("kpi must be research_only")
    if onepager.get("distribution") != "INTERNAL_DRAFT":
        return _fail("onepager must stay INTERNAL_DRAFT until legal review")
    if onepager.get("legal_review_status") != "PENDING":
        return _fail("unexpected legal_review_status — human promotion only")

    for key in REQUIRED_ONEPAGER_KEYS:
        if key not in onepager:
            return _fail(f"onepager missing key: {key}")

    if not onepager.get("disclaimers_ko") or not onepager.get("disclaimers_en"):
        return _fail("disclaimers required")

    for pat in FORBIDDEN_MD_PATTERNS:
        if pat.search(md_text):
            return _fail(f"forbidden marketing pattern in MD: {pat.pattern}")

    kpi_ids = {row.get("kpi_id") for row in kpi.get("kpi_rows", [])}
    required_kpis = {"inject_tokens_off", "must_keep_gate_pass_rate", "token_reduction_vs_full_anchors"}
    if not required_kpis.issubset(kpi_ids):
        return _fail(f"missing kpi_ids: {required_kpis - kpi_ids}")

    roi = kpi.get("roi_hypothesis") or {}
    if roi.get("customer_monthly_context_spend_usd") not in (None, 0):
        if not roi.get("projected_savings_note"):
            return _fail("roi_hypothesis spend set without projected_savings_note guard")

    print("OK: agent_handoff_governance_phase1_readiness")
    print(f"  kpi: {KPI_PATH.relative_to(SCRIPT_ROOT)}")
    print(f"  onepager: {ONEPAGER_JSON.relative_to(SCRIPT_ROOT)}")
    print(f"  pilot_status: {kpi.get('pilot_status')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
