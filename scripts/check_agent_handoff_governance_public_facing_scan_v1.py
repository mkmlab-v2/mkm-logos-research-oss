#!/usr/bin/env python3
"""Engineering cross-check for Agent Handoff Governance pack vs PUBLIC_FACING v1.7.

Not legal sign-off. Blocks ready_for_external_send while legal_review_status is PENDING.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
ONEPAGER_JSON = SCRIPT_ROOT / "docs/final/artifacts/agent_handoff_governance_enterprise_onepager_v1_latest.json"
ONEPAGER_MD = SCRIPT_ROOT / "docs/final/artifacts/agent_handoff_governance_enterprise_onepager_v1_latest.md"
KPI_PATH = SCRIPT_ROOT / "docs/final/artifacts/agent_handoff_governance_pilot_kpi_v1_latest.json"
BASELINE_SUMMARY = SCRIPT_ROOT / "reports/agent_handoff_governance_weekly_baseline_summary_v1_latest.json"
COPY_GUARD = SCRIPT_ROOT / "scripts/check_track_c_copy_guard_v1.py"
PUBLIC_FACING_REF = "docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md v1.7"

FORBIDDEN_MARKETING = [
    re.compile(r"100%\s*무손실", re.I),
    re.compile(r"\bguaranteed\s+returns?\b", re.I),
    re.compile(r"상용\s*SLA\s*보장", re.I),
    re.compile(r"신경과학적으로\s*증명", re.I),
    re.compile(r"neuroscience[- ]proven", re.I),
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _run_copy_guard(target: Path) -> tuple[bool, str]:
    r = subprocess.run(
        [sys.executable, str(COPY_GUARD), str(target)],
        cwd=SCRIPT_ROOT,
        capture_output=True,
        text=True,
    )
    out = (r.stdout or "") + (r.stderr or "")
    return r.returncode == 0, out.strip()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--out-json",
        default="reports/agent_handoff_governance_public_facing_scan_v1_latest.json",
    )
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args()

    checks: list[dict[str, Any]] = []
    failures: list[str] = []

    missing = [p for p in (ONEPAGER_JSON, ONEPAGER_MD, KPI_PATH) if not p.is_file()]
    if missing:
        for p in missing:
            failures.append(f"missing:{p.relative_to(SCRIPT_ROOT)}")
        checks.append({"id": "files_present", "ok": False, "missing": [str(p) for p in missing]})
    else:
        checks.append({"id": "files_present", "ok": True})

    onepager = _load(ONEPAGER_JSON) if ONEPAGER_JSON.is_file() else {}
    kpi = _load(KPI_PATH) if KPI_PATH.is_file() else {}
    md_text = ONEPAGER_MD.read_text(encoding="utf-8") if ONEPAGER_MD.is_file() else ""

    for check_id, ok, detail in (
        ("distribution_internal_draft", onepager.get("distribution") == "INTERNAL_DRAFT", onepager.get("distribution")),
        ("legal_review_pending", onepager.get("legal_review_status") == "PENDING", onepager.get("legal_review_status")),
        ("research_only", bool(onepager.get("research_only") and kpi.get("research_only")), None),
        ("disclaimers_ko", bool(onepager.get("disclaimers_ko")), len(onepager.get("disclaimers_ko") or [])),
        ("disclaimers_en", bool(onepager.get("disclaimers_en")), len(onepager.get("disclaimers_en") or [])),
        ("not_included_v1", bool(onepager.get("not_included_v1")), len(onepager.get("not_included_v1") or [])),
        ("boundary_ack", bool(onepager.get("boundary_ack")), None),
    ):
        checks.append({"id": check_id, "ok": ok, "detail": detail})
        if not ok:
            failures.append(check_id)

    for target in (ONEPAGER_MD, ONEPAGER_JSON):
        ok, msg = _run_copy_guard(target)
        checks.append({"id": f"copy_guard:{target.name}", "ok": ok, "detail": msg.splitlines()[-1] if msg else ""})
        if not ok:
            failures.append(f"copy_guard:{target.name}")

    marketing_hits: list[str] = []
    for pat in FORBIDDEN_MARKETING:
        if pat.search(md_text):
            marketing_hits.append(pat.pattern)
    checks.append({"id": "md:forbidden_marketing", "ok": not marketing_hits, "patterns": marketing_hits})
    if marketing_hits:
        failures.append("md:forbidden_marketing")

    baseline_ok = False
    baseline_detail: dict[str, Any] = {}
    if BASELINE_SUMMARY.is_file():
        summary = _load(BASELINE_SUMMARY)
        baseline_ok = summary.get("ok_streak_lifecycle_and_ops_memory", 0) >= 4
        baseline_detail = {
            "ok_streak": summary.get("ok_streak_lifecycle_and_ops_memory"),
            "ready_for_customer_pilot": summary.get("ready_for_customer_pilot"),
        }
    checks.append({"id": "internal_baseline_streak", "ok": baseline_ok, "detail": baseline_detail})
    if not baseline_ok:
        failures.append("internal_baseline_streak")

    engineering_pass = not failures
    ready_external = engineering_pass and onepager.get("legal_review_status") not in (None, "PENDING")

    report = {
        "schema": "agent_handoff_governance_public_facing_scan_v1",
        "generated_at_utc": _utc_now(),
        "public_facing_checklist": PUBLIC_FACING_REF,
        "engineering_cross_check_pass": engineering_pass,
        "ready_for_external_send": ready_external,
        "legal_review_status": onepager.get("legal_review_status"),
        "distribution": onepager.get("distribution"),
        "checks": checks,
        "failures": failures,
        "boundary_ack": (
            "Engineering scan only — counsel sign-off required before external send; "
            "not Track A·live·compression API merge"
        ),
    }

    if not args.stdout_only:
        out_path = SCRIPT_ROOT / args.out_json
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.stdout_only:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"WROTE: {SCRIPT_ROOT / args.out_json}")
        print(f"engineering_cross_check_pass: {engineering_pass}")
        print(f"ready_for_external_send: {ready_external}")

    return 0 if engineering_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
