#!/usr/bin/env python3
"""Synthesize llm_wiki wiki page from theory mathematization canon (raw→wiki draft)."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from llm_wiki_okf_v1 import wrap_concept_document  # noqa: E402

CANON = ROOT / "docs/final/artifacts/mkm_theory_mathematization_canon_v1_latest.md"
FORMULAS_JSON = ROOT / "docs/final/artifacts/mkm12_75_formulas_ssot_v1_latest.json"
WORLDVIEW = ROOT / "docs/final/MKM_WORLDVIEW_AND_PHILOSOPHY_CONSTITUTION_V1.md"
WIRING = ROOT / "docs/final/artifacts/logos_theory_implementation_wiring_v1.json"
FUSION_PLAN = ROOT / "docs/final/artifacts/mkm_llm_wiki_ops_memory_fusion_plan_v1_latest.json"
WIKI_DIR = ROOT / "memory/obsidian_vault/llm_wiki/wiki"
RAW_DIR = ROOT / "memory/obsidian_vault/llm_wiki/raw"
REPORT = ROOT / "docs/final/artifacts/llm_wiki_theory_mathematization_synthesis_v1_latest.json"

# Existing resume-pack / overlay pin ids only (do not invent).
OPS_MEMORY_PIN_IDS = [
    "prism_ops_theory_mathematization_gate",
    "prism_ops_theory_formula_ssot",
    "prism_ops_logos_metacog_coord",
    "prism_ops_logos_cosmic_anchor_bridge",
    "prism_ops_central_checkpoint",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_section(path: Path, heading_prefix: str, max_lines: int = 40) -> str:
    if not path.is_file():
        return ""
    lines: list[str] = []
    capture = False
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith(heading_prefix):
            capture = True
            lines.append(line)
            continue
        if capture:
            if line.startswith("## ") and not line.startswith(heading_prefix):
                break
            lines.append(line)
            if len(lines) >= max_lines:
                break
    return "\n".join(lines).strip()


def main() -> int:
    ts = utc_now()
    WIKI_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    payload = {}
    if FORMULAS_JSON.is_file():
        payload = json.loads(FORMULAS_JSON.read_text(encoding="utf-8"))

    unrecovered = int(payload.get("unrecovered_slots", 51))
    with_expr = int(payload.get("documented_with_expr", 0))
    fact_count = len(payload.get("repo_implemented_facts", []))

    worldview_s5 = _read_section(WORLDVIEW, "## 5.", 12)
    canon_intro = ""
    if CANON.is_file():
        text = CANON.read_text(encoding="utf-8", errors="replace")
        canon_intro = "\n".join(text.splitlines()[:25]).strip()

    wiki_inner = f"""# MKM 이론·수학화 합성 (LLM Wiki)

> **격벽:** 본 페이지는 **연구·내부 정본** 합성물이다. Track A·K-Startup·실매매 주장 근거로 쓰지 않는다.

## 스냅샷 ({ts[:10]})

| 항목 | 값 |
|------|-----|
| 75식 슬롯 | {payload.get('total_slots', 75)} |
| UNRECOVERED | {unrecovered} |
| 수식 문자열 보유 | {with_expr} |
| 레포 FACT | {fact_count} (`repo_implemented_facts`) |

## WORLDVIEW §5 (서사↔수학)

{worldview_s5 or "(WORLDVIEW 미로드)"}

## Canon 요약 (상단)

{canon_intro or "(canon 미로드)"}

## 등급 계약

- **FACT:** `gematria_blend`, `gematria_4d_bridge`, `myeongni_d_out`, `geumhwa` + CONSTITUTION 압축식
- **HYPO:** 75식 헌법 인덱스 (이름·장별 카탈로그)
- **FORBIDDEN:** dt/dx 통일장 · EPD 임상 SSOT · Two-Track IR wash · fake ops scripts

## 갱신 명령

```powershell
py scripts/mirror_mkm12_math_vault_to_workspace_v1.py
py scripts/build_mkm_formula_ssot_bundle_v1.py
py scripts/synthesize_llm_wiki_theory_mathematization_v1.py
```

## Hybrid LTM pointers (resource only · no page balloon)

| Layer | Pointer |
|-------|---------|
| L0 ops pins | `{', '.join(OPS_MEMORY_PIN_IDS)}` |
| L1 fusion plan | `docs/final/artifacts/mkm_llm_wiki_ops_memory_fusion_plan_v1_latest.json` |
| L2 wiring | `docs/final/artifacts/logos_theory_implementation_wiring_v1.json` |
| L2 truth | `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` + scripts + exit 0 |

## raw 포인터

- `memory/obsidian_vault/llm_wiki/raw/` — 원문 불변; 본 wiki는 합성만.
"""
    wiki_body = wrap_concept_document(
        wiki_inner,
        {
            "schema": "llm_wiki_wiki_v1",
            "type": "Theory Canon",
            "content_type": "synthesis",
            "title": "MKM Theory Mathematization Canon",
            "description": "Internal B-track synthesis of 75-formula canon and WORLDVIEW §5.",
            "resource": "docs/final/artifacts/mkm_theory_mathematization_canon_v1_latest.md",
            "wiring_artifact": "docs/final/artifacts/logos_theory_implementation_wiring_v1.json",
            "fusion_plan": "docs/final/artifacts/mkm_llm_wiki_ops_memory_fusion_plan_v1_latest.json",
            "ops_memory_pin_ids": OPS_MEMORY_PIN_IDS,
            "tags": ["mkm", "theory", "mathematization", "HYPO", "hybrid-ltm"],
            "timestamp": ts,
            "generated_at_utc": ts,
            "grade": "HYPO",
            "track": "B-track internal",
            "sources": [
                "docs/final/artifacts/mkm_theory_mathematization_canon_v1_latest.md",
                "docs/final/artifacts/mkm12_75_formulas_ssot_v1_latest.json",
                "docs/final/MKM_WORLDVIEW_AND_PHILOSOPHY_CONSTITUTION_V1.md",
                "docs/final/artifacts/logos_theory_implementation_wiring_v1.json",
            ],
            "fact_lock": "CONSTITUTION + scripts only for implementation claims",
        },
    )

    wiki_path = WIKI_DIR / "mkm_theory_mathematization_canon_v1.md"
    wiki_path.write_text(wiki_body, encoding="utf-8")

    raw_pointer = RAW_DIR / "2026-06-15_mkm_theory_mathematization_canon_pointer.md"
    raw_body = wrap_concept_document(
        "\n".join(
            [
                "# Pointer: theory mathematization canon (immutable raw stub)",
                "",
                "Immutable ingest pointer. Synthesis lives under `wiki/`; pass/fail is L2 only.",
                "",
                f"- wiki_synthesis: `memory/obsidian_vault/llm_wiki/wiki/mkm_theory_mathematization_canon_v1.md`",
                f"- ssot_canon: `docs/final/artifacts/mkm_theory_mathematization_canon_v1_latest.md`",
                f"- wiring: `docs/final/artifacts/logos_theory_implementation_wiring_v1.json`",
                f"- fusion_plan: `docs/final/artifacts/mkm_llm_wiki_ops_memory_fusion_plan_v1_latest.json`",
            ]
        ),
        {
            "schema": "llm_wiki_raw_v1",
            "type": "External Reference",
            "content_type": "source_summary",
            "title": "Theory mathematization canon pointer",
            "description": "Raw pointer to theory canon + logos wiring (no body dump).",
            "resource": "docs/final/artifacts/mkm_theory_mathematization_canon_v1_latest.md",
            "tags": ["mkm", "theory", "pointer", "HYPO"],
            "timestamp": ts,
            "generated_at_utc": ts,
            "ops_memory_pin_ids": OPS_MEMORY_PIN_IDS,
        },
    )
    raw_pointer.write_text(raw_body, encoding="utf-8")

    report = {
        "schema": "llm_wiki_theory_mathematization_synthesis_v1",
        "generated_at_utc": ts,
        "wiki_path": str(wiki_path.relative_to(ROOT)).replace("\\", "/"),
        "raw_pointer": str(raw_pointer.relative_to(ROOT)).replace("\\", "/"),
        "wiring_artifact": str(WIRING.relative_to(ROOT)).replace("\\", "/") if WIRING.is_file() else None,
        "fusion_plan": str(FUSION_PLAN.relative_to(ROOT)).replace("\\", "/") if FUSION_PLAN.is_file() else None,
        "ops_memory_pin_ids": OPS_MEMORY_PIN_IDS,
        "unrecovered_slots": unrecovered,
        "documented_with_expr": with_expr,
        "ok": wiki_path.is_file(),
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
