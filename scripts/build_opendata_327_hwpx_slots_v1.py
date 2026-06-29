#!/usr/bin/env python3
"""Build HWPX slots for OpenData 327 official (붙임2) business plan form."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUBMISSION = ROOT / "docs/final/artifacts/ai_opendata_challenge_2026_327_business_plan_submission_v1.md"
MARKET_SUMMARY = ROOT / "docs/final/artifacts/ai_opendata_challenge_2026_327_market_expansion_summary_v1.md"
DEFAULT_OUT = ROOT / "data/btrack/hwpx_poc/slots_opendata_327_official_v1.json"
META_OUT = ROOT / "reports/opendata_327_hwpx_slots_build_latest.json"

STRIP_LINE_PATTERNS = (
    r"^-\s+\*\*schema:",
    r"^-\s+\*\*공고:",
    r"^-\s+\*\*과제:",
    r"^-\s+\*\*신청",
    r"^-\s+\*\*대표",
    r"^-\s+\*\*소재",
    r"^-\s+\*\*기업",
    r"^-\s+\*\*Fact-Lock",
    r"^-\s+\*\*접수",
    r"^-\s+\*\*KSIC",
    r"^-\s+\*\*장기기억",
    r"^-\s+\*\*연계",
    r"^-\s+\*\*시장성",
    r"^-\s+\*\*통제",
    r"^-\s+\*\*범위",
    r"^>\s",
    r"`docs/",
    r"`reports/",
    r"moksori_mega_commercialization",
    r"mkmlife\.com",
    r"P0_COMMERCIALIZATION",
    r"MKM_DOMAIN_PORTFOLIO",
    r"PERSONADIARY",
    r"AGENTS\.md",
    r"a-codeai\.com",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def extract_block(text: str, start_pat: str, end_pat: str) -> str:
    m = re.search(start_pat, text, re.MULTILINE)
    if not m:
        return ""
    start = m.start()
    rest = text[m.end() :]
    em = re.search(end_pat, rest, re.MULTILINE)
    end = m.end() + (em.start() if em else len(rest))
    return text[start:end].strip()


def sanitize_submission(text: str) -> str:
    lines: list[str] = []
    for line in text.splitlines():
        if any(re.search(p, line) for p in STRIP_LINE_PATTERNS):
            continue
        if line.startswith("# "):
            continue
        if "제출 시 삭제" in line or "파란색 안내" in line:
            continue
        if line.strip().startswith("※"):
            continue
        if "붙여 넣기용" in line or "붙여넣기용" in line:
            continue
        lines.append(line)
    out = "\n".join(lines).strip()
    out = re.sub(r"^#{1,6}\s+", "", out, flags=re.MULTILINE)
    out = re.sub(r"\*\*([^*]+)\*\*", r"\1", out)
    out = re.sub(r"`([^`]+)`", r"\1", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


OVERVIEW_SUMMARIES: dict[str, str] = {
    "overview-1": (
        "중진공 정책자금 신청은 규정 준수 문서로, 공고·서식·예시를 버전별 인덱싱하고 "
        "지식 그래프·RAG·슬롯 생성·근거 미연결 HOLD 후 담당자 확인으로 초안을 산출한다. "
        "범용 폼 매핑이 아니며 AI 자동 제출 없음."
    ),
    "overview-2": (
        "하이브리드 검색·지식 그래프 라우팅·reranker·슬롯 우선 생성·무결성 HOLD 게이트로 "
        "근거 정밀도와 서식 정합성을 확보한다. 민감 항목은 RAG 인용·고정문 우선."
    ),
    "overview-3": (
        "준비 시간·인지 부담·형식 오류·제3자 개입 리스크를 줄이고, 공공 서식 라스트마일 "
        "납품 품질로 차별화한다. 그래프·체크리스트로 필수·연관 항목을 구조화한다."
    ),
    "overview-4": (
        "시연: RAG·지식 그래프 회수 경로·HOLD·최종 확인 화면 및 파이프라인 개요도(선택 1~2점)."
    ),
}


def _table_md_to_text(block: str) -> str:
    rows = []
    for line in block.splitlines():
        if not line.strip().startswith("|"):
            continue
        if re.match(r"^\|\s*[-:]+", line):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells and cells[0] in ("단계", "순서", "지표", "버전"):
            continue
        rows.append(" | ".join(cells))
    return "\n".join(rows)


def build_3_2(submission: str, market_summary: str) -> str:
    econ = extract_block(
        submission,
        r"### 3-2\.",
        r"^---\s*$",
    )
    econ = sanitize_submission(econ)
    bullets = extract_block(
        market_summary,
        r"## 3-2에 그대로 붙여 넣기용",
        r"^## 표:",
    )
    bullets = sanitize_submission(bullets)
    if "**확장 방향 (Phase 2" in bullets:
        bullets = bullets.split("**확장 방향 (Phase 2")[0].strip()
    if "**격벽" in bullets:
        bullets = bullets.split("**격벽")[0].strip()
    parts = [p for p in (econ, bullets) if p]
    return "\n\n".join(parts).strip()


def _short_text(text: str, limit: int = 220) -> str:
    flat = re.sub(r"\s+", " ", text).strip()
    if len(flat) <= limit:
        return flat
    return flat[: limit - 1].rstrip() + "…"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--submission-md", type=Path, default=SUBMISSION)
    ap.add_argument("--market-summary-md", type=Path, default=MARKET_SUMMARY)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    submission = args.submission_md.read_text(encoding="utf-8")
    market_summary = args.market_summary_md.read_text(encoding="utf-8")

    task_pick = sanitize_submission(
        extract_block(submission, r"## 선택한 과제", r"^## 1\.")
    )
    task_pick = re.sub(r"^##\s*선택한 과제\s*", "", task_pick)
    task_pick = task_pick.replace("---", "").strip()
    s_1_1 = sanitize_submission(
        extract_block(submission, r"### 1-1\.", r"### 1-2\.")
    )
    s_1_2 = sanitize_submission(
        extract_block(submission, r"### 1-2\.", r"^---\s*$")
    )
    s_2_1 = sanitize_submission(
        extract_block(submission, r"### 2-1\.", r"### 2-2\.")
    )
    s_2_2 = sanitize_submission(
        extract_block(submission, r"### 2-2\.", r"^---\s*$")
    )
    s_3_1 = sanitize_submission(
        extract_block(submission, r"### 3-1\.", r"### 3-2\.")
    )
    s_3_2 = build_3_2(submission, market_summary)
    s_4_1 = sanitize_submission(
        extract_block(submission, r"### 4-1\.", r"### 4-2\.")
    )
    if s_4_1 and "목소리네트워크" not in s_4_1:
        s_4_1 = "기업명: 주식회사 목소리네트워크\n\n" + s_4_1
    s_4_2 = sanitize_submission(
        extract_block(submission, r"### 4-2\.", r"^---\s*$")
    )
    s_task_optional = OVERVIEW_SUMMARIES["overview-4"]

    s_5_1 = "해당 없음 (수상이력 없음)"
    s_5_2 = (
        "LG H&S 「2026 모두의 챌린지」 1차 평가 통과(2026-05, 사실만 기재). "
        "2차·최종 결과 미확정. 본 과제(정책자금 신청서 자동 생성)와 직접 동일 산출물은 아니며, "
        "RAG·게이트·문서 파이프라인 운영 역량의 참고 이력으로 기재."
    )

    slots = {
        "schema": "hwpx_label_cells_v1",
        "track": "B",
        "boundary_ack": "official 붙임2 양식 fill — verify in Hancom before K-Startup upload",
        "source_title": "(붙임2) AI+ OpenData 챌린지 사업계획서 양식",
        "generated_at_utc": _utc_now(),
        "label_cells": [
            {
                "label": "선택한 과제",
                "table_index": 1,
                "row": 0,
                "col_min": 1,
                "value": task_pick or "① 정책자금 융자 신청서 자동 생성 (중진공, 계약 연계형)",
            }
        ],
        "table_cells": [
            {"table_index": 1, "row": 1, "col": 1, "value": OVERVIEW_SUMMARIES["overview-1"], "section": "overview-1"},
            {"table_index": 1, "row": 2, "col": 1, "value": OVERVIEW_SUMMARIES["overview-2"], "section": "overview-2"},
            {"table_index": 1, "row": 3, "col": 1, "value": OVERVIEW_SUMMARIES["overview-3"], "section": "overview-3"},
            {"table_index": 1, "row": 4, "col": 1, "value": OVERVIEW_SUMMARIES["overview-4"], "section": "overview-4"},
            {"table_index": 1, "row": 5, "col": 1, "value": "해당 없음 (이미지 미첨부)", "section": "overview-5"},
            {"table_index": 1, "row": 6, "col": 1, "value": "해당 없음", "section": "overview-6-title-left"},
            {"table_index": 1, "row": 6, "col": 2, "value": "해당 없음", "section": "overview-6-title-right"},
            {"table_index": 2, "row": 0, "col": 0, "value": "", "section": "image-hint-clear"},
            {"table_index": 3, "row": 0, "col": 0, "value": "", "section": "image-hint-clear"},
            {"table_index": 5, "row": 0, "col": 0, "value": s_1_1, "section": "1-1"},
            {"table_index": 6, "row": 0, "col": 0, "value": s_1_2, "section": "1-2"},
            {"table_index": 8, "row": 0, "col": 0, "value": s_2_1, "section": "2-1"},
            {"table_index": 9, "row": 0, "col": 0, "value": s_2_2, "section": "2-2"},
            {"table_index": 11, "row": 0, "col": 0, "value": s_3_1, "section": "3-1"},
            {"table_index": 12, "row": 0, "col": 0, "value": s_3_2, "section": "3-2"},
            {"table_index": 14, "row": 0, "col": 0, "value": s_4_1, "section": "4-1"},
            {"table_index": 15, "row": 0, "col": 0, "value": s_4_2, "section": "4-2"},
            {"table_index": 18, "row": 0, "col": 0, "value": s_5_1, "section": "5-1"},
            {"table_index": 20, "row": 0, "col": 0, "value": s_5_2, "section": "5-2"},
        ],
        "expected_substrings": [
            "① 정책자금 융자 신청서 자동 생성",
            "이기륜",
            "해당사항 없음",
        ],
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(slots, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    paste_dir = ROOT / "reports/kstartup_opendata327_paste_ready"
    paste_dir.mkdir(parents=True, exist_ok=True)
    one_liner = (
        "중진공 정책자금 융자 신청서 자동 초안: 공고·서식·예시(OpenData) 버전 인덱싱 → "
        "RAG·슬롯 생성 → 근거 미연결 HOLD·재질의·감사로그 → 담당자 최종 확인 후 PDF(hwp 단계적). "
        "범용 폼 매핑이 아닌 규정 준수 문서 보조. AI 자동 제출 없음."
    )
    (paste_dir / "standard_items_one_liner.txt").write_text(one_liner + "\n", encoding="utf-8")
    (paste_dir / "overview_summary_1page.txt").write_text(
        (task_pick + "\n\n" + s_1_1[:2800]).strip() + "\n",
        encoding="utf-8",
    )

    meta = {
        "schema": "opendata_327_hwpx_slots_build_v1",
        "generated_at_utc": _utc_now(),
        "slots_path": args.out.resolve().as_posix(),
        "section_lengths": {
            k: len(v)
            for k, v in {
                "1-1": s_1_1,
                "1-2": s_1_2,
                "2-1": s_2_1,
                "2-2": s_2_2,
                "3-1": s_3_1,
                "3-2": s_3_2,
                "4-1": s_4_1,
                "4-2": s_4_2,
                "5-1": s_5_1,
                "5-2": s_5_2,
            }.items()
        },
    }
    META_OUT.parent.mkdir(parents=True, exist_ok=True)
    META_OUT.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.out.as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
