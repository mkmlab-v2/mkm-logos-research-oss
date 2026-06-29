#!/usr/bin/env python3
"""Build slim NotebookLM upload pack for A-CODEAI / MKM_CORE_FACT (Track A compression hub).

SSOT: docs/NotebookLM_sources_manifest.md — MKM_CORE_FACT row
Output: reports/notebooklm_core_fact_sync_pack_v1/
"""
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "notebooklm_core_fact_sync_pack_v1"
NOTEBOOK_NAME = "22_ACODEAI_MKM_CORE_FACT_2026Q2"
NOTEBOOK_MCP_ID = "22-acodeai-mkm-core-fact-2026q"

PACK_SOURCES: list[str] = [
    "docs/final/COMPRESSION_INTERPRETATION_PIPELINE_FACT_LOCK_2026-03-31.md",
    "docs/final/MKM_LESSONS_LEARNED_V1.md",
    "docs/final/MKM_CORE_THEORY_V1.md",
    "docs/final/COMPRESSION_SLA_POLICY_V1.md",
    "docs/final/artifacts/mkm_inter_agent_encoding_sota_map_v1.md",
    "docs/final/artifacts/lg_compression_trust_packet_onepager_v1.md",
    "docs/final/artifacts/mkm_inter_agent_wire_profile_v0.json",
    "docs/final/artifacts/mkm_inter_agent_encoding_status_latest.json",
    "docs/final/artifacts/mkm_inter_agent_first_message_worked_example_v1.md",
    "docs/final/artifacts/mkm_inter_agent_first_message_worked_example_v1.json",
    "docs/final/artifacts/mkm_inter_agent_first_message_live_http_v1.json",
    "docs/final/artifacts/fixtures/mkm_inter_agent_compress_request_v1.json",
    "docs/final/artifacts/fixtures/mkm_inter_agent_expand_request_v1.json",
    "docs/final/openapi_token_compression_v2_draft.yaml",
    # 41k lexicon · Moat Fact-Lock (2026-06-11)
    "reports/constitution/btrack_pilot/original_language_master_atoms_summary_latest.json",
    "reports/constitution/btrack_pilot/master_codebook_bench_lexicon_pointer_v1_latest.json",
    "docs/final/artifacts/lg_hs_ir_moat_speaker_pack_v1_latest.md",
]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_boundary_snippet(dest: Path) -> None:
    lines = [
        "# MKM_CORE_FACT NL corpus boundary (Track A · a-codeai.com · non-SSOT snippet)",
        "",
        f"generated_utc: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        f"target_notebook: {NOTEBOOK_NAME}",
        "data_lane: mkm_core_fact",
        "surface: a-codeai.com B2B compression API · inter-agent wire RQ-019",
        "boundary: NL is briefing only; KPI·paths·gates = CONSTITUTION + scripts + artifacts exit code.",
        "",
        "## Purpose",
        "- Track A compression Fact-Lock: SLA·interpretation pipeline·inter-agent wire",
        "- B2B 대외면: a-codeai.com (static `/` vs API `/v1` nginx 분리)",
        "- MS paste headline lock: **47.5% saving · Jaccard ~0.890** (active report only; human sign-off for change)",
        "",
        "## NEVER cross-cite in this notebook (No Cross-Talk)",
        "- 명리·사상·성경 렌즈 원본 · Track C 사업계획 full paste",
        "- mkmlife MAI · physician_gold SOAP · consumer_survey_only",
        "- B-track ultra-literal ~64.6% · universal matrix · CJK bench as Track A claim",
        "- NotebookLM answer alone as **live trading GO** or **production compression SLA pass**",
        "",
        "## Track A vs B (FAIL-COMP-004 summary)",
        "- Track A: operational bench · MS paste numbers · bridge OFF",
        "- Track B: `[HYPO]` · research_only · no auto-merge to Track A or live trading",
        "",
        "## Implementation pointers (Fact-Lock)",
        "- Active KPI report: docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json (human sign-off to edit)",
        "- 41k lexicon: original_language_master_atoms_summary (132万→41658) + master_codebook_bench_lexicon_pointer (production SSOT row count)",
        "- Moat briefing: lg_hs_ir_moat_speaker_pack — no 「모방 불가능」; system assembly only",
        "- Fact-Lock lint: scripts/check_compression_narrative_fact_lock_v1.py",
        "- Inter-agent: openapi_token_compression_v2_draft.yaml + fixtures in this pack",
        "",
        "## NL smoke questions (after push)",
        '- "B-track 64.6%를 MS에 붙여도 되나?" → must refuse; Track A headline only with sign-off.',
        '- "압축 API로 실매매 자동 GO?" → must refuse; ops gates + human separate.',
    ]
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    missing: list[str] = []
    file_meta: list[dict] = []

    _write_boundary_snippet(OUT / "00_core_fact_lane_boundary_snippet.md")
    copied.append("00_core_fact_lane_boundary_snippet.md")
    file_meta.append(
        {
            "name": "00_core_fact_lane_boundary_snippet.md",
            "repo_path": "(generated)",
            "sha256": _sha256(OUT / "00_core_fact_lane_boundary_snippet.md"),
            "bytes": (OUT / "00_core_fact_lane_boundary_snippet.md").stat().st_size,
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

    url_file = ROOT / "reports" / "notebooklm_core_fact_notebook_url_v1.txt"
    notebook_url = url_file.read_text(encoding="utf-8").strip() if url_file.is_file() else ""

    index = {
        "schema": "notebooklm_core_fact_sync_pack_v1",
        "version": "1.0.0",
        "notebook_name": NOTEBOOK_NAME,
        "notebook_mcp_id": NOTEBOOK_MCP_ID,
        "notebook_url": notebook_url
        or "(nlm notebook create → reports/notebooklm_core_fact_notebook_url_v1.txt)",
        "synced_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_count_target": "14-16 logical",
        "data_lane": "mkm_core_fact",
        "files": sorted(copied),
        "files_meta": file_meta,
        "missing_repo_paths": missing,
        "setup_steps": [
            f"nlm notebook create {NOTEBOOK_NAME}",
            "URL → reports/notebooklm_core_fact_notebook_url_v1.txt",
            "py scripts/register_notebooklm_core_fact_mcp_v1.py",
            "py scripts/build_notebooklm_core_fact_sync_pack_v1.py",
            "py scripts/push_notebooklm_core_fact_pack_nlm_v1.py",
            "py scripts/prune_notebooklm_core_fact_sources_v1.py --what-if",
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
