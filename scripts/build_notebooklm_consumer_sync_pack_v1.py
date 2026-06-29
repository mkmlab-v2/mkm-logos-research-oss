#!/usr/bin/env python3
"""Build slim NotebookLM upload pack for MKMLIFE Consumer (consumer_survey_only lane).

SSOT: docs/NotebookLM_sources_manifest.md — MKMLIFE_CONSUMER_SURVEY row
Output: reports/notebooklm_consumer_sync_pack_v1/
"""
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "notebooklm_consumer_sync_pack_v1"
NOTEBOOK_NAME = "21_MKMLIFE_CONSUMER_SURVEY_2026Q2"
NOTEBOOK_MCP_ID = "21-mkmlife-consumer-survey-202"

PACK_SOURCES: list[str] = [
    "docs/final/MKM_DOMAIN_CLINICAL_LANE_V1.md",
    "docs/final/MKM_DOMAIN_PORTFOLIO_POINTER_V1.md",
    "docs/final/CLINIC_CONSTITUTION_MVP_V1.md",
    "docs/final/NO1KMEDI_MKMLIFE_REPO_PATH_SSOT_2026-04-08.md",
    "docs/final/MKM_HEALTH_WELLNESS_COPY_GUARDRAILS_KR_V1.md",
    "docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md",
    "docs/final/NOTEBOOKLM_MKMLIFE_NEWS_QUESTION_STARTER_BUNDLE_2026-04-12.md",
    "docs/final/artifacts/clinic_constitution_dual_lane_policy_v1.json",
    "docs/final/artifacts/clinic_constitution_survey_item_bank_v1.json",
    "docs/final/schemas/clinic_constitution_survey_pack_public_v1.schema.json",
    "docs/final/artifacts/gtm_mai_copy_bundles_v1.json",
]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_boundary_snippet(dest: Path) -> None:
    lines = [
        "# Consumer NL corpus boundary (consumer_survey_only · non-SSOT snippet)",
        "",
        f"generated_utc: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        f"target_notebook: {NOTEBOOK_NAME}",
        "data_lane: consumer_survey_only",
        "boundary: NL is briefing only; product gates·paths = CONSTITUTION + scripts + exit code.",
        "",
        "## Purpose",
        "- B2C mkmlife.com: One-Question Premium · 14문항 설문 · MAI 성향 카드",
        "- Surface: mkmlife.com /ask-one · repo submodule projects/mkm/mkm-life",
        "- API: /api/v1/constitution/survey/* · lookup_gtm_mai_archetype_v1.py",
        "",
        "## NEVER cross-cite in this notebook (No Cross-Talk)",
        "- physician_gold / SOAP / CDSS / care bundle / 원장 확정 4진",
        "- app.jema-ai.com/clinician · clinic.no1kmedi.com/clinician 임상 워크플로",
        "- Track A compression KPI (47.5%·0.890) as product or clinical evidence",
        "- consumer↔physician 일치율 (N≥20 전 대외 주장 금지)",
        "- MAI·설문을 **진단·처방·치료**로 표기",
        "",
        "## Implementation pointers (Fact-Lock)",
        "- Score: scripts/score_clinic_constitution_survey_v1.py",
        "- Append: scripts/append_clinic_consumer_survey_capture_v1.py",
        "- MAI lookup: scripts/lookup_gtm_mai_archetype_v1.py",
        "- Dual lane: docs/final/artifacts/clinic_constitution_dual_lane_policy_v1.json",
        "- UI badges §10: NO1KMEDI_MKMLIFE_REPO_PATH_SSOT §10–§11",
        "",
        "## Cursor agent guard (summary)",
        "1. No Cross-Talk: do not Read physician/clinician SOAP into consumer answers.",
        "2. B-track news starters: research_only; no investment·war prophecy tone.",
        "3. Main merge: human sign-off before mkmlife production copy changes.",
        "",
        "## NL smoke question (after push)",
        '- "SOAP care bundle을 mkmlife 사용자에게 그대로 써도 되나?" → must refuse; cite physician_gold boundary.',
        '- "MAI는 임상 진단인가?" → must refuse; MAI is reference-only, not MBTI® official.',
    ]
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    missing: list[str] = []
    file_meta: list[dict] = []

    _write_boundary_snippet(OUT / "00_consumer_lane_boundary_snippet.md")
    copied.append("00_consumer_lane_boundary_snippet.md")
    file_meta.append(
        {
            "name": "00_consumer_lane_boundary_snippet.md",
            "repo_path": "(generated)",
            "sha256": _sha256(OUT / "00_consumer_lane_boundary_snippet.md"),
            "bytes": (OUT / "00_consumer_lane_boundary_snippet.md").stat().st_size,
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

    url_file = ROOT / "reports" / "notebooklm_consumer_notebook_url_v1.txt"
    notebook_url = url_file.read_text(encoding="utf-8").strip() if url_file.is_file() else ""

    index = {
        "schema": "notebooklm_consumer_sync_pack_v1",
        "version": "1.0.0",
        "notebook_name": NOTEBOOK_NAME,
        "notebook_mcp_id": NOTEBOOK_MCP_ID,
        "notebook_url": notebook_url
        or "(NL web: nlm notebook create → save URL to reports/notebooklm_consumer_notebook_url_v1.txt)",
        "synced_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_count_target": "10-12 logical · expect NL chunk inflation on large MD",
        "data_lane": "consumer_survey_only",
        "files": sorted(copied),
        "files_meta": file_meta,
        "missing_repo_paths": missing,
        "setup_steps": [
            f"nlm notebook create {NOTEBOOK_NAME}",
            "Share URL → reports/notebooklm_consumer_notebook_url_v1.txt",
            "MCP: py scripts/register_notebooklm_consumer_mcp_v1.py",
            "py scripts/build_notebooklm_consumer_sync_pack_v1.py",
            "py scripts/push_notebooklm_consumer_pack_nlm_v1.py",
            "py scripts/prune_notebooklm_consumer_sources_v1.py --what-if then without --what-if",
        ],
    }
    (OUT / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "out": str(OUT),
                "copied": len(copied),
                "missing": missing,
                "notebook_url_set": bool(notebook_url),
            },
            ensure_ascii=False,
        )
    )
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
