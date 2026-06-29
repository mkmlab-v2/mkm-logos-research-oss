#!/usr/bin/env python3
"""Build NotebookLM upload pack for COMPRESSION_BTRACK (B-track compression research lane).

SSOT: docs/NotebookLM_sources_manifest.md · build_notebooklm_lens_source_packs_v1.py COMPRESSION_BTRACK list
Output: reports/notebooklm_compression_btrack_sync_pack_v1/
"""
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "notebooklm_compression_btrack_sync_pack_v1"
NOTEBOOK_NAME = "23_COMPRESSION_BTRACK_2026Q2"
NOTEBOOK_MCP_ID = "23-compression-btrack-2026q2"

PACK_SOURCES: list[str] = [
    "reports/constitution/btrack_pilot/comp_atom_track_b_closure_v1.json",
    "reports/constitution/btrack_pilot/comp_atom02_pointer_research_brief_v1.json",
    "reports/constitution/btrack_pilot/comp_atom02_pointer_feasibility_summary_v1.json",
    "reports/constitution/btrack_pilot/comp_anchor05_verse_pool_full_scan_v1.json",
    "reports/constitution/btrack_pilot/comp_anchor06_registry_codebook_bridge_v1.json",
    "reports/constitution/btrack_pilot/comp_anchor06_top_verse_pools_v1.json",
    "reports/constitution/btrack_pilot/comp_compression_lane_handoff_v1.json",
    "reports/constitution/btrack_pilot/comp_cross_chat_achievement_index_v1.json",
    "reports/constitution/btrack_pilot/comp_atom05_bridge_boost_per_case_delta_v1.json",
    "reports/constitution/btrack_pilot/comp_anchor07_wire_atom_candidates_v1.json",
    "reports/constitution/btrack_pilot/comp_atom05_profile_matrix_brief_v1.json",
    "reports/constitution/btrack_pilot/comp_atom05_compare_prior_v1.json",
    "reports/constitution/btrack_pilot/comp_anchor07_registry_seed_mapping_poc_v1.json",
    "reports/constitution/btrack_pilot/comp_anchor08_seed_curation_queue_v1.json",
    "reports/constitution/btrack_pilot/comp_anchor08_seed_curation_applied_v1.json",
    "reports/constitution/btrack_pilot/comp_nl_manual_upload_manifest_v1.json",
    "reports/constitution/btrack_pilot/comp_atom05_bridge_boost_detail_v1.json",
    "reports/constitution/btrack_pilot/comp_atom05_full_v2_sweep_v1.json",
    "reports/constitution/btrack_pilot/comp_atom01_ab_summary_v1.json",
    "reports/constitution/btrack_pilot/comp_ijeoma_b7_manifest_closure_v1.json",
    "docs/final/COMPRESSION_INTERPRETATION_PIPELINE_FACT_LOCK_2026-03-31.md",
    "docs/final/COMPRESSION_SLA_POLICY_V1.md",
    # B2B commercial proof (Track A bench ≠ prospect PoC · research_only boundaries)
    "docs/final/artifacts/compression_b2b_recommended_workflow_v1.json",
    "docs/final/artifacts/compression_b2b_pilot_roi_report_v1_latest.json",
    "docs/final/artifacts/compression_public_reproduce_pack_v1_latest.json",
]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_boundary_snippet(dest: Path) -> None:
    lines = [
        "# COMPRESSION_BTRACK NL corpus boundary (B-track · research_only · non-SSOT snippet)",
        "",
        f"generated_utc: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        f"target_notebook: {NOTEBOOK_NAME}",
        "data_lane: compression_btrack",
        "boundary: NL is briefing only; gates·KPI·paths = CONSTITUTION + scripts + exit code.",
        "",
        "## Purpose",
        "- B-track compression R&D: anchor·atom·pointer·CJK bench handoffs",
        "- `[HYPO]` · `research_only` — no auto-merge to Track A or live trading",
        "",
        "## NEVER cross-cite in this notebook (No Cross-Talk)",
        "- Track A MS headline **47.5% / ~0.890** as production claim without active report + sign-off",
        "- mkmlife MAI · physician_gold SOAP · consumer_survey_only full paste",
        "- Track C 사업계획·명리·성경 렌즈 원본을 Track A 승격 근거로 사용",
        "- NotebookLM answer alone as **live trading GO**",
        "",
        "## Track A vs B (FAIL-COMP-004)",
        "- Track A: `22_ACODEAI_MKM_CORE_FACT_2026Q2` — inter-agent wire·SLA only",
        "- Track B: this notebook — ultra-literal·universal matrix·CJK are **research** until human promotion",
        "",
        "## Pointers",
        "- Lane handoff: reports/constitution/btrack_pilot/comp_compression_lane_handoff_v1.json",
        "- Cross-chat index: comp_cross_chat_achievement_index_v1.json",
        "- Vault mirror: scripts/push_lens_packs_to_vault_v1.py",
    ]
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    missing: list[str] = []
    file_meta: list[dict] = []

    _write_boundary_snippet(OUT / "00_compression_btrack_lane_boundary_snippet.md")
    copied.append("00_compression_btrack_lane_boundary_snippet.md")
    file_meta.append(
        {
            "name": "00_compression_btrack_lane_boundary_snippet.md",
            "repo_path": "(generated)",
            "sha256": _sha256(OUT / "00_compression_btrack_lane_boundary_snippet.md"),
            "bytes": (OUT / "00_compression_btrack_lane_boundary_snippet.md").stat().st_size,
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

    url_file = ROOT / "reports" / "notebooklm_compression_btrack_notebook_url_v1.txt"
    notebook_url = url_file.read_text(encoding="utf-8").strip() if url_file.is_file() else ""

    index = {
        "schema": "notebooklm_compression_btrack_sync_pack_v1",
        "version": "1.0.0",
        "notebook_name": NOTEBOOK_NAME,
        "notebook_mcp_id": NOTEBOOK_MCP_ID,
        "notebook_url": notebook_url,
        "synced_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_count_target": "22-24 logical",
        "data_lane": "compression_btrack",
        "files": sorted(copied),
        "files_meta": file_meta,
        "missing_repo_paths": missing,
        "setup_steps": [
            f"nlm notebook create {NOTEBOOK_NAME}",
            "URL → reports/notebooklm_compression_btrack_notebook_url_v1.txt",
            "py scripts/register_notebooklm_compression_btrack_mcp_v1.py",
            "py scripts/build_notebooklm_compression_btrack_sync_pack_v1.py",
            "py scripts/push_notebooklm_compression_btrack_pack_nlm_v1.py",
            "powershell -File scripts/notebooklm_dedupe_sources_by_title.ps1 -NotebookId <uuid> -Confirm",
            "py scripts/prune_notebooklm_compression_btrack_sources_v1.py --what-if",
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
