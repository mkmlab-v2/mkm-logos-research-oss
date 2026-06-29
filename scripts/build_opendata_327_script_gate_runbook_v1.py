#!/usr/bin/env python3
"""§B script-gate runbook — 10 ordered steps (copy-paste + machine commands)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSON = ROOT / "docs/final/artifacts/opendata_327_script_gate_runbook_v1_latest.json"
DEFAULT_MD = ROOT / "docs/final/artifacts/opendata_327_script_gate_runbook_v1_latest.md"

RUNBOOK: list[dict[str, Any]] = [
    {
        "step": 1,
        "task_id": "327-grep-g1",
        "title": "G1 — LG/47%/OEM 금지어 (B·C·D MD)",
        "command": "py scripts/check_opendata_327_pre_export_gates_v1.py",
        "pass": "exit 0 · all_gates_ok_for_export_draft=true",
        "artifact": "reports/opendata_327_pre_export_gates_latest.json",
    },
    {
        "step": 2,
        "task_id": "327-grep-g2",
        "title": "G2 — 미구현→완료 서술 금지",
        "command": "py scripts/check_opendata_327_submission_forbidden_grep_v1.py --mode shipped",
        "pass": "exit 0 · overview에 shipped-claim 패턴 0건",
        "artifact": "docs/final/artifacts/ai_opendata_challenge_2026_327_business_plan_overview_v1.md",
    },
    {
        "step": 3,
        "task_id": "327-parallel-od1-review",
        "title": "OD1 — overview 금지어",
        "command": "py scripts/check_opendata_327_submission_forbidden_grep_v1.py --mode overview",
        "pass": "exit 0",
        "artifact": "reports/opendata_327_forbidden_grep_latest.json",
    },
    {
        "step": 4,
        "task_id": "327-parallel-od4-review",
        "title": "OD4 — 무결성 = 계획 not shipped",
        "command": "py scripts/check_opendata_327_submission_forbidden_grep_v1.py --mode shipped",
        "pass": "exit 0 (step 2와 동일 스크립트 — 의도적 중복 확인)",
        "artifact": "parallel_lane OD4",
    },
    {
        "step": 5,
        "task_id": "327-fact-technical-ready",
        "title": "technical_ready",
        "command": "py scripts/build_opendata_327_submission_readiness_v1.py",
        "pass": "exit 0 · technical_ready_for_pdf_bundle=true",
        "artifact": "reports/opendata_327_submission_readiness_latest.json",
    },
    {
        "step": 6,
        "task_id": "327-hold-gate-ready",
        "title": "Draft HOLD gate (ready fixture)",
        "command": "py scripts/check_opendata_327_draft_hold_v1.py --input-json tests/fixtures/opendata_327_policy_slot_ready_v1.json",
        "pass": "exit 0 · decision=REVIEW_READY",
        "artifact": "reports/opendata_327_draft_hold_latest.json",
    },
    {
        "step": 7,
        "task_id": "327-fact-forbidden-claims",
        "title": "Fact-Lock — part B/C forbidden",
        "command": "py scripts/check_opendata_327_submission_forbidden_grep_v1.py --mode submission",
        "pass": "exit 0",
        "artifact": "forbidden_in_submission checklist",
    },
    {
        "step": 8,
        "task_id": "327-doc-doc-annex-json_field_copy-0",
        "title": "Annex SSOT + Part D gate",
        "command": "py scripts/check_opendata_327_pre_export_gates_v1.py",
        "pass": "G1_D ok · Annex MD exists",
        "artifact": "docs/final/B2G_CONTROL_INTEGRITY_PROPOSAL_ANNEX_V1.md",
        "note": "복붙은 verbatim only — LLM rewrite forbidden",
    },
    {
        "step": 9,
        "task_id": "327-doc-doc-brn-json_field_copy-0",
        "title": "BRN / KSIC SSOT file",
        "command": "py -c \"from pathlib import Path; import sys; p=Path('docs/final/artifacts/business_registration_plan_v1.md'); sys.exit(0 if p.is_file() else 1)\"",
        "pass": "exit 0 · or overview meta has BRN/KSIC if artifact gitignored",
        "artifact": "docs/final/artifacts/business_registration_plan_v1.md",
    },
    {
        "step": 10,
        "task_id": "327-doc-doc-tech-implementation_claim-1",
        "title": "Tech disclosure — no fake patent no.",
        "command": "py scripts/check_opendata_327_submission_forbidden_grep_v1.py --mode tech",
        "pass": "exit 0 · G3 human after real filing",
        "artifact": "docs/final/B2G_TECH_DISCLOSURE_ONEPAGER_PREP_V1.md",
    },
]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def render_md(doc: dict[str, Any]) -> str:
    lines = [
        "# OpenData 327 — §B Script Gate Runbook (10 steps)",
        "",
        f"- generated_at_utc: `{doc['generated_at_utc']}`",
        "- **LLM forbidden** · green all 10 before Lane A",
        "",
        "## One-shot",
        "",
        "```powershell",
        "powershell -NoProfile -File scripts/Run-GrantProposalOpenData327ScriptGateB_v1.ps1",
        "```",
        "",
        "## Checklist",
        "",
    ]
    for row in doc["steps"]:
        lines += [
            f"### {row['step']}/10 · `{row['task_id']}` — {row['title']}",
            "",
            "```powershell",
            row["command"],
            "```",
            "",
            f"**Pass:** {row['pass']}",
            f"**Artifact:** `{row['artifact']}`",
        ]
        if row.get("note"):
            lines.append(f"**Note:** {row['note']}")
        lines.append("")
    lines += [
        "## After Lane A (re-export smoke)",
        "",
        "```powershell",
        "py scripts/check_opendata_327_pre_export_gates_v1.py",
        "py scripts/build_opendata_327_submission_readiness_v1.py",
        "```",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_JSON)
    ap.add_argument("--out-md", type=Path, default=DEFAULT_MD)
    args = ap.parse_args()

    doc = {
        "schema": "opendata_327_script_gate_runbook_v1",
        "generated_at_utc": _now(),
        "research_only": True,
        "step_count": len(RUNBOOK),
        "one_shot_ps1": "scripts/Run-GrantProposalOpenData327ScriptGateB_v1.ps1",
        "steps": RUNBOOK,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.out_md.write_text(render_md(doc), encoding="utf-8")
    print(json.dumps({"ok": True, "out_json": str(args.out_json), "out_md": str(args.out_md)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
