#!/usr/bin/env python3
"""Build slim NotebookLM upload pack for JEMA-AI Clinician (physician_gold lane).

SSOT: docs/NotebookLM_sources_manifest.md — CLINICIAN_PHYSICIAN_GOLD row
Output: reports/notebooklm_clinician_sync_pack_v1/
"""
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "notebooklm_clinician_sync_pack_v1"
NOTEBOOK_NAME = "20_CLINICIAN_PHYSICIAN_GOLD_2026Q2"
NOTEBOOK_MCP_ID = "20-clinician-physician-gold-20"

PACK_SOURCES: list[str] = [
    "docs/final/MKM_DOMAIN_CLINICAL_LANE_V1.md",
    "docs/final/CLINIC_CONSTITUTION_MVP_V1.md",
    "docs/final/JEMA_AI_DOMAIN_POINTER_V1.md",
    "docs/final/MKM_HEALTH_WELLNESS_COPY_GUARDRAILS_KR_V1.md",
    "docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md",
    "docs/final/artifacts/clinic_constitution_dual_lane_policy_v1.json",
    "docs/final/artifacts/han_clinic_owner_onboarding_brief_v1_latest.md",
    "docs/final/artifacts/patient_care_bundle_generation_policy_v1.default.json",
    "docs/final/schemas/patient_care_bundle_v1.schema.json",
    "docs/final/schemas/clinic_constitution_mvp_capture_v1.schema.json",
]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_boundary_snippet(dest: Path) -> None:
    lines = [
        "# Clinician NL corpus boundary (physician_gold · non-SSOT snippet)",
        "",
        f"generated_utc: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        f"target_notebook: {NOTEBOOK_NAME}",
        "data_lane: physician_gold",
        "boundary: NL is briefing only; clinical gates·paths = CONSTITUTION §9 + scripts + exit code.",
        "",
        "## Purpose",
        "- B2B 한의사 진료 보조: SOAP · CDSS · care bundle · 원장 확정 4진",
        "- Surface: app.jema-ai.com/clinician · clinic.no1kmedi.com/clinician",
        "- Repo: projects/no1kmedi + clinic scripts under scripts/",
        "",
        "## NEVER cross-cite in this notebook (No Cross-Talk)",
        "- mkmlife.com / consumer_survey_only / MAI 카드 / 14문항 설문",
        "- Track A compression KPI (47.5%·0.890) as clinical evidence",
        "- B-track [HYPO] as diagnosis or prescription trigger",
        "- consumer↔physician 일치율 (N≥20 전 대외 주장 금지)",
        "- **00_OPS_지휘부 / ops command pack auto-merge 금지** (A4 gate: check_notebooklm_clinician_no_ops_merge_v1.py)",
        "",
        "## Implementation pointers (Fact-Lock)",
        "- Turn JSON: scripts/build_han_physician_clinical_assist_turn_v1.py",
        "- Care bundle: scripts/Invoke-PatientCareBundleAssemblePatientFacing_v1.ps1",
        "- Clinic ledger: scripts/clinic_constitution_mvp_ledger_v1.py",
        "- Dual lane policy: docs/final/artifacts/clinic_constitution_dual_lane_policy_v1.json",
        "- Owner onboarding (Dual-Entry A/B): docs/final/artifacts/han_clinic_owner_onboarding_brief_v1_latest.md",
        "",
        "## Cursor agent guard (summary)",
        "1. No Cross-Talk: do not Read consumer/mkmlife copy into clinician answers.",
        "2. Exa/external web: refine to *.pack.json or guideline MD before add_source here.",
        "3. Main merge: DailyOpsPatrol + human sign-off before Track A / production copy.",
        "",
        "## NL smoke question (after push)",
        '- "MAI를 임상 진단으로 써도 되나?" → must refuse; cite consumer_survey_only boundary.',
    ]
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    missing: list[str] = []
    file_meta: list[dict] = []

    _write_boundary_snippet(OUT / "00_clinician_lane_boundary_snippet.md")
    copied.append("00_clinician_lane_boundary_snippet.md")
    file_meta.append(
        {
            "name": "00_clinician_lane_boundary_snippet.md",
            "repo_path": "(generated)",
            "sha256": _sha256(OUT / "00_clinician_lane_boundary_snippet.md"),
            "bytes": (OUT / "00_clinician_lane_boundary_snippet.md").stat().st_size,
        }
    )

    for rel in PACK_SOURCES:
        src = ROOT / rel.replace("\\", "/")
        if not src.is_file():
            missing.append(rel)
            continue
        dest = OUT / src.name
        shutil.copy2(src, dest)
        copied.append(dest.name)
        file_meta.append(
            {
                "name": dest.name,
                "repo_path": rel.replace("\\", "/"),
                "sha256": _sha256(dest),
                "bytes": dest.stat().st_size,
            }
        )

    notebook_url = (
        (ROOT / "reports" / "notebooklm_clinician_notebook_url_v1.txt").read_text(encoding="utf-8").strip()
        if (ROOT / "reports" / "notebooklm_clinician_notebook_url_v1.txt").is_file()
        else ""
    )

    index = {
        "schema": "notebooklm_clinician_sync_pack_v1",
        "version": "1.0.0",
        "notebook_name": NOTEBOOK_NAME,
        "notebook_mcp_id": NOTEBOOK_MCP_ID,
        "notebook_url": notebook_url or "(NL web: create notebook → save URL to reports/notebooklm_clinician_notebook_url_v1.txt)",
        "synced_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_count_target": "8-12 logical · expect NL chunk inflation on large MD",
        "data_lane": "physician_gold",
        "ops_auto_merge_forbidden": True,
        "forbidden_ops_source_fragments": [
            "00_OPS",
            "notebooklm_ops_command",
            "MISSION_LOG",
            "mkm_chat_resume_pack",
        ],
        "files": sorted(copied),
        "files_meta": file_meta,
        "missing_repo_paths": missing,
        "setup_steps": [
            f"NL web: + 새 노트 → 이름 {NOTEBOOK_NAME}",
            "Share URL → reports/notebooklm_clinician_notebook_url_v1.txt (one line)",
            "MCP: add_notebook → select_notebook 20-clinician-physician-gold-20 (register_notebooklm_clinician_mcp_v1.py)",
            "py scripts/build_notebooklm_clinician_sync_pack_v1.py",
            "py scripts/push_notebooklm_clinician_pack_nlm_v1.py",
            "powershell -File scripts/notebooklm_dedupe_sources_by_title.ps1 -NotebookId f9503fe6-d53d-4981-9094-874aa6baa76b -Confirm",
            "py scripts/prune_notebooklm_clinician_sources_v1.py --what-if then without --what-if",
        ],
    }
    (OUT / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {"out": str(OUT), "copied": len(copied), "missing": missing, "notebook_url_set": bool(notebook_url)},
            ensure_ascii=False,
        )
    )
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
