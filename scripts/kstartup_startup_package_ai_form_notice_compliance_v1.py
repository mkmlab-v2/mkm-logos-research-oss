#!/usr/bin/env python3
"""K-Startup 340 별첨1 양식 공고 안내 문구 준수 (페이지·PII·파란 안내).

SSOT 요약 (공고 별첨1 상단 안내):
- 목차 1p 제외 본문 약 15p; 「5. AI 인재 활용 계획」은 전체 15p 중 2p 이내.
- 양식 구조 변경·삭제 금지; 표 행 추가 가능, 해당 없으면 공란.
- 파란 안내 문구 삭제 후 검정으로 작성.
- 대표·직원 성명·성별·생년월일·대학(원)명·소재지·직장명 등 PII는 제외 또는 ○/* 마스킹.
  [학력] 학·석·박·학과·전공 / [직장] 직업·주요 수행업무만 가능.
"""
from __future__ import annotations

import re
from typing import Any

# --- PII: 제출 본문·표에 넣지 말 것 (법인명·사업자등록 소재지는 양식 필수 항목으로 예외) ---
PII_LITERAL_BLOCKLIST: tuple[str, ...] = (
    "이기륜",
    "광명백제한의원",
    "광명백제",
)

PII_PATTERN_BLOCKLIST: tuple[re.Pattern[str], ...] = (
    re.compile(r"대표\s+[가-힣]{2,4}(?!\s*[\·/])"),  # "대표 홍길동" (법인 대표 직함 제외)
    re.compile(r"[가-힣]{2,4}\s*원장"),
    re.compile(r"생년\s*월\s*일|생년월일"),
    re.compile(r"성별\s*[:：]"),
    re.compile(r"(서울|경기|부산|대구|인천|광주|대전|울산|세종|강원|충북|충남|전북|전남|경북|경남|제주)[가-힣\s]*대학교"),
    re.compile(r"(서울|경기|부산|대구|인천|광주|대전|울산|세종|강원|충북|충남|전북|전남|경북|경남|제주)[가-힣\s]*대학원"),
)

BLUE_INSTRUCTION_SNIPPETS: tuple[str, ...] = (
    "법인등기부등본 및 사업자등록증",
    "동일하게 기입",
    "기준으로 기입",
    "※ 사업 신청 시",
    "※ 정부지원사업비는 최대",
    "※ 본문 내",
    "< 사진(이미지) 또는 설계도 제목 >",
)

# 팀·대표 역량 (PII 없음 · 공고 [직장] 형식)
TEAM_SECTION_COMPLIANT = """5.1 대표

- [직장] 한의사(면허) · 개인 의료기관 개원·운영 / 주식회사 목소리네트워크 대표.
- [직장] AI·RAG·HOLD 게이트·Fact-Lock 문서자동화 파이프라인 설계·구현·운영(OpenData 327 과제① 동일 아키텍처 축).
- 금융·신용·연체 모델링 실무 경력 없음 — 본 과제 범위에 명시.

5.2 팀·역량

- 1인 기업(법인 설립 2021) — 협약 후 AI 양성과정 수료 인재 정규직 1명(붙임6~8)으로 RAG·회귀·API 역량 보강(§6).
- 내부 pytest·감사 JSONL 회귀 체인으로 공고 개정 시 재인덱싱 품질을 관리한다.
- 외주는 UI/UX·보안·변리 선행조사 등 제한적으로만 활용; 핵심 RAG·게이트는 자체 수행."""

TEAM_CAPABILITY_GENERAL = "한의사 · AI/RAG·문서자동화·운영총괄"
TEAM_CAPABILITY_DETAIL = "한의사 · AI/RAG·Fact-Lock 파이프라인 구축·운영"

# 본문 「AI 인재 활용」칸: 2p 이내 요약 (별첨 2p PDF는 plan_06 전문)
AI_TALENT_BODY_SUMMARY_MAX_CHARS = 3_200


def _mask_literal(text: str, token: str) -> str:
    if token not in text:
        return text
    if token == "이기륜":
        return text.replace(token, "○○○")
    if "한의원" in token or "백제" in token:
        return text.replace(token, "개인 의료기관")
    return text.replace(token, "○○○")


def apply_form_notice_compliance(text: str, *, context: str = "") -> str:
    """Strip/mask PII and blue-instruction fragments from submission-bound text."""
    if not text:
        return text
    out = text
    for token in PII_LITERAL_BLOCKLIST:
        out = _mask_literal(out, token)
    if context == "plan_05_team_paste.txt":
        out = TEAM_SECTION_COMPLIANT
    elif "5.1 대표" in out and "이기륜" in out:
        out = TEAM_SECTION_COMPLIANT
    # heading cleanup
    out = re.sub(r"5\.1\s*대표\s+○○○", "5.1 대표", out)
    out = re.sub(r"5\.1\s*대표\s+이기륜", "5.1 대표", out)
    for pat in PII_PATTERN_BLOCKLIST:
        out = pat.sub("○○○", out)
    # drop lines that are pure form instructions
    lines: list[str] = []
    for line in out.splitlines():
        s = line.strip()
        if any(sn in s for sn in BLUE_INSTRUCTION_SNIPPETS):
            continue
        if s.startswith("※ ") and "제출" in s:
            continue
        lines.append(line)
    out = "\n".join(lines)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


def scan_pii_violations(text: str, *, source: str = "") -> list[dict[str, str]]:
    hits: list[dict[str, str]] = []
    for token in PII_LITERAL_BLOCKLIST:
        if token in text:
            hits.append({"source": source, "kind": "literal", "token": token})
    for pat in PII_PATTERN_BLOCKLIST:
        for m in pat.finditer(text):
            hits.append(
                {
                    "source": source,
                    "kind": "pattern",
                    "token": pat.pattern,
                    "snippet": m.group(0)[:40],
                }
            )
    return hits


def scan_instruction_remnants(text: str, *, source: str = "") -> list[dict[str, str]]:
    hits: list[dict[str, str]] = []
    for sn in BLUE_INSTRUCTION_SNIPPETS:
        if sn in text:
            hits.append({"source": source, "snippet": sn})
    return hits


def ai_talent_body_summary(full_text: str) -> str:
    """Main doc section 5 — keep within ~2 pages; full text goes to 별첨 PDF only."""
    text = apply_form_notice_compliance(full_text, context="plan_06_ai_talent_2p_paste.txt")
    if len(text) <= AI_TALENT_BODY_SUMMARY_MAX_CHARS:
        return text
    cut = text[: AI_TALENT_BODY_SUMMARY_MAX_CHARS]
    last = cut.rfind("\n\n")
    if last > AI_TALENT_BODY_SUMMARY_MAX_CHARS // 2:
        cut = cut[:last]
    return cut.rstrip() + "\n\n(상세는 별첨 「AI 인재 활용 계획」2p 참조)"


def compliance_report_from_docx_tables(doc) -> dict[str, Any]:
    """Scan python-docx Document for PII / instruction remnants."""
    pii: list[dict[str, str]] = []
    instr: list[dict[str, str]] = []
    for ti, table in enumerate(doc.tables):
        seen: set[int] = set()
        for ri, row in enumerate(table.rows):
            for ci, cell in enumerate(row.cells):
                tc = id(cell._tc)
                if tc in seen:
                    continue
                seen.add(tc)
                tx = cell.text or ""
                if not tx.strip():
                    continue
                src = f"T{ti}r{ri}c{ci}"
                pii.extend(scan_pii_violations(tx, source=src))
                instr.extend(scan_instruction_remnants(tx, source=src))
    return {"pii_hits": pii, "instruction_hits": instr}
