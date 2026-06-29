#!/usr/bin/env python3
"""Lane A draft builder — deterministic extract from SSOT (research_only, no LLM API)."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OVERVIEW = ROOT / "docs/final/artifacts/ai_opendata_challenge_2026_327_business_plan_overview_v1.md"
SUBMISSION_B = ROOT / "docs/final/artifacts/ai_opendata_challenge_2026_327_business_plan_submission_v1.md"
PART_C = ROOT / "docs/final/artifacts/ai_opendata_challenge_2026_327_market_expansion_submission_v1.md"
MARKET_SUMMARY = ROOT / "docs/final/artifacts/ai_opendata_challenge_2026_327_market_expansion_summary_v1.md"
ANNEX = ROOT / "docs/final/B2G_CONTROL_INTEGRITY_PROPOSAL_ANNEX_V1.md"
TECH_PREP = ROOT / "docs/final/B2G_TECH_DISCLOSURE_ONEPAGER_PREP_V1.md"
PROMPT_PACK = ROOT / "docs/final/artifacts/opendata_327_grant_agent_prompt_pack_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/opendata_327_lane_a_draft_v1_latest.json"

AX_GOVERNANCE_2026_PARAGRAPH = (
    "**AX 비용·품질 거버넌스 (2026 맥락)**  \n"
    "2026년 기업 AX 도입에서는 API 호출량·컨텍스트 길이에 따른 **비용 통제**가 핵심 리스크로 부상하고 있다. "
    "본 과제는 범용 챗봇형 사용량 경쟁이 아니라, **공고·서식 근거 RAG**, **슬롯 기반 생성**, "
    "**근거 미연결 시 HOLD**, **감사 가능 로그**로 **추론 호출 상한과 품질을 동시에** 관리하는 "
    "**비용·품질 거버넌스**를 목표로 한다. "
    "(내부 연구용 토큰·압축 벤치마크는 **본 공모 범위와 데이터를 합선하지 않는다**.)"
)

NEGATION_MARKERS = (
    "기재하지 않음",
    "미기재",
    "합선하지",
    "합선 기재",
    "주장하지",
    "별 트랙",
    "합선 출력 금지",
    "문장 합선 금지",
)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def extract_block(text: str, start_pat: str, end_pat: str) -> str:
    m = re.search(start_pat, text, re.MULTILINE)
    if not m:
        return f"[DRAFT] block not found: {start_pat[:40]}"
    start = m.start()
    rest = text[m.end() :]
    em = re.search(end_pat, rest, re.MULTILINE)
    end = m.end() + (em.start() if em else len(rest))
    return text[start:end].strip() + "\n"


def sanitize_lane_a(md: str) -> str:
    """Drop lines that trip Lane A forbidden grep (keep negation context)."""
    out: list[str] = []
    for line in md.splitlines():
        if any(n in line for n in NEGATION_MARKERS):
            out.append(line)
            continue
        if re.search(r"\bLG\b", line):
            continue
        if re.search(r"Track\s+A", line, re.I):
            continue
        if "47%" in line or "0.47" in line:
            continue
        if re.search(r"compression\s+OEM", line, re.I):
            continue
        if "Safety PLC" in line:
            continue
        if "실매매" in line:
            continue
        out.append(line)
    return "\n".join(out).strip() + "\n"


def grep_check_text(label: str, content: str) -> dict[str, Any]:
    hits: list[str] = []
    forbidden = ["47%", "0.47", "Safety PLC", "실매매", "hallucination-free"]
    for i, line in enumerate(content.splitlines(), 1):
        if any(n in line for n in NEGATION_MARKERS):
            continue
        if re.search(r"\bLG\b", line):
            hits.append(f"L{i}: LG")
        if re.search(r"Track\s+A", line, re.I):
            hits.append(f"L{i}: Track A")
        for f in forbidden:
            if f in line:
                hits.append(f"L{i}: {f}")
    return {"label": label, "ok": len(hits) == 0, "hits": hits}


def _task(
    task_id: str,
    markdown: str,
    method: str,
    *,
    ssot: str = "",
) -> dict[str, Any]:
    md = sanitize_lane_a(markdown)
    g = grep_check_text(task_id, md)
    return {
        "task_id": task_id,
        "status": "done" if g["ok"] else "blocked",
        "method": method,
        "ssot_ref": ssot,
        "output_markdown": md,
        "grep": g,
    }


def build_all_tasks() -> list[dict[str, Any]]:
    ov = OVERVIEW.read_text(encoding="utf-8")
    tasks: list[dict[str, Any]] = []

    # 1 outline
    lines_out = [
        "# OpenData 327 — OUTLINE (SSOT headings)\n",
        "> Lane A · `327-doc-doc-plan-outline-0`\n",
    ]
    for raw in ov.splitlines():
        if raw.startswith("## ") and "변경 이력" in raw:
            break
        if raw.startswith("## "):
            lines_out.append(raw)
        elif raw.startswith("### "):
            lines_out.append(f"  {raw}")
    tasks.append(_task("327-doc-doc-plan-outline-0", "\n".join(lines_out), "ssot_headings", ssot=str(OVERVIEW)))

    # 2 narrative §1-1
    s11 = extract_block(ov, r"### 1-1\.", r"### 1-2\.")
    tasks.append(
        _task(
            "327-doc-doc-plan-narrative_section-1",
            f"# §1-1 개발계획 본문 (SSOT extract)\n\n{s11}",
            "ssot_extract_1-1",
            ssot=str(OVERVIEW),
        )
    )

    # 8 schedule (do early — same file)
    s12 = extract_block(ov, r"### 1-2\.", r"\n---\n\n## 2\.")
    tasks.append(
        _task(
            "327-table-dev-schedule",
            s12,
            "ssot_extract_1-2",
            ssot=str(OVERVIEW),
        )
    )

    # 3 annex §2.1 + §3
    if ANNEX.is_file():
        ax = ANNEX.read_text(encoding="utf-8")
        annex_body = extract_block(ax, r"## 2\.1 한국어", r"## 4\. 각주")
        tasks.append(
            _task(
                "327-doc-doc-annex-risk_legal-1",
                f"# Annex paste block (verbatim SSOT)\n\n{annex_body}",
                "annex_verbatim",
                ssot=str(ANNEX),
            )
        )

    # 4 market — overview §3-1 + market summary Phase1 bullets only
    s31 = extract_block(ov, r"### 3-1\.", r"### 3-2\.")
    phase1 = ""
    if MARKET_SUMMARY.is_file():
        ms = MARKET_SUMMARY.read_text(encoding="utf-8")
        phase1 = extract_block(
            ms,
            r"\*\*확장 방향 \(Phase 1",
            r"\*\*확장 방향 \(Phase 2",
        )
    tasks.append(
        _task(
            "327-doc-doc-market-narrative_section-0",
            f"# §3-1 + Phase1 확장 (Lane A clean)\n\n{s31}\n\n{phase1}",
            "overview_3-1+market_phase1",
            ssot=str(OVERVIEW),
        )
    )

    # 5 tech — disclosure prep blocks 2-5
    if TECH_PREP.is_file():
        tp = TECH_PREP.read_text(encoding="utf-8")
        tech_body = extract_block(tp, r"## 2\. 1페이지", r"## 6\.")
        tasks.append(
            _task(
                "327-doc-doc-tech-narrative_section-0",
                f"# 기술공시 1p 준비 목차 (출원 전 · SSOT)\n\n{tech_body}",
                "tech_prep_extract",
                ssot=str(TECH_PREP),
            )
        )

    # 6 table §2-2 from submission B
    if SUBMISSION_B.is_file():
        sb = SUBMISSION_B.read_text(encoding="utf-8")
        t22 = extract_block(sb, r"### 2-2\.", r"\n---\n\n## 3\.")
        tasks.append(
            _task(
                "327-table-part-b",
                f"# Part B §2-2 (SSOT — commander confirm numbers)\n\n{t22}",
                "submission_b_2-2",
                ssot=str(SUBMISSION_B),
            )
        )

    # 7 part C — §3-2 경제성(overview) + market expansion 3-2 paste bullets (Lane A clean)
    s32 = extract_block(ov, r"### 3-2\.", r"\*\*지식재산")
    if "비용·품질 거버넌스" not in s32:
        s32 = s32.rstrip() + "\n\n" + AX_GOVERNANCE_2026_PARAGRAPH + "\n"
    pc_bullets = ""
    if PART_C.is_file():
        pc = PART_C.read_text(encoding="utf-8")
        # Phase 1 only — Phase 2 mentions B2B compression API (Track A negation line trips OD1)
        pc_bullets = extract_block(
            pc,
            r"\*\*확장 방향 \(Phase 1",
            r"\*\*확장 방향 \(Phase 2",
        )
    body = f"# Part C / §3-2 경제성·시장 (Lane A clean)\n\n{s32}\n"
    if pc_bullets and "[DRAFT] block not found" not in pc_bullets:
        body += f"\n---\n\n## 첨부 3-2 불릿 (Phase 1~2)\n\n{pc_bullets}\n"
    tasks.append(
        _task(
            "327-narrative-part-c",
            body,
            "overview_3-2+part_c_bullets",
            ssot=str(PART_C if PART_C.is_file() else OVERVIEW),
        )
    )

    return tasks


def build() -> dict[str, Any]:
    if not OVERVIEW.is_file():
        raise FileNotFoundError(OVERVIEW)

    patch_script = ROOT / "scripts/patch_opendata_327_ssot_section_3_2_ax_v1.py"
    if patch_script.is_file():
        import subprocess
        import sys

        subprocess.run([sys.executable, str(patch_script)], cwd=str(ROOT), check=True)

    completed = build_all_tasks()
    pack: dict[str, Any] = {}
    if PROMPT_PACK.is_file():
        pack = json.loads(PROMPT_PACK.read_text(encoding="utf-8-sig"))

    all_ids = [t["task_id"] for t in pack.get("llm_draft_tasks", [])]
    done_ids = {c["task_id"] for c in completed if c["status"] == "done"}
    pending = [tid for tid in all_ids if tid not in done_ids]

    return {
        "schema": "opendata_327_lane_a_draft_v1",
        "generated_at_utc": _now(),
        "research_only": True,
        "ssot": str(OVERVIEW.resolve()),
        "prompt_pack": str(PROMPT_PACK.resolve()),
        "completed_count": len(done_ids),
        "total_llm_tasks": len(all_ids),
        "pending_task_ids": pending,
        "completed": completed,
        "next_recommended": pending[0] if pending else None,
        "post_lane_a": [
            "powershell -NoProfile -File scripts/Run-GrantProposalOpenData327ScriptGateB_v1.ps1",
        ],
        "human_lane_c": "12 tasks — cover A, §2-2 confirm, G3, G5, K-Startup, Nara",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(args.out),
                "completed": doc["completed_count"],
                "total": doc["total_llm_tasks"],
                "pending": doc["pending_task_ids"],
            },
            ensure_ascii=False,
        )
    )
    blocked = [c for c in doc["completed"] if c["status"] == "blocked"]
    return 1 if blocked else 0


if __name__ == "__main__":
    raise SystemExit(main())
