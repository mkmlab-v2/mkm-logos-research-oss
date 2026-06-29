#!/usr/bin/env python3
"""Pre-meeting readiness gate for Logos Graph Studio B2B pilot pack (local + live smoke JSON)."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_MD = [
    "docs/final/artifacts/logos_graph_studio_b2b_poc_one_pager_v1_latest.md",
    "docs/final/artifacts/logos_graph_studio_pilot_sow_executive_summary_v1_latest.md",
    "docs/final/artifacts/logos_graph_studio_pilot_sow_template_v1_latest.md",
    "docs/final/artifacts/logos_graph_studio_b2b_30s_demo_script_v1_latest.md",
    "docs/final/artifacts/logos_graph_studio_b2b_live_rehearsal_checklist_v1_latest.md",
    "docs/final/artifacts/logos_gtm_linkedin_b2b_copy_variants_v1_latest.md",
    "docs/final/artifacts/logos_gtm_counsel_handoff_brief_v1_latest.md",
    "docs/final/artifacts/logos_graph_studio_organic_b2b_outreach_v1_latest.md",
]

REQUIRED_JSON = [
    "docs/final/artifacts/logos_graph_studio_commander_pilot_approval_v1_latest.json",
]

LIVE_REPORTS = [
    "reports/logos_graph_studio_b2b_rehearsal_live_v1_latest.json",
    "reports/logos_jema_ai_deploy_verify_latest.json",
    "reports/logos_trace_public_check_v1_latest.json",
]

COPY_SCAN_REPORTS = [
    "reports/logos_gtm_linkedin_b2b_copy_scan_v1_latest.json",
    "reports/logos_research_public_docs_copy_scan_v1_latest.json",
    "reports/logos_gtm_counsel_handoff_bundle_v1_latest.json",
]

FORBIDDEN_IN_ONEPAGER = [
    re.compile(r"[A-Za-z]:\\workspace", re.I),
    re.compile(r"ready_for_external_send:\s*true", re.I),
]

COPY_MARKERS = [
    "NON_GATING",
    "send_gate",
    "HOLD",
    "research_only",
]


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--out-json",
        default="reports/logos_graph_studio_b2b_meeting_pack_readiness_v1_latest.json",
    )
    args = ap.parse_args()

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    checks: list[dict[str, Any]] = []
    missing: list[str] = []

    for rel in REQUIRED_MD + REQUIRED_JSON:
        ok = (ROOT / rel).is_file()
        checks.append({"id": f"file:{rel}", "ok": ok})
        if not ok:
            missing.append(rel)

    approval = _load(ROOT / "docs/final/artifacts/logos_graph_studio_commander_pilot_approval_v1_latest.json")
    commander_ok = bool(approval.get("commander_signoff")) and bool(
        approval.get("ready_for_internal_b2b_pilot")
    )
    send_hold_ok = approval.get("send_gate") == "HOLD" and approval.get("ready_for_external_send") is False
    checks.append({"id": "commander_pilot_approval", "ok": commander_ok and send_hold_ok})

    one_pager = (
        ROOT / "docs/final/artifacts/logos_graph_studio_b2b_poc_one_pager_v1_latest.md"
    ).read_text(encoding="utf-8") if (ROOT / "docs/final/artifacts/logos_graph_studio_b2b_poc_one_pager_v1_latest.md").is_file() else ""
    leak_hits = [p.pattern for p in FORBIDDEN_IN_ONEPAGER if p.search(one_pager)]
    checks.append({"id": "one_pager:no_leaks", "ok": not leak_hits, "patterns_matched": leak_hits})
    one_pager_markers_ok = all(m in one_pager for m in COPY_MARKERS)
    checks.append({"id": "one_pager:compliance_markers", "ok": one_pager_markers_ok})

    live_ok = True
    for rel in LIVE_REPORTS:
        doc = _load(ROOT / rel)
        ok = bool(doc.get("ok"))
        checks.append({"id": f"live:{rel}", "ok": ok})
        if not ok:
            live_ok = False

    scan_reports_ok = True
    for rel in COPY_SCAN_REPORTS:
        doc = _load(ROOT / rel)
        ok = bool(doc.get("scan_ok") if "scan_ok" in doc else doc.get("ready_for_counsel_submission"))
        checks.append({"id": f"copy:{rel}", "ok": ok})
        if not ok:
            scan_reports_ok = False

    ready_internal = (
        not missing
        and commander_ok
        and send_hold_ok
        and not leak_hits
        and one_pager_markers_ok
        and scan_reports_ok
        and live_ok
    )

    report = {
        "schema": "logos_graph_studio_b2b_meeting_pack_readiness_v1",
        "generated_at_utc": generated_at,
        "ready_for_internal_b2b_meeting": ready_internal,
        "ready_for_external_send": False,
        "send_gate": "HOLD",
        "commander_signoff": commander_ok,
        "missing_files": missing,
        "demo_primary_url": approval.get("demo_primary_url")
        or "https://api.jemaai.cloud/public_showroom_meaning_topology_qa_v2.html?preset=job_job_suffering_reason",
        "commercial_workspace_url": approval.get("commercial_workspace_url")
        or "https://logos.jema-ai.com/logos-research",
        "checks": checks,
        "reproduce": "py scripts/check_logos_graph_studio_b2b_meeting_pack_readiness_v1.py",
    }

    out_path = ROOT / args.out_json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ready_internal, "out": str(out_path)}, ensure_ascii=False))
    return 0 if ready_internal else 1


if __name__ == "__main__":
    raise SystemExit(main())
