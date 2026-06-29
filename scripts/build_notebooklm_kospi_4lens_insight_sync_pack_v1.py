#!/usr/bin/env python3
"""Build NotebookLM upload pack — KOSPI B-track 4-lens + MKM 4AI insight [HYPO].

Output: reports/notebooklm_kospi_4lens_insight_sync_pack_v1/
URL SSOT: reports/notebooklm_kospi_4lens_insight_notebook_url_v1.txt
"""
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "notebooklm_kospi_4lens_insight_sync_pack_v1"
NOTEBOOK_NAME = "KOSPI_BTRACK_4LENS_MKM4AI_INSIGHT"
NOTEBOOK_MCP_ID = "kospi-btrack-4lens-mkm4ai-insight"

PACK_SOURCES: list[str] = [
    "docs/final/LENS_UTILIZATION_CHARTER_V1.md",
    "docs/final/MKM_LENS_GLOBAL_PROFILE_PROMPT_RAG_INSTRUCTIONS_DRAFT_V1.md",
    "docs/final/LOGOS_NOTEBOOK_META_GUIDE.md",
    "data/commander/kospi_june2026_prophecy_evolution_v1.json",
    "reports/kospi_june2026_4ai_prophecy_report_latest.md",
    "reports/kospi_june2026_prophecy_document_v1.md",
    "reports/premium_btrack_multilens_report_v1.md",
    "reports/kospi_briefing_vs_scoring_lane_compare_v1_latest.json",
    "reports/kospi_june2026_oos_significance_v1_latest.json",
    "reports/kospi_june2026_4ai_lock_unlock_hr_cross_v1_latest.json",
    "reports/kospi_june2026_conditional_unlock_shadow_v1_latest.json",
    "reports/kospi_june2026_unlock_diff_macro_panel_v1_latest.json",
    "reports/kospi_june2026_daily_miss_insight_v1_latest.json",
    "reports/kospi_june2026_evening_miss_insight_chain_v1_latest.json",
    "reports/kospi_june2026_per_date_lens_counterfactual_latest.json",
    "reports/kospi_evening_briefing_chain_v1_latest.json",
    "reports/kospi_lens_ablation_backtest_walkforward_latest.json",
    "docs/final/artifacts/myeongni_independent_lens_latest.json",
    "docs/final/artifacts/sasang_independent_lens_latest.json",
    "docs/final/artifacts/logos_independent_lens_latest.json",
    "reports/btrack_science_core_per_date_kospi_v1.jsonl",
]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_boundary_snippet(dest: Path) -> None:
    lines = [
        "# KOSPI B-track 4-lens + MKM 4AI insight NL boundary [HYPO · research_only]",
        "",
        f"generated_utc: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        f"target_notebook: {NOTEBOOK_NAME}",
        "data_lane: kospi_btrack_4lens_mkm4ai",
        "boundary: NL = briefing·통찰 only; gates·HR·paths = CONSTITUTION + scripts + exit code.",
        "",
        "## Purpose",
        "- 4렌즈(사상·명리·성경·Science) 병렬 + MKM 4AI(태양/소양/태음/소음) 조율 통찰",
        "- briefing_lane vs scoring_shadow **분리** — direction_merge 금지",
        "- unlock/conditional shadow = 연구 PoC; auto_apply·Track A 금지",
        "",
        "## Lens roles (MKM contract)",
        "- 성경(Logos): `[NON_GATING]` 거시 해설·앵커 only",
        "- 명리: 중기 방향 · 사상: 단기 강도 · Science@finance: per-date",
        "- 4AI: Absolute Balance Coordinator Mode (제5 AI 아님)",
        "",
        "## NEVER cross-cite",
        "- NotebookLM alone as live trading GO or Track A promotion",
        "- unlock shadow HR as production claim without Wilson/significance artifact",
        "- merge briefing_four_lens into scoring_shadow headline",
        "",
        "## Key artifacts in this pack",
        "- 4AI report MD · premium multilens · lane compare · lock/unlock cross",
        "- 6/26 FAIL miss insight · per-date lens counterfactual",
    ]
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    missing: list[str] = []
    file_meta: list[dict] = []

    _write_boundary_snippet(OUT / "00_kospi_4lens_mkm4ai_lane_boundary_snippet.md")
    copied.append("00_kospi_4lens_mkm4ai_lane_boundary_snippet.md")
    file_meta.append(
        {
            "name": "00_kospi_4lens_mkm4ai_lane_boundary_snippet.md",
            "repo_path": "(generated)",
            "sha256": _sha256(OUT / "00_kospi_4lens_mkm4ai_lane_boundary_snippet.md"),
            "bytes": (OUT / "00_kospi_4lens_mkm4ai_lane_boundary_snippet.md").stat().st_size,
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

    url_file = ROOT / "reports" / "notebooklm_kospi_4lens_insight_notebook_url_v1.txt"
    notebook_url = url_file.read_text(encoding="utf-8").strip() if url_file.is_file() else ""

    index = {
        "schema": "notebooklm_kospi_4lens_insight_sync_pack_v1",
        "version": "1.0.0",
        "notebook_name": NOTEBOOK_NAME,
        "notebook_mcp_id": NOTEBOOK_MCP_ID,
        "notebook_url": notebook_url,
        "synced_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "data_lane": "kospi_btrack_4lens_mkm4ai",
        "research_only": True,
        "send_gate": "HOLD",
        "files": sorted(copied),
        "files_meta": file_meta,
        "missing_repo_paths": missing,
        "reproduce": [
            "py scripts/build_notebooklm_kospi_4lens_insight_sync_pack_v1.py",
            "py scripts/push_notebooklm_kospi_4lens_insight_pack_nlm_v1.py",
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
    return 0 if not missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
