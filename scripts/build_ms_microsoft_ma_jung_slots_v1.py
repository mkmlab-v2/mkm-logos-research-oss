#!/usr/bin/env python3
"""Build slots JSON for ms microsoft ma-jung HWPX fill from reports/ms_rq019_paste_ready SSOT."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(ROOT))
PASTE = ROOT / "reports/ms_rq019_paste_ready"
OUT = ROOT / "data/btrack/hwpx_poc/slots_ms_microsoft_ma_jung_v1.json"
META = ROOT / "reports/hwpx_poc/build_ms_microsoft_ma_jung_slots_latest.json"

from scripts.ms_ma_jung_submission_sanitize_v1 import (  # noqa: E402
    EXTERNAL_DISCLAIMER,
    external_finops_blurb,
    external_k1_body,
    external_k2_body,
    external_k3_body,
    sanitize_submission_text,
    submission_agreement_schedule_blurb,
    submission_budget_blurb,
    submission_collab_roadmap_visual,
    submission_feasibility_summary,
    submission_growth_summary,
    submission_competitor_comparison,
    submission_method_implementation_detail,
    submission_ms_ac_deliverable_map,
    submission_problem_body,
    submission_problem_summary,
    submission_roadmap_goals_only,
)
from scripts.ms_hwpx_cjk_billing_footnote_v1 import (  # noqa: E402
    cjk_billing_footnote_submission_ko,
    write_footnote_paste_file,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _paste_body(fname: str) -> str:
    path = PASTE / fname
    if not path.is_file():
        raise SystemExit(f"missing paste SSOT: {path}")
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    if lines and lines[0].startswith("["):
        lines = lines[1:]
    while lines and not lines[0].strip():
        lines = lines[1:]
    return "\n".join(lines).strip()


def _short(text: str, max_chars: int = 1200) -> str:
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def main() -> int:
    k1 = external_k1_body(_paste_body("k1_problem_paste.txt"))
    k2 = external_k2_body(_paste_body("k2_method_paste.txt"))
    k3 = external_k3_body(_paste_body("k3_differentiation_paste.txt"))
    moat = sanitize_submission_text(_paste_body("technical_moat_sector_paste.txt"))
    write_footnote_paste_file()
    disclaimer = sanitize_submission_text(
        EXTERNAL_DISCLAIMER + "\n\n" + cjk_billing_footnote_submission_ko()
    )
    finops_public = external_finops_blurb()

    ann_header = (
        "공고 제2026-329호 [마중] Microsoft AC · 클라우드 기반 B2B 솔루션 · "
        "협약 5개월(’26.7~’26.11 예정) · 총사업비 288백만(정부 200·현금 33·현물 55)."
    )
    overview = _short(
        ann_header
        + "\n\nMKM Trust Packet — 엔터프라이즈 AI handoff 시 토큰·지연·감사 비용을 줄이는 "
        "inter-agent wire PoC. 패킷 기반 roundtrip·주간 자동 검증. PoC 범위이며 상용 SLA·실거래 보장은 하지 않습니다.",
        900,
    )
    scope = (
        "클라우드 기반 B2B 솔루션(inter-agent wire·Trust Packet) · "
        "Azure·FinOps·감사 PoC · 공고 [마중] AC 정합"
    )
    ms_collab = _short(
        ann_header
        + "\n\n[마중] Microsoft AC: Azure·클라우드 크레딧·Responsible AI·ISV 실사·"
        "멘토링·네트워킹(공고 범위). PoC는 비프로덕션·법무·대표 승인 후 확장.\n\n"
        + moat,
        2200,
    )
    # table_index map (Fact-Lock probe 2026-05-21): narrative 1x1 cells — NOT T13–15 (양식 ※ 힌트만).
    # T12 개요 · T19 1-1 배경 · T20 1-2 시장 · T22 2-1 준비 · T23 2-2 방법 · T25 수익 · T27 3-x 차별 · T48–50 MS 협업.
    narrative_k1 = _short(
        submission_problem_body(k1) + "\n\n" + submission_competitor_comparison(),
        3000,
    )
    narrative_k2 = _short(k2 + "\n\n" + submission_method_implementation_detail(), 3200)
    narrative_k3 = _short(k3, 1800)
    narrative_market = _short(
        "목표시장: 엔터프라이즈·클라우드 B2B — AI 에이전트·다중 handoff를 운영하는 "
        "플랫폼·ISV·내부 자동화 팀. 요구: 토큰 비용 통제(FinOps), 감사 가능 패킷, 단계적 PoC. "
        "경쟁: 범용 LLM API만으로는 roundtrip·격벽 증거 부족.\n\n" + k1,
        2200,
    )
    narrative_ready = sanitize_submission_text(
        _short(
            "준비 현황: Trust Packet(v2)·연동 프로파일·개발 마일스톤 완료. "
            "주간 자동 검증·정적 시연 페이지. 벤치 49.1%·Jaccard 0.873(40건·41658 lexicon)는 동일 조건 실측만 표기.\n\n"
            + finops_public,
            1800,
        )
    )
    narrative_revenue = sanitize_submission_text(
        _short(
            "수익 모델: B2B PoC·파일럿 라이선스·클라우드·API 번들. "
            "협약기간 내 파일럿 LOI·과금 설계 검토, 11월 이후 단계적 상용화 로드맵. "
            "벤치 49.1%(40건)는 동일 조건 벤치마크로만 표기.",
            1200,
        )
    )
    narrative_roadmap_331 = submission_roadmap_goals_only()
    narrative_agreement_schedule = submission_agreement_schedule_blurb()
    narrative_budget = submission_budget_blurb()
    narrative_funding_history = sanitize_submission_text(
        "기존: 자체 연구·인프라. 본 과제: B2B 연동 PoC·감사 패키지·문서화 중심. "
        "투자 연동은 별도 검토."
    )
    narrative_team = _short(
        "대표: Trust Packet·FinOps PoC 총괄(학력·경력·연락처 기재). "
        "소규모 운영: 자동 검증·운영 자동화.",
        1200,
    )
    narrative_hiring = (
        "협약기간 추가 채용: PoC 확대 시 S/W·DevOps 0–1명 검토(미확정). "
        "현재는 대표 중심 + 자동화; 인력 표는 실명·역량으로 기재."
    )
    narrative_partners = _short(
        "협력: Microsoft Azure(FinOps·Responsible AI)·ISV 실사·멘토링(공고 AC). "
        "PoC 호스팅·감사 패키지·검증 리포트를 단계적으로 교환합니다.\n\n"
        + submission_ms_ac_deliverable_map()
        + "\n\n"
        + _short(moat, 900),
        2800,
    )
    narrative_esg = sanitize_submission_text(
        "E: 토큰·불필요 LLM 호출 절감(설명용, 제로비용 단정 없음). "
        "S: B2B PoC 투명·면책·법무·대표 승인. G: 1인 기업·검증 증빙·영역 분리 운영."
    )
    product_blurb = (
        "도메인 라우터·Trust Packet 기반 inter-agent handoff 압축/복원 PoC "
        "(감사·FinOps·주간 스모크)"
    )
    deliverables_blurb = (
        "협약 5개월 내: Trust Packet v2·OpenAPI·자동 검증·정적 시연·BM/사업화 증빙(공고 AC)"
    )
    final_product = (
        "최종(협약 말): B2B wire PoC 패키지·OpenAPI·검증 리포트·시연·지재권(해당 시)·집행 증빙 "
        "— [마중] 클라우드 B2B·Microsoft 협업 범위"
    )
    section1_blurb = submission_problem_summary()
    section2_blurb = submission_feasibility_summary()
    section3_blurb = submission_growth_summary()
    collab_roadmap_visual = submission_collab_roadmap_visual()
    image_note = (
        "물리 제품 사진 대신: Trust Packet 아키텍처 다이어그램·정적 시연(showroom) 캡처 첨부 예정 "
        "(협약기간). 설계도=OpenAPI·wire 시퀀스."
    )
    ms_cloud_rows = {
        "cloud_use": (
            "[마중·AC] 공고: Microsoft 클라우드·개발 tool·크레딧 무상/할인(별첨). "
            "PoC: 비프로덕션 stub·TLS·실매매 키 미포함."
        ),
        "cloud_link": (
            "모집분야 「클라우드 기반 B2B 솔루션」= Trust Packet·inter-agent wire·Azure FinOps."
        ),
        "cloud_scenario": (
            "5개월: compress/expand PoC → expand 후 LLM handoff · Responsible AI 관측 · "
            "글로벌기업 멘토링·세미나(공고 지원 프로그램)."
        ),
        "ms_outcomes": (
            "성과(안): roundtrip 자동 검증·주간 점검·B2B 파일럿 LOI. "
            "49.1%는 40건 벤치만 표기(상용 단정·감액 전제 없음)."
        ),
        "b2b_plan": (
            "AC: Azure·ISV PoC → 법무·대표 승인 → 네트워킹/마케팅(공고). "
            "단계적 B2B 상용화."
        ),
    }
    masked_cv = "소프트웨어·AI 관련 학력 및 B2B PoC·클라우드 솔루션 경력"
    company_name = "(K-Startup 신청 법인명과 동일)"
    market_domestic = [
        (1, "국내 B2B ISV·AI 플랫폼", "Trust Packet PoC", "'26.7~8", "파일럿 N", "협의", "(감액 전)"),
        (2, "엔터프라이즈 자동화", "wire API", "'26.9", "-", "협의", "-"),
        (3, "범위 외", "B2C 앱스토어", "-", "-", "-", "-"),
        (4, "범위 외", "무료 회원 모델", "-", "-", "-", "-"),
    ]
    market_global = [
        (1, "Microsoft/Azure 채널", "B2B wire PoC", "'26.10", "-", "협의", "(공고 네트워킹)"),
        (2, "해외 ISV(검토)", "PoC·FinOps", "'26.11", "-", "협의", "-"),
        (3, "범위 외", "-", "-", "-", "-", "-"),
        (4, "범위 외", "-", "-", "-", "-", "-"),
    ]
    def _won(amount: int) -> str:
        return f"{amount:,}"

    # 신청현황 T4 (table_index 4): 병합 셀 — 기간열(3–8)에 동일 값 반복 시 마지막만 보임 → col3·col10 앵커만.
    budget_t4_rows = (
        (5, "200", "정부지원"),
        (6, "33", "자기부담 현금"),
        (7, "55", "자기부담 현물"),
    )
    # T37 (table_index 37): col0 비목은 양식 유지, col1–4만 채움
    budget_t37_lines: list[tuple[int, str, int, int]] = [
        (2, "5개월 Azure·API·자동 검증 CI (FinOps PoC)", 25_000_000, 0),
        (3, "Trust Packet v2·wire·OpenAPI·회귀 52종", 125_000_000, 0),
        (4, "사업계획·지재권·Responsible AI 검수", 25_000_000, 0),
        (5, "대표·내부 R&D (협약 5개월, 현물)", 0, 55_000_000),
        (
            6,
            "글로벌 ISV 실사·클라우드 보안·법무 자문(5개월, Microsoft·Azure 정합 검토 포함)",
            25_000_000,
            0,
        ),
    ]
    budget_t37_totals = (200_000_000, 55_000_000, 288_000_000)

    extra_table_cells: list[dict] = [
        {"table_index": 6, "row": 0, "col": 0, "value": final_product},
        {"table_index": 7, "row": 0, "col": 0, "value": "법인사업자 (K-Startup 신청 시 최종 확인)"},
        {"table_index": 10, "row": 0, "col": 0, "value": "Azure·Entra·FinOps — inter-agent handoff PoC"},
        {"table_index": 11, "row": 0, "col": 0, "value": "B2B wire compression API·감사 패킷"},
        {"table_index": 13, "row": 0, "col": 0, "value": section1_blurb, "section": "§1 요약블록"},
        {"table_index": 14, "row": 0, "col": 0, "value": section2_blurb, "section": "§2 요약블록"},
        {"table_index": 15, "row": 0, "col": 0, "value": section3_blurb, "section": "§3 요약블록"},
        {"table_index": 16, "row": 0, "col": 0, "value": image_note},
        {"table_index": 17, "row": 0, "col": 0, "value": image_note},
        {"table_index": 9, "row": 1, "col": 1, "value": overview, "section": "개요 아이템"},
        {"table_index": 9, "row": 2, "col": 1, "value": _short(k1, 1200), "section": "개요 배경"},
        {
            "table_index": 9,
            "row": 3,
            "col": 1,
            "value": _short(narrative_ready + "\n\n" + k2[:500], 1500),
            "section": "개요 현황",
        },
        {
            "table_index": 9,
            "row": 4,
            "col": 1,
            "value": _short(narrative_market[:800] + "\n\n" + narrative_k3[:500], 1500),
            "section": "개요 전략",
        },
        {"table_index": 9, "row": 6, "col": 1, "value": "Trust Packet 아키텍처(첨부)"},
        {"table_index": 9, "row": 6, "col": 2, "value": "wire 시퀀스·OpenAPI(첨부)"},
        {"table_index": 9, "row": 6, "col": 3, "value": "정적 시연 capture(첨부)"},
        {"table_index": 9, "row": 6, "col": 4, "value": "검증·감사 요약(첨부)"},
        {"table_index": 8, "row": 1, "col": 2, "value": ms_cloud_rows["cloud_use"]},
        {"table_index": 8, "row": 2, "col": 2, "value": ms_cloud_rows["cloud_link"]},
        {"table_index": 8, "row": 3, "col": 2, "value": ms_cloud_rows["cloud_scenario"]},
        {"table_index": 8, "row": 4, "col": 2, "value": ms_cloud_rows["ms_outcomes"]},
        {"table_index": 8, "row": 5, "col": 2, "value": ms_cloud_rows["b2b_plan"]},
        {"table_index": 35, "row": 0, "col": 0, "value": narrative_budget},
        {"table_index": 36, "row": 2, "col": 0, "value": "288,000,000원", "section": "T36 집행요약 총"},
        {"table_index": 36, "row": 2, "col": 1, "value": "200,000,000원", "section": "T36 정부"},
        {"table_index": 36, "row": 2, "col": 2, "value": "33,000,000원", "section": "T36 현금"},
        {"table_index": 36, "row": 2, "col": 3, "value": "55,000,000원", "section": "T36 현물"},
        {"table_index": 36, "row": 3, "col": 0, "value": "100%", "section": "T36 비율"},
        {"table_index": 36, "row": 3, "col": 1, "value": "69.4%", "section": "T36 비율 정부"},
        {"table_index": 36, "row": 3, "col": 2, "value": "11.5%", "section": "T36 비율 현금"},
        {"table_index": 36, "row": 3, "col": 3, "value": "19.1%", "section": "T36 비율 현물"},
        {"table_index": 5, "row": 2, "col": 3, "value": company_name},
        {"table_index": 5, "row": 2, "col": 4, "value": company_name},
        {"table_index": 5, "row": 7, "col": 1, "value": "대표"},
        {"table_index": 5, "row": 7, "col": 2, "value": "Trust Packet·PoC 총괄"},
        {"table_index": 5, "row": 7, "col": 4, "value": masked_cv},
        {"table_index": 5, "row": 7, "col": 5, "value": masked_cv},
        {"table_index": 5, "row": 7, "col": 6, "value": masked_cv},
        {"table_index": 5, "row": 8, "col": 1, "value": "(추가 인력 없음)"},
        {"table_index": 5, "row": 8, "col": 2, "value": "자동화·검증"},
        {"table_index": 5, "row": 8, "col": 4, "value": "해당 없음"},
        {"table_index": 41, "row": 0, "col": 3, "value": "0"},
        {"table_index": 41, "row": 0, "col": 6, "value": "0"},
        {"table_index": 41, "row": 2, "col": 1, "value": "대표"},
        {"table_index": 41, "row": 2, "col": 2, "value": "Trust Packet·FinOps PoC"},
        {"table_index": 41, "row": 2, "col": 5, "value": masked_cv},
        {"table_index": 41, "row": 2, "col": 6, "value": masked_cv},
        {"table_index": 41, "row": 2, "col": 7, "value": masked_cv},
        {"table_index": 43, "row": 1, "col": 1, "value": "PoC scale-up 시 DevOps(검토)"},
        {"table_index": 43, "row": 1, "col": 2, "value": masked_cv},
        {"table_index": 43, "row": 1, "col": 3, "value": "미확정"},
        {"table_index": 45, "row": 1, "col": 1, "value": "Microsoft Azure"},
        {"table_index": 45, "row": 1, "col": 2, "value": "FinOps·Responsible AI·클라우드 PoC"},
        {"table_index": 45, "row": 1, "col": 3, "value": "ISV 실사·wire PoC 호스팅·아티팩트 교환"},
        {"table_index": 45, "row": 1, "col": 4, "value": "협약기간"},
        {"table_index": 45, "row": 2, "col": 1, "value": "(파일럿 고객 NDA 검토)"},
        {"table_index": 45, "row": 2, "col": 2, "value": "B2B handoff 검증"},
        {"table_index": 45, "row": 2, "col": 3, "value": "wire roundtrip·감사 리포트"},
        {"table_index": 45, "row": 2, "col": 4, "value": "협의"},
    ]
    for row_vals in market_domestic:
        row_i = row_vals[0]
        for col_i, val in enumerate(row_vals[1:], start=1):
            extra_table_cells.append(
                {"table_index": 26, "row": row_i, "col": col_i, "value": val}
            )
    for row_vals in market_global:
        row_i = row_vals[0]
        for col_i, val in enumerate(row_vals[1:], start=1):
            extra_table_cells.append(
                {"table_index": 28, "row": row_i, "col": col_i, "value": val}
            )

    for row_i, amount_m, _label in budget_t4_rows:
        extra_table_cells.append(
            {
                "table_index": 4,
                "row": row_i,
                "col": 3,
                "value": f"{amount_m}백만원",
                "section": "T4 사업비",
            }
        )
    # T4 합계열(col10) 세로 병합 — 총사업비 288만원 1회만(00백만원 placeholder 대체).
    for col_i in (10, 11):
        extra_table_cells.append(
            {
                "table_index": 4,
                "row": 5,
                "col": col_i,
                "value": "288백만원",
                "section": "T4 총사업비 합계",
            }
        )
    for row_i, rationale, gov_won, inkind_won in budget_t37_lines:
        total_won = gov_won + inkind_won
        extra_table_cells.extend(
            [
                {"table_index": 37, "row": row_i, "col": 1, "value": rationale, "section": "T37 집행"},
                {
                    "table_index": 37,
                    "row": row_i,
                    "col": 2,
                    "value": _won(gov_won) if gov_won else "-",
                },
                {
                    "table_index": 37,
                    "row": row_i,
                    "col": 3,
                    "value": _won(inkind_won) if inkind_won else "",
                },
                {"table_index": 37, "row": row_i, "col": 4, "value": _won(total_won)},
            ]
        )
    gov_t, inkind_t, sum_t = budget_t37_totals
    extra_table_cells.extend(
        [
            {"table_index": 37, "row": 7, "col": 2, "value": _won(gov_t)},
            {"table_index": 37, "row": 7, "col": 3, "value": _won(inkind_t)},
            {
                "table_index": 37,
                "row": 7,
                "col": 4,
                "value": _won(sum_t),
            },
        ]
    )
    extra_table_cells.append(
        {
            "table_index": 3,
            "row": 0,
            "col": 0,
            "value": _short(
                "신청: 공고 제2026-329호 [마중] Microsoft AC. "
                "총사업비 288백만(정부 200·현금 33·현물 55) — 아래 신청현황·집행표 참고.",
                1200,
            ),
        }
    )

    slots = {
        "schema": "hwpx_label_cells_v1",
        "track": "B",
        "boundary_ack": "K-Startup sanitize v3.2 — body enrich + CJK billing footnote (49.1% Policy A)",
        "cjk_billing_footnote_paste": "reports/hwpx_poc/ms_cjk_billing_footnote_paste_v1.txt",
        "cjk_billing_mode_note": "MKM_IJEOMA_CJK_BILLING_MODE=1 → o200k_tight; daily ascii_compact",
        "source_title": "별첨1-2. (마이크로소프트) 마중 프로그램 사업계획서",
        "generated_at_utc": _utc_now(),
        "narrative_table_map_note": "T9 개요·T8 MS특화·T13–17 요약·T19+ 본문·T26/28 시장·T41/43/45 인력·협력.",
        "fill_by_path": {
            "명     칭 > right": "MKM Trust Packet (inter-agent wire PoC)",
        },
        "label_cells": [
            {
                "label": "창업아이템명",
                "table_index": 5,
                "row": 0,
                "col_min": 1,
                "value": "MKM Trust Packet — inter-agent wire compression (감사 가능 PoC)",
            },
            {
                "label": "기업명",
                "table_index": 5,
                "row": 2,
                "col_min": 1,
                "value": company_name,
            },
            {
                "label": "신청 주관기관명",
                "table_index": 4,
                "row": 0,
                "col_min": 1,
                "value": "(K-Startup 신청 후 자동 기재 — 수동 확인)",
            },
        ],
        "table_cells": [
            {"table_index": 5, "row": 0, "col": 3, "value": product_blurb, "section": "일반현황 창업아이템"},
            {"table_index": 5, "row": 1, "col": 3, "value": deliverables_blurb, "section": "일반현황 산출물"},
            {
                "table_index": 5,
                "row": 3,
                "col": 6,
                "value": "(K-Startup 신청 사업장 주소와 동일)",
                "section": "사업장 소재지",
            },
            {"table_index": 9, "row": 0, "col": 4, "value": scope},
            {"table_index": 12, "row": 0, "col": 0, "value": overview},
            {"table_index": 19, "row": 0, "col": 0, "value": narrative_k1, "section": "1-1 배경"},
            {"table_index": 20, "row": 0, "col": 0, "value": narrative_market, "section": "1-2 시장"},
            {"table_index": 22, "row": 0, "col": 0, "value": narrative_ready, "section": "2-1 준비"},
            {"table_index": 23, "row": 0, "col": 0, "value": narrative_k2, "section": "2-2 방법"},
            {"table_index": 25, "row": 0, "col": 0, "value": narrative_revenue, "section": "수익모델"},
            {"table_index": 27, "row": 0, "col": 0, "value": narrative_k3, "section": "3-x 차별"},
            {
                "table_index": 29,
                "row": 0,
                "col": 0,
                "value": narrative_roadmap_331,
                "section": "3-3-1 종합목표",
            },
            {
                "table_index": 30,
                "row": 1,
                "col": 1,
                "value": "wire 코어·Trust Packet v2 동결",
                "section": "3-3-1 일정",
            },
            {"table_index": 30, "row": 1, "col": 2, "value": "'26.7~8 (5개월 중)"},
            {
                "table_index": 30,
                "row": 1,
                "col": 3,
                "value": "compress/expand·roundtrip 검증·문서화",
            },
            {
                "table_index": 30,
                "row": 2,
                "col": 1,
                "value": "Azure·ISV 실사 패키지",
            },
            {"table_index": 30, "row": 2, "col": 2, "value": "'26.9"},
            {
                "table_index": 30,
                "row": 2,
                "col": 3,
                "value": "FinOps·Responsible AI 정합·아티팩트",
            },
            {
                "table_index": 30,
                "row": 3,
                "col": 1,
                "value": "정적 시연·서류 갱신",
            },
            {"table_index": 30, "row": 3, "col": 2, "value": "'26.10"},
            {"table_index": 30, "row": 3, "col": 3, "value": "정적 시연·사업계획서 검수"},
            {
                "table_index": 30,
                "row": 4,
                "col": 1,
                "value": "법무·대표 승인·대외 PoC 검토",
            },
            {"table_index": 30, "row": 4, "col": 2, "value": "'26.11(협약 종료)"},
            {
                "table_index": 30,
                "row": 4,
                "col": 3,
                "value": "법무·대표 승인 후 대외 PoC 제출",
            },
            {
                "table_index": 31,
                "row": 0,
                "col": 0,
                "value": narrative_agreement_schedule,
                "section": "3-3-2 협약기간 일정",
            },
            {
                "table_index": 32,
                "row": 1,
                "col": 1,
                "value": "v2 stub·OpenAPI draft 정합",
            },
            {"table_index": 32, "row": 1, "col": 2, "value": "'26.7"},
            {"table_index": 32, "row": 1, "col": 3, "value": "Trust Packet 계약·예제 JSON"},
            {
                "table_index": 32,
                "row": 2,
                "col": 1,
                "value": "weekly smoke·metering",
            },
            {"table_index": 32, "row": 2, "col": 2, "value": "'26.7~9"},
            {"table_index": 32, "row": 2, "col": 3, "value": "주간 검증·모니터링"},
            {
                "table_index": 32,
                "row": 3,
                "col": 1,
                "value": "품질·비용 게이트 유지",
            },
            {"table_index": 32, "row": 3, "col": 2, "value": "'26.10"},
            {
                "table_index": 32,
                "row": 3,
                "col": 3,
                "value": "선택 기능은 벤치 기준 별도 검증",
            },
            {
                "table_index": 32,
                "row": 4,
                "col": 1,
                "value": "제출 HWPX·면책 검수",
            },
            {"table_index": 32, "row": 4, "col": 2, "value": "'26.11"},
            {"table_index": 32, "row": 4, "col": 3, "value": "최종 검수·제출"},
            {
                "table_index": 33,
                "row": 0,
                "col": 0,
                "value": narrative_budget,
                "section": "사업비 집행",
            },
            {
                "table_index": 38,
                "row": 0,
                "col": 0,
                "value": narrative_funding_history,
                "section": "자금조달 이력",
            },
            {
                "table_index": 40,
                "row": 0,
                "col": 0,
                "value": narrative_team,
                "section": "4-1-1 대표 역량",
            },
            {
                "table_index": 42,
                "row": 0,
                "col": 0,
                "value": narrative_hiring,
                "section": "4-1-2 채용",
            },
            {
                "table_index": 44,
                "row": 0,
                "col": 0,
                "value": narrative_partners,
                "section": "4-2 협력",
            },
            {
                "table_index": 46,
                "row": 0,
                "col": 0,
                "value": narrative_esg,
                "section": "4-3 ESG",
            },
            {"table_index": 48, "row": 0, "col": 0, "value": ms_collab},
            {
                "table_index": 49,
                "row": 0,
                "col": 0,
                "value": sanitize_submission_text(
                    _short(
                        "핵심성과: 에이전트 간 연동 PoC·감사 패키지·FinOps 관측. "
                        "전략: Azure·Responsible AI 정합·단계적 파일럿 확대.\n\n"
                        + k3,
                        2200,
                    )
                ),
            },
            {"table_index": 50, "row": 0, "col": 0, "value": collab_roadmap_visual},
        ]
        + extra_table_cells,
        "footer_table_cells": [
            {
                "table_index": 2,
                "row": 0,
                "col": 0,
                "value": disclaimer,
                "mode": "set",
                "note": "면책 + CJK 청구 각주(제출용, Golden 49.1% Policy A)",
            }
        ],
        "expected_substrings": [
            "MKM Trust Packet",
            "제2026-329호",
            "[마중]",
            "클라우드 기반 B2B",
            "5개월",
            "inter-agent wire",
        ],
        "announcement_pointer": "reports/ms_rq019_paste_ready/announcement_2026_329_ma_jung_v1.txt",
        "narrative_paste_pointers": {
            "hwpx_bundle": "reports/ms_rq019_paste_ready/hwpx_fact_lock_5blocks_v1.txt",
            "readiness": "reports/ms_rq019_paste_pack_readiness_latest.json",
        },
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(slots, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    meta = {
        "schema": "build_ms_microsoft_ma_jung_slots_v1",
        "generated_at_utc": _utc_now(),
        "out": str(OUT.relative_to(ROOT)).replace("\\", "/"),
        "table_cells_count": len(slots["table_cells"]),
        "ok": True,
    }
    META.parent.mkdir(parents=True, exist_ok=True)
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
