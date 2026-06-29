#!/usr/bin/env python3
"""Build NotebookLM upload pack for MKM theory mathematization (internal B-track canon).

SSOT: docs/NotebookLM_sources_manifest.md — MKM_THEORY_MATHEMATIZATION row
Output: reports/notebooklm_theory_mathematization_pack_v1/
"""
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "notebooklm_theory_mathematization_pack_v1"
NOTEBOOK_NAME = "23_MKM_THEORY_MATHEMATIZATION_2026Q2"
NOTEBOOK_MCP_ID = "23-mkm-theory-mathematization-2026q2"

PACK_SOURCES: list[str] = [
    "docs/final/artifacts/mkm_theory_mathematization_canon_v1_latest.md",
    "docs/final/MKM_WORLDVIEW_AND_PHILOSOPHY_CONSTITUTION_V1.md",
    "docs/final/artifacts/mkm12_75_formulas_ssot_v1_latest.json",
    "docs/final/artifacts/mkm_theory_formula_promotion_registry_v1_latest.json",
    "docs/final/artifacts/worldview_formula_crosslink_bridge_v1_latest.json",
    "docs/final/MKM12_75개_수학공식_전체목록_2026-01-31.md",
    "docs/final/MKM12_L0_L1_L2_CLAIMS_TAGGED_FACTCHECK_2026-04-09.md",
    "docs/final/MKM_CORE_THEORY_V1.md",
    "docs/final/vault_mirror/mkm12_mathematics/MKM12_수학공식_인덱스_2026-01-31.md",
    "docs/final/MKM12_수학헌법_v4.0_최종봉인판_2026-01-31.md",
]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_boundary_snippet(dest: Path) -> None:
    lines = [
        "# MKM Theory Mathematization NL corpus boundary (internal · non-SSOT snippet)",
        "",
        f"generated_utc: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        f"target_notebook: {NOTEBOOK_NAME}",
        "data_lane: mkm_theory_mathematization",
        "track: B-track / internal canon · K-Startup·Track A 격벽",
        "boundary: NL is briefing only; FACT paths = CONSTITUTION + scripts + exit code.",
        "",
        "## Purpose",
        "- 75식 HYPO 인덱스·도메인 맵·금지 목록 (dt/dx·EPD·Two-Track IR wash)",
        "- WORLDVIEW §5 (24+4+51) · canon v1 · 75 JSON",
        "- **NOT** compression SLA headline · **NOT** live trading GO",
        "",
        "## NEVER cross-cite in this notebook",
        "- MS paste 47.5%/Jaccard as 「75식 전역 완성」",
        "- dt/dx 역시간 통일장 · EPD 임상 · fake PowerShell ops scripts",
        "- NotebookLM alone as **production implemented** or **Track A promotion**",
        "",
        "## Grade contract",
        "- FACT: 4 repo_implemented_facts + CONSTITUTION compression only",
        "- HYPO: 헌법 75식 names · vault mirror",
        "- FORBIDDEN: single TOE complete · IR deception",
        "",
        "## NL smoke questions",
        '- "75식 전부 프로덕션?" → must refuse; 4 FACT + HYPO index.',
        '- "dt/dx 통일장 완성?" → must refuse; FORBIDDEN in canon.',
        '- "압축 47.5% = 수학헌법 증명?" → separate lanes; compression FACT only.',
    ]
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    missing: list[str] = []
    file_meta: list[dict] = []

    _write_boundary_snippet(OUT / "00_theory_mathematization_lane_boundary_snippet.md")
    copied.append("00_theory_mathematization_lane_boundary_snippet.md")
    file_meta.append(
        {
            "name": "00_theory_mathematization_lane_boundary_snippet.md",
            "repo_path": "(generated)",
            "sha256": _sha256(OUT / "00_theory_mathematization_lane_boundary_snippet.md"),
            "bytes": (OUT / "00_theory_mathematization_lane_boundary_snippet.md").stat().st_size,
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
        "schema": "notebooklm_theory_mathematization_pack_v1",
        "version": "1.0.0",
        "notebook_name": NOTEBOOK_NAME,
        "notebook_mcp_id": NOTEBOOK_MCP_ID,
        "synced_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "data_lane": "mkm_theory_mathematization",
        "files": sorted(copied),
        "files_meta": file_meta,
        "missing_repo_paths": missing,
        "setup_steps": [
            f"nlm notebook create {NOTEBOOK_NAME}",
            "py scripts/build_notebooklm_theory_mathematization_pack_v1.py",
            "Upload reports/notebooklm_theory_mathematization_pack_v1/ to NL (web or MCP add_source)",
            "py scripts/mirror_mkm12_math_vault_to_workspace_v1.py (prerequisite vault mirror)",
            "py scripts/build_mkm_formula_ssot_bundle_v1.py (refresh 75 JSON before pack)",
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
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
