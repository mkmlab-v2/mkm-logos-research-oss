#!/usr/bin/env python3
"""Assemble counsel handoff bundle: copy scans + brief on disk + readiness JSON."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
OUT = ROOT / "reports/logos_gtm_counsel_handoff_bundle_v1_latest.json"

BRIEF = ROOT / "docs/final/artifacts/logos_gtm_counsel_handoff_brief_v1_latest.md"
ORGANIC = ROOT / "docs/final/artifacts/logos_graph_studio_organic_b2b_outreach_v1_latest.md"
GTM_VARIANTS = ROOT / "docs/final/artifacts/logos_gtm_linkedin_b2b_copy_variants_v1_latest.md"
SIGNOFF = ROOT / "docs/final/artifacts/logos_track_l_external_send_signoff_v1_latest.json"

SCAN_SCRIPTS = [
    ("gtm_copy_scan", "scripts/check_logos_gtm_linkedin_b2b_copy_scan_v1.py", []),
    ("public_docs_copy_scan", "scripts/check_logos_research_public_docs_copy_v1.py", []),
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(script: str, extra: list[str] | None = None) -> dict[str, Any]:
    cmd = [PY, str(ROOT / script), *(extra or [])]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return {
        "script": script,
        "exit_code": proc.returncode,
        "ok": proc.returncode == 0,
        "stdout": (proc.stdout or "").strip()[-500:],
        "stderr": (proc.stderr or "").strip()[-300:],
    }


def _load_json(rel: str) -> dict[str, Any]:
    path = ROOT / rel
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", default=str(OUT))
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    for name, script, extra in SCAN_SCRIPTS:
        step = _run(script, extra)
        step["id"] = name
        steps.append(step)

    files_ok = all(
        p.is_file()
        for p in (BRIEF, ORGANIC, GTM_VARIANTS, SIGNOFF)
    )

    signoff = _load_json(str(SIGNOFF.relative_to(ROOT)))
    counsel_present = bool((signoff.get("legal_counsel_signoff") or {}).get("present"))

    scans_ok = all(s["ok"] for s in steps)
    ready_counsel = scans_ok and files_ok and not counsel_present

    report: dict[str, Any] = {
        "schema": "logos_gtm_counsel_handoff_bundle_v1",
        "generated_at_utc": _utc(),
        "send_gate": "HOLD",
        "ready_for_external_send": False,
        "ready_for_counsel_submission": ready_counsel,
        "counsel_signoff_present": counsel_present,
        "public_surfaces": {
            "demo_primary_url": "https://api.jemaai.cloud/public_showroom_meaning_topology_qa_v2.html?preset=job_job_suffering_reason",
            "workspace_url": "https://logos.jema-ai.com/logos-research",
            "public_docs_url": "https://logos.jema-ai.com/logos-research/docs",
            "glossary_url": "https://logos.jema-ai.com/logos-research/docs/glossary",
        },
        "artifact_pointers": {
            "counsel_brief": str(BRIEF.relative_to(ROOT)).replace("\\", "/"),
            "organic_outreach": str(ORGANIC.relative_to(ROOT)).replace("\\", "/"),
            "gtm_variants": str(GTM_VARIANTS.relative_to(ROOT)).replace("\\", "/"),
            "signoff_worksheet": str(SIGNOFF.relative_to(ROOT)).replace("\\", "/"),
            "ltm_research_fact_onepager": (
                "docs/research/nextgen_ltm_knowledge_os/"
                "NEXTGEN_LTM_KNOWLEDGE_OS_FACT_ONEPAGER_V1.md"
            ),
            "ltm_research_slot_report": "reports/nextgen_ltm_research_slot_v1_latest.json",
            "four_forces_fact_onepager": (
                "docs/research/four_forces_sasang_biophysical/"
                "FOUR_FORCES_SASANG_FACT_ONEPAGER_V1.md"
            ),
            "four_forces_lexicon_matrix": (
                "docs/research/four_forces_sasang_biophysical/LEXICON_ALIGNMENT_MATRIX_V1.md"
            ),
            "four_forces_research_slot_report": (
                "reports/four_forces_sasang_research_slot_v1_latest.json"
            ),
        },
        "scan_steps": steps,
        "scan_reports": {
            "gtm": "reports/logos_gtm_linkedin_b2b_copy_scan_v1_latest.json",
            "public_docs": "reports/logos_research_public_docs_copy_scan_v1_latest.json",
        },
        "boundary_ack": "Bundle assembles pre-counsel evidence only; counsel fills signoff JSON.",
        "reproduce": "py scripts/build_logos_gtm_counsel_handoff_bundle_v1.py",
    }

    out_path = Path(args.out_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ready_counsel, "out": str(out_path.relative_to(ROOT)).replace("\\", "/")}))
    return 0 if ready_counsel else 1


if __name__ == "__main__":
    raise SystemExit(main())
