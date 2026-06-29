#!/usr/bin/env python3
"""KOSPI DART MD&A PoC shared library — citation lock, scope guard, retrieval."""

from __future__ import annotations

import re
from typing import Any

PARAGRAPH_ID_RE = re.compile(r"DART-MDNA-P(\d{3})")
PARAGRAPH_REF_RE = re.compile(r"\[Ref:\s*(DART-MDNA-P\d{3})\]")
NUMERIC_CLAIM_RE = re.compile(
    r"(?:\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)\s*%"
    r"|\d{1,3}(?:,\d{3})*(?:\.\d+)?\s*(?:억|조|원|일)"
)

SCOPE_VIOLATION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"주가|목표가|매수|매도|상승\s*전망|하락\s*전망|다음\s*달\s*코스피", re.I),
    re.compile(r"재무제표\s*표|표\s*데이터|엑셀\s*표|table\s*data", re.I),
    re.compile(r"연준|금리\s*인상|뉴스|블로그|외부\s*매크로|골드만|모건스탠리", re.I),
)

MDA_SECTION_MARKERS = (
    "이사의 경영진단",
    "경영진단 및 분석",
    "MD&A",
    "Management Discussion",
)

MDA_END_MARKERS = (
    "재무에 관한 사항",
    "주주에 관한 사항",
    "이사 및 감사의",
    "주석",
)

_TOC_LINE_RE = re.compile(r"-{5,}")


def _is_toc_line(line: str) -> bool:
    s = line.strip()
    if not s:
        return True
    if _TOC_LINE_RE.search(s) and len(s) < 220:
        return True
    if re.fullmatch(r"[IVXLC\d\.\s]+", s):
        return True
    return False


def _filter_toc_lines(section: str) -> str:
    kept = [line.strip() for line in section.splitlines() if line.strip() and not _is_toc_line(line)]
    return "\n".join(kept).strip()


def _trim_mda_end(section: str, *, min_body_before_end: int = 200) -> str:
    end = len(section)
    for marker in MDA_END_MARKERS:
        idx = section.find(marker)
        if idx >= min_body_before_end:
            end = min(end, idx)
    return section[:end].strip()


def extract_mda_section(raw: str) -> str:
    text = raw.strip()
    if not text:
        return ""
    lower = text.lower()
    candidates: list[str] = []

    for marker in MDA_SECTION_MARKERS:
        start = 0
        while True:
            idx = text.find(marker, start)
            if idx < 0:
                idx = lower.find(marker.lower(), start)
            if idx < 0:
                break
            section = _filter_toc_lines(_trim_mda_end(text[idx:]))
            if len(section) >= 200:
                candidates.append(section)
            start = idx + len(marker)

    if candidates:
        return max(candidates, key=len)

    # Fallback: first marker hit (legacy short filings).
    start = 0
    for marker in MDA_SECTION_MARKERS:
        idx = text.find(marker)
        if idx >= 0:
            start = idx
            break
        idx = lower.find(marker.lower())
        if idx >= 0:
            start = idx
            break
    section = _filter_toc_lines(_trim_mda_end(text[start:].strip() if start else text, min_body_before_end=80))
    return section.strip()


def normalize_paragraph_id(ord_idx: int) -> str:
    return f"DART-MDNA-P{ord_idx:03d}"


def split_text_to_paragraphs(raw: str) -> list[str]:
    chunks: list[str] = []
    for block in re.split(r"\n\s*\n+", raw.strip()):
        for line in block.splitlines():
            line = line.strip()
            if not line or line.startswith("※"):
                continue
            chunks.append(line)
    return chunks


def chunk_mda_text_to_paragraphs(raw: str) -> list[dict[str, Any]]:
    paragraphs: list[dict[str, Any]] = []
    for ord_idx, text in enumerate(split_text_to_paragraphs(raw), start=1):
        paragraphs.append(
            {
                "paragraph_id": normalize_paragraph_id(ord_idx),
                "ord": ord_idx,
                "text_ko": text,
            }
        )
    return paragraphs


def paragraph_map(corpus: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for row in corpus.get("paragraphs") or []:
        pid = str(row.get("paragraph_id") or "")
        text = str(row.get("text_ko") or "")
        if pid:
            out[pid] = text
    return out


def validate_paragraph_citations(text: str, allowed: set[str]) -> dict[str, Any]:
    cited = {m.group(1) for m in PARAGRAPH_REF_RE.finditer(text or "")}
    orphan = sorted(cited - allowed)
    return {
        "cited_paragraph_ids": sorted(cited),
        "orphan_citations": orphan,
        "citation_valid": len(orphan) == 0 and len(cited) > 0,
    }


def extract_numeric_claims(text: str) -> list[str]:
    return sorted({m.group(0).strip() for m in NUMERIC_CLAIM_RE.finditer(text or "")})


def validate_numeric_claims(answer: str, cited_ids: set[str], pmap: dict[str, str]) -> dict[str, Any]:
    claims = extract_numeric_claims(answer)
    if not claims:
        return {"numeric_claims": [], "unverified_numeric_claims": [], "numeric_valid": True}
    source_blob = " ".join(pmap.get(pid, "") for pid in cited_ids)
    unverified = [c for c in claims if c not in source_blob]
    return {
        "numeric_claims": claims,
        "unverified_numeric_claims": unverified,
        "numeric_valid": len(unverified) == 0,
    }


def is_scope_violation_query(query: str) -> bool:
    q = (query or "").strip()
    if not q:
        return True
    return any(p.search(q) for p in SCOPE_VIOLATION_PATTERNS)


def scope_refusal_payload(query: str) -> dict[str, Any]:
    return {
        "ok": False,
        "schema": "kospi_dart_mda_refusal_v1",
        "research_only": True,
        "send_gate": "HOLD",
        "canon_status": "not_acquired",
        "error_code": "SCOPE_VIOLATION_HONEST_REFUSAL",
        "msg": (
            "본 오라클은 지정된 DART MD&A 공시 1종(문단 텍스트) 외의 데이터를 참조할 수 없으므로 "
            "답변을 거부합니다."
        ),
        "query": query,
        "table_excluded_v1": True,
    }


_KO_STOP = frozenset(
    {
        "은",
        "는",
        "이",
        "가",
        "을",
        "를",
        "의",
        "에",
        "와",
        "과",
        "도",
        "로",
        "으로",
        "에서",
        "무엇",
        "어떤",
        "있는가",
        "하였으며",
        "대비",
        "전망",
        "정책",
        "이유",
        "관계",
        "서술",
        "변화",
        "영향",
        "기여",
        "대응",
        "확대",
        "증가",
    }
)

_DOMAIN_KEYS = (
    "연구개발",
    "연구개발비",
    "반도체",
    "메모리",
    "파운드리",
    "Foundry",
    "영업이익",
    "배당",
    "환율",
    "AI",
    "HBM",
    "HBM3E",
    "HBM4",
    "재고",
    "tape-out",
    "capex",
    "OLED",
    "시스템LSI",
    "주주환원",
    "배당성향",
    "DS",
    "DX",
    "SDC",
    "Harman",
    "매출",
    "매출액",
    "Galaxy",
    "배터리",
    "ESS",
    "전기차",
    "이차전지",
)

# Weak synonyms only used when the full phrase is in the query (avoid '연구' alone → false hit).
_QUERY_SYNONYMS: dict[str, tuple[str, ...]] = {
    "연구개발비": ("연구개발", "연구 개발", "R&D", "연구개발비용"),
    "배당": ("현금배당", "주주환원", "배당성향", "배당금"),
    "파운드리": ("Foundry", "파운드리"),
    "메모리": ("메모리 사업", "DRAM", "NAND"),
    "HBM": ("HBM3E", "HBM4", "고대역폭메모리"),
}


def _query_keywords(query: str) -> set[str]:
    q = re.sub(r"[?？!,，.]", " ", query or "")
    parts = re.findall(r"[\w가-힣]+", q)
    keys: set[str] = set()
    for part in parts:
        if len(part) >= 2 and part not in _KO_STOP:
            keys.add(part)
    for key in _DOMAIN_KEYS:
        if key in query:
            keys.add(key)
    for anchor, syns in _QUERY_SYNONYMS.items():
        if anchor in query:
            keys.add(anchor)
            keys.update(syns)
    return keys


def _score_paragraph(query: str, text: str) -> int:
    keys = _query_keywords(query)
    score = 0
    for key in keys:
        if key in text:
            score += 2 + min(len(key) // 4, 3)
    # Phrase bonus for multi-token domain anchors (e.g. "DS 부문").
    for phrase in ("DS 부문", "DX 부문", "메모리 사업", "Foundry 사업"):
        if phrase in query and phrase in text:
            score += 6
    return score


def corpus_keyword_hit_rate(corpus: dict[str, Any], keyword: str) -> float:
    """Fraction of paragraphs containing keyword (discovery helper)."""
    paras = corpus.get("paragraphs") or []
    if not paras:
        return 0.0
    hits = sum(1 for row in paras if keyword in str(row.get("text_ko") or ""))
    return hits / len(paras)


def retrieve_paragraphs_for_query(query: str, corpus: dict[str, Any], *, top_k: int = 2) -> list[dict[str, Any]]:
    ranked: list[tuple[int, dict[str, Any]]] = []
    for row in corpus.get("paragraphs") or []:
        text = str(row.get("text_ko") or "")
        score = _score_paragraph(query, text)
        if score > 0:
            ranked.append((score, row))
    ranked.sort(key=lambda x: (-x[0], x[1].get("ord", 0)))
    return [row for _, row in ranked[:top_k]]


def detect_intra_document_conflicts(corpus: dict[str, Any]) -> list[dict[str, Any]]:
    """Same-document numeric tension only (PoC v1 — no QoQ second filing)."""
    conflicts: list[dict[str, Any]] = []
    paras = corpus.get("paragraphs") or []
    growth: list[tuple[str, str]] = []
    risk: list[tuple[str, str]] = []
    for row in paras:
        pid = str(row.get("paragraph_id") or "")
        text = str(row.get("text_ko") or "")
        if "증가" in text or "확대" in text or "개선" in text:
            growth.append((pid, text))
        if "리스크" in text or "불확실" in text or "조정" in text or "비수기" in text:
            risk.append((pid, text))
    if growth and risk:
        conflicts.append(
            {
                "conflict_id": "mda_growth_vs_risk_v1",
                "label_ko": "성장 서술 vs 리스크·조정 서술 (동일 MD&A 내 병렬)",
                "side_a": {"paragraph_ids": [p for p, _ in growth[:2]], "label_ko": "성장·투자·개선"},
                "side_b": {"paragraph_ids": [p for p, _ in risk[:2]], "label_ko": "리스크·조정·비수기"},
            }
        )
    return conflicts


def build_deterministic_answer(query: str, corpus: dict[str, Any]) -> dict[str, Any]:
    hits = retrieve_paragraphs_for_query(query, corpus, top_k=2)
    if not hits:
        return {"ok": False, "error": "no_paragraph_hit", "query": query}

    pmap = paragraph_map(corpus)
    allowed = {str(h["paragraph_id"]) for h in hits}
    snippets: list[str] = []
    refs: list[str] = []
    for row in hits:
        pid = str(row["paragraph_id"])
        text = str(row["text_ko"]).strip()
        snippets.append(f"{text} `[Ref: {pid}]`")
        refs.append(pid)

    conflicts = detect_intra_document_conflicts(corpus)
    conflict_note = ""
    if conflicts and any(k in query for k in ("리스크", "모순", "상충", "대조")):
        c0 = conflicts[0]
        conflict_note = (
            f"\n\n[Conflict 병렬] {c0['label_ko']} — "
            f"A:{', '.join(c0['side_a']['paragraph_ids'])} vs "
            f"B:{', '.join(c0['side_b']['paragraph_ids'])} (합의 요약 없음)."
        )

    answer = (
        f"[HYPO][research_only] 질문 「{query.strip()}」에 대한 MD&A 인용 요약 — "
        f"표 데이터 제외(TABLE_EXCLUDED_v1).\n\n"
        + "\n\n".join(snippets)
        + conflict_note
        + "\n\n단일 투자 권유·주가 예측 아님 — Human Gate [NON_GATING]."
    )

    citation_check = validate_paragraph_citations(answer, allowed)
    numeric_check = validate_numeric_claims(answer, set(citation_check["cited_paragraph_ids"]), pmap)
    citation_valid = citation_check["citation_valid"] and numeric_check["numeric_valid"]

    return {
        "ok": True,
        "schema": "kospi_dart_mda_answer_v1",
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_tier": "B",
        "wires_to_scoring_core": False,
        "non_gating": True,
        "synthesis_mode": "deterministic_mda_citation_lock",
        "llm_invoked": False,
        "query": query,
        "answer_ko": answer,
        "citation_valid": citation_valid,
        "citation_check": citation_check,
        "numeric_check": numeric_check,
        "allowed_paragraph_ids": sorted(allowed),
        "conflicts": conflicts,
    }
