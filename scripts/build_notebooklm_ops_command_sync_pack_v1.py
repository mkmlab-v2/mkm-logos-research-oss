#!/usr/bin/env python3
"""Build slim NotebookLM upload pack for MKM ops command notebook (deterministic).

Purpose: replace deleted 00_MASTER / 10_OPS with a **low-source** 지휘부 notebook (~8–12 files).
SSOT: docs/NotebookLM_sources_manifest.md — OPS_COMMAND_ANCHOR row
Output: reports/notebooklm_ops_command_sync_pack_v1/
"""
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "notebooklm_ops_command_sync_pack_v1"
NOTEBOOK_NAME = "00_OPS_지휘부_2026Q2"
NOTEBOOK_MCP_ID = "00-ops-2026q2"

PACK_SOURCES: list[str] = [
    "AGENTS.md",
    "docs/NotebookLM_sources_manifest.md",
    "docs/final/CENTRAL_AGENT_MEMORY_V1.md",
    "docs/final/P0_COMMERCIALIZATION_TRACKER.md",
    "docs/final/RESEARCH_HISTORY_V1.md",
    "reports/compression_track_a_headline_policy_v1_latest.json",
    "reports/notebooklm_archive_migration_plan_v1_latest.json",
    "reports/parallel_ops_run_2026-05-23_latest.json",
]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_command_handoff_snippet(dest: Path) -> None:
    mission = ROOT / "MISSION_LOG.md"
    text = mission.read_text(encoding="utf-8", errors="replace") if mission.is_file() else ""
    lines = [
        "# MKM Ops command handoff (NotebookLM · non-SSOT snippet)",
        "",
        f"generated_utc: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        f"target_notebook: {NOTEBOOK_NAME}",
        "boundary: NL is briefing only; paths·gates·pass/fail = CONSTITUTION + scripts + exit code.",
        "",
        "## Notebook roles (2026-05-23)",
        "- **00_OPS (this notebook):** 일상 지휘·Fact-Lock·우선순위·레포 포인터",
        "- **06_스마트팜:** 금산 IoT·벤더·현장만 (도메인 격벽)",
        "- **99_ARCHIVE:** 읽기 전용 보관 · 신규 질의 금지",
        "",
        "## MISSION_LOG 작전 보드 (발췌)",
    ]
    in_board = False
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("## ") and ("작전 보드" in line or "전술 작전 보드" in line):
            in_board = True
            lines.append(line)
            continue
        if in_board:
            if line.startswith("## ") and "작전 보드" not in line:
                break
            if line.strip():
                lines.append(line)
    if len(lines) < 12:
        lines.extend(
            [
                "(MISSION_LOG.md not found or empty — paste 작전 보드 manually)",
                "",
                "## Default routing",
                "- Implementation: CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md + pytest",
                "- Daily ops board: MISSION_LOG.md (local)",
                "- Smartfarm NL: 06 only",
            ]
        )
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    missing: list[str] = []
    file_meta: list[dict] = []

    _write_command_handoff_snippet(OUT / "00_ops_command_handoff_snippet.md")
    copied.append("00_ops_command_handoff_snippet.md")
    file_meta.append(
        {
            "name": "00_ops_command_handoff_snippet.md",
            "repo_path": "(generated)",
            "sha256": _sha256(OUT / "00_ops_command_handoff_snippet.md"),
            "bytes": (OUT / "00_ops_command_handoff_snippet.md").stat().st_size,
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

    index = {
        "schema": "notebooklm_ops_command_sync_pack_v1",
        "version": "1.0.0",
        "notebook_name": NOTEBOOK_NAME,
        "notebook_mcp_id": NOTEBOOK_MCP_ID,
        "notebook_url": "(create in NL web — paste share URL into MCP add_notebook)",
        "synced_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_count_target": "8-12",
        "files": sorted(copied),
        "files_meta": file_meta,
        "missing_repo_paths": missing,
        "setup_steps": [
            "NL web: + 새 노트 → 이름 00_OPS_지휘부_2026Q2",
            "Upload each file in this pack (or MCP add_source type=text)",
            "MCP: add_notebook with share URL → select_notebook 00-ops-command-2026q2",
            "Delete [ARCHIVED] 03 and 04 from home after optional source export to 99",
        ],
    }
    (OUT / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {"out": str(OUT), "copied": len(copied), "missing": missing},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
