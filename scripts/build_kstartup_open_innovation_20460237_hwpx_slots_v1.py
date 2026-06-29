#!/usr/bin/env python3
"""OI 20460237 — 붙임1 사업계획서 HWPX slots (공고문 내 양식 + paste SSOT)."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PASTE_DIR = ROOT / "reports/kstartup_open_innovation_20460237_paste_ready"
CONFIG = ROOT / "docs/final/artifacts/kstartup_startup_package_ai_pms_config_v1.json"
ELIGIBILITY = ROOT / "docs/final/artifacts/startup_package_ai_2026_eligibility_v1_latest.json"
DEFAULT_OUT = ROOT / "data/btrack/hwpx_poc/slots_open_innovation_20460237_v1.json"
META_OUT = ROOT / "reports/kstartup_open_innovation_20460237_hwpx_slots_latest.json"
DEMAND_INTRO = ROOT / "docs/final/artifacts/kstartup_oi_demand_task_intro_korea_eval_rpa_v1.json"

# PMS·공고문 2. 협업 과제 개요 (한국평가데이터 · AI RPA)
COLLAB_DEMAND_COMPANY = "한국평가데이터"
COLLAB_TASK_NAME = "AI 기반 RPA를 활용한 수작업 업무 프로세스 자동화"
STRATEGY_FIELD = "AI"
STRATEGY_DETAIL = "AI 에이전트"

PUBLIC_EMAIL = "support@mkmlife.com"
PUBLIC_PHONE = "010-3677-0676"
SUPPORT_FIELD = "지식서비스"
COMPANY_SUMMARY_TABLE = 54


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_paste(name: str) -> str:
    p = PASTE_DIR / name
    if not p.is_file():
        return ""
    return p.read_text(encoding="utf-8").strip()


def _entity() -> dict[str, str]:
    ent: dict[str, str] = {}
    for src in (CONFIG, ELIGIBILITY):
        if not src.is_file():
            continue
        data = json.loads(src.read_text(encoding="utf-8-sig"))
        leg = data.get("legal_entity") or {}
        for k, v in leg.items():
            if k == "incorporation_facts":
                facts = v or {}
                if facts.get("개업연월일"):
                    ent["founding_iso"] = str(facts["개업연월일"])
                continue
            if v and not ent.get(k):
                ent[k] = str(v)
    return ent


def _load_demand_intro() -> dict:
    if not DEMAND_INTRO.is_file():
        return {}
    return json.loads(DEMAND_INTRO.read_text(encoding="utf-8-sig"))


def _founding_kr(iso: str) -> str:
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", iso)
    if not m:
        return ""
    y, mo, d = m.groups()
    return f"{y}년 {int(mo)}월 {int(d)}일"


def _founding_compact(iso: str) -> str:
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", iso)
    if not m:
        return ""
    y, mo, d = m.groups()
    return f"{y}.{int(mo)}.{int(d)}"


def _company_product_line(_majr: str, _tsks_nm: str) -> str:
    return "AI·RPA 기반 문서·업무 프로세스 자동화(OCR·슬롯·HOLD 게이트·Human Gold)"


def _company_features_summary(majr: str, tech: str) -> str:
    lead = (
        "주식회사 목소리네트워크는 AI 에이전트·문서 자동화 PoC를 수행하는 1인 창업기업입니다. "
        f"주요 서비스: {_company_product_line(majr, '')}. "
        "OCR·필드 슬롯·출력보류(HOLD)·감사로그·담당자 최종확인 구조로 수작업·오류 리스크를 줄입니다. "
        "자동 제출·금융 심사 대체를 주장하지 않습니다."
    )
    if tech:
        first = tech.split("\n\n", 1)[0].strip()
        if first and len(first) < 200:
            lead = f"{lead}\n{first}"
    return lead


def build_slots() -> dict:
    ent = _entity()
    demand = _load_demand_intro()
    tsks_nm = _read_paste("step4_tsksNm.txt")
    tsks_ctnt = _read_paste("step4_tsksCtnt.txt")
    majr = _read_paste("step2_majrProd.txt")
    problem = _read_paste("oi_problem_3lines.txt")
    poc = _read_paste("oi_poc_scope.txt")
    tech = _read_paste("oi_tech_differentiation_v1_lock.txt")
    risk = _read_paste("oi_risk_defense_v1_lock.txt")

    d_situation = demand.get("situation") or ""
    d_problem = demand.get("problem") or ""
    d_requirements = demand.get("requirements") or []
    d_criteria = demand.get("startup_criteria") or []
    d_util = demand.get("utilization_plan") or ""
    d_support = demand.get("collab_support") or ""
    d_subtitle = demand.get("task_subtitle") or ""

    intro = (
        f"[수요기업 과제 맥락 — {COLLAB_DEMAND_COMPANY}]\n"
        f"· 과제: {COLLAB_TASK_NAME}\n"
        f"· 세부: {d_subtitle}\n"
        f"· 현황: {d_situation}\n"
        f"· 문제점: {d_problem}\n\n"
        f"[스타트업 제안 개요]\n{tsks_ctnt}\n\n"
        f"[수요 통증(교차 정리)]\n{problem}"
    ).strip()

    req_lines = "\n".join(f"  {i + 1}) {r}" for i, r in enumerate(d_requirements))
    crit_lines = "\n".join(f"  - {c}" for c in d_criteria[:5])

    solution = (
        f"협업 과제({COLLAB_DEMAND_COMPANY} · {COLLAB_TASK_NAME})에 대해, "
        "수요기업 요구사항을 PoC 범위로 구조화하고 단계별로 자동화합니다.\n\n"
        "[수요기업 요구사항 정합 PoC 설계]\n"
        f"{req_lines}\n\n"
        "[제안 접근 — 문서·데이터 파이프라인 + HOLD 게이트]\n"
        "1) FAX/스캔 서식 수신 → OCR·필드 추출(외부/OSS 엔진 연동) → 슬롯 매핑\n"
        "2) 추출값·근거 미연결 시 HOLD·감사로그 → 담당자 재확인 후만 시스템 반영\n"
        "3) 크레탑 검색·상담 시나리오: LLM 요약·메일 초안 생성은 Human Gold 확인 후 송부\n"
        "4) 인입량·응대율·VOC 유형 주간 리포트(조건부 지표, 절대 성과 단정 없음)\n\n"
        f"[PoC 운영 원칙]\n{poc}"
    ).strip()

    deliverables = (
        "협약기간(8개월) 내 산출물(안):\n"
        "1) 공개중지/정보정정 요청 프로세스 As-Is·To-Be 및 필드 매핑 명세 1식\n"
        "2) OCR→슬롯→HOLD→(승인 후) 입력 연동 PoC 모듈 1식\n"
        "3) 검색·상담 메일 초안 생성 샘플 워크플로 1식\n"
        "4) 주간 비용·품질·운영(VOC 요약) 리포트 템플릿 및 샘플 로그\n"
        "5) 담당자 검토용 hwp/pdf 초안 세트\n"
        "현재 개발단계: 아이디어 기획·시제품(PoC) 연동 검증 단계.\n\n"
        "[수요기업 기준요건 대응 요약]\n"
        f"{crit_lines}"
    )

    commercial = (
        f"{COLLAB_DEMAND_COMPANY} {d_util or '내부 고객관리 부서 업무자동화 성능 검증'}.\n"
        f"협업지원: {d_support or '데이터마트·현업 검증 지원(공고 기준)'}.\n"
        "자동 제출·금융 심사 대체·수익 보장을 주장하지 않으며, "
        "PoC 검증 후 정식 지원 프로그램·부가서비스 출시는 성과·조건에 따라 검토합니다."
    )

    team = (
        "대표 이기륜: 한의사(면허)·임상·기업 경영, AI·RAG·게이트 운영 파이프라인 구축.\n"
        "1인 창업기업 기준 PoC 수행·주간 리포트·수요기업 협의 창구 단일화.\n"
        "수상·투자유치 등 해당없음(필요 시 증빙 별첨)."
    )

    schedule = (
        "| 단계 | 추진 내용 | 추진 기간 | 세부 |\n"
        "| --- | --- | --- | --- |\n"
        "| 1 | 현장 진단·FAX/서식 샘플 수집·필드 매핑 | 협약 1~2개월 | 수요기업 현업 인터뷰 |\n"
        "| 2 | OCR·슬롯·HOLD PoC 연동·시나리오 1~2건 | 3~5개월 | 공개중지 요청 자동입력 |\n"
        "| 3 | 검색·메일 초안·VOC 리포트 시범 | 5~7개월 | Human Gold 확인 |\n"
        "| 4 | 성능 검증·종료 보고·후속 검토안 | 8개월 | 주간 리포트 누적 |\n"
        "※ 일정은 협의에 따라 조정 가능."
    )

    budget = (
        "정부지원사업비 집행계획(안, 최대 1.4억원 이내 · 세부는 협약 시 확정):\n"
        "| 비목 | 산출근거 | 금액(원) |\n"
        "| --- | --- | ---: |\n"
        "| 외주용역비 | OCR 튜닝·RPA 시나리오 연동 외주 | 48,000,000 |\n"
        "| 지급수수료 | 클라우드·API·감사로그·OCR API | 22,000,000 |\n"
        "| 재료비 | 익명화 테스트 서식·샘플 데이터 | 10,000,000 |\n"
        "| 인건비 | 대표자·PoC 총괄(자부담 병행) | 40,000,000 |\n"
        "| 합계 | | 120,000,000 |\n"
        "※ 선정평가·협약체결 시 금액·비목 조정 가능. 절대 성과 표현 없음."
    )

    company = ent.get("name", "주식회사 목소리네트워크")
    brn = ent.get("brn", "628-86-01742")
    ceo = ent.get("ceo", "이기륜")
    address = ent.get("address", "경기도 광명시 광명로 880")
    founding_iso = ent.get("founding_iso", "2021-01-05")
    founding_kr = _founding_kr(founding_iso)
    founding_compact = _founding_compact(founding_iso)
    product_line = _company_product_line(majr, tsks_nm)
    features_summary = _company_features_summary(majr, tech)

    summary_table_cells = [
        {"table_index": COMPANY_SUMMARY_TABLE, "row": 0, "col": 1, "value": company},
        {"table_index": COMPANY_SUMMARY_TABLE, "row": 0, "col": 7, "value": ceo},
        {"table_index": COMPANY_SUMMARY_TABLE, "row": 1, "col": 1, "value": SUPPORT_FIELD},
        {"table_index": COMPANY_SUMMARY_TABLE, "row": 1, "col": 7, "value": COLLAB_DEMAND_COMPANY},
        {"table_index": COMPANY_SUMMARY_TABLE, "row": 2, "col": 1, "value": founding_compact},
        {"table_index": COMPANY_SUMMARY_TABLE, "row": 2, "col": 7, "value": PUBLIC_PHONE},
        {"table_index": COMPANY_SUMMARY_TABLE, "row": 3, "col": 1, "value": address},
        {"table_index": COMPANY_SUMMARY_TABLE, "row": 4, "col": 1, "value": product_line},
        {"table_index": COMPANY_SUMMARY_TABLE, "row": 5, "col": 1, "value": features_summary},
        {"table_index": COMPANY_SUMMARY_TABLE, "row": 7, "col": 4, "value": "N"},
        {"table_index": COMPANY_SUMMARY_TABLE, "row": 7, "col": 9, "value": "0"},
        {"table_index": COMPANY_SUMMARY_TABLE, "row": 10, "col": 2, "value": "-"},
        {"table_index": COMPANY_SUMMARY_TABLE, "row": 10, "col": 4, "value": "해당없음"},
        {"table_index": COMPANY_SUMMARY_TABLE, "row": 11, "col": 2, "value": "-"},
        {"table_index": COMPANY_SUMMARY_TABLE, "row": 11, "col": 4, "value": "해당없음"},
        {"table_index": COMPANY_SUMMARY_TABLE, "row": 14, "col": 2, "value": "-"},
        {"table_index": COMPANY_SUMMARY_TABLE, "row": 14, "col": 4, "value": "해당없음"},
        {"table_index": COMPANY_SUMMARY_TABLE, "row": 15, "col": 2, "value": "-"},
        {"table_index": COMPANY_SUMMARY_TABLE, "row": 15, "col": 4, "value": "해당없음"},
        {"table_index": COMPANY_SUMMARY_TABLE, "row": 19, "col": 4, "value": "0"},
        {"table_index": COMPANY_SUMMARY_TABLE, "row": 19, "col": 5, "value": "0.5"},
        {"table_index": COMPANY_SUMMARY_TABLE, "row": 19, "col": 10, "value": "-"},
        {"table_index": COMPANY_SUMMARY_TABLE, "row": 20, "col": 4, "value": "1"},
        {"table_index": COMPANY_SUMMARY_TABLE, "row": 20, "col": 5, "value": "1"},
        {"table_index": COMPANY_SUMMARY_TABLE, "row": 20, "col": 10, "value": "1"},
    ]

    slots = {
        "schema": "hwpx_label_cells_v1",
        "track": "A_draft",
        "program": "민관협력 오픈이노베이션 2026",
        "pms_task_id": "20460237",
        "boundary_ack": "HOLD gate — human review before PMS upload; no auto submit",
        "generated_at_utc": _utc_now(),
        "collab": {
            "demand_company": COLLAB_DEMAND_COMPANY,
            "task_name": COLLAB_TASK_NAME,
            "demand_intro_ssot": str(DEMAND_INTRO.relative_to(ROOT)).replace("\\", "/")
            if DEMAND_INTRO.is_file()
            else "",
        },
        "label_cells": [
            {"label": "명칭", "value": product_line},
            {"label": "소개", "value": intro},
            {"label": "과제해결방안", "value": solution},
            {"label": "기술 경쟁력", "value": tech},
            {"label": "산출물 및 개발단계", "value": deliverables},
            {"label": "사업화 방안", "value": commercial},
            {"label": "기타 특·장점", "value": f"{team}\n\n[리스크 방어 요약]\n{risk}"},
            {"label": "협약기간 내 추진 계획", "value": schedule},
            {"label": "정부지원사업비집행 계획", "value": budget},
        ],
        "table_cells": [
            {"table_index": 34, "row": 0, "col": 2, "value": STRATEGY_FIELD},
            {"table_index": 34, "row": 0, "col": 4, "value": STRATEGY_DETAIL},
            {"table_index": 34, "row": 1, "col": 2, "value": COLLAB_DEMAND_COMPANY},
            {"table_index": 34, "row": 2, "col": 2, "value": COLLAB_TASK_NAME},
            {"table_index": 35, "row": 0, "col": 3, "value": tsks_nm or COLLAB_TASK_NAME},
            {"table_index": 35, "row": 1, "col": 3, "value": company},
            {"table_index": 35, "row": 1, "col": 5, "value": ceo},
            {"table_index": 35, "row": 4, "col": 3, "value": founding_kr},
            {"table_index": 35, "row": 4, "col": 5, "value": "경기도 광명시"},
            {"table_index": 35, "row": 5, "col": 3, "value": brn},
            {"table_index": 35, "row": 6, "col": 3, "value": address},
            {"table_index": 35, "row": 3, "col": 5, "value": PUBLIC_EMAIL},
            *summary_table_cells,
        ],
        "company_summary_table54": {
            "table_index": COMPANY_SUMMARY_TABLE,
            "cells_filled": len(summary_table_cells),
            "support_field": SUPPORT_FIELD,
            "demand_company": COLLAB_DEMAND_COMPANY,
            "revenue_2024_eok": "0.5",
            "revenue_note": "PMS 기업상세 매출 50,000,000원 기준(억원 환산); 사업자등록증·결산으로 최종 확인",
        },
        "human_verify_fields": [
            "대표자 생년월일 (table 35 r2 c3)",
            "연락처 (table 35 r3 c3 · table 54 r2 c7)",
            "법인등록번호 (table 35 r5 c5)",
            "인력 구성 표 (table 35 r9+)",
            "기업현황요약 정량 매출·고용 (table 54 r19-r20 · 사업자등록증·결산 대조)",
            "기업현황요약 협업실적 Y/N·횟수 (table 54 r7 — 사실과 다르면 수정)",
            "제품 및 서비스 사진 (table 54 r5 c7-c9 · 선택 첨부)",
        ],
    }
    return slots


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--meta", type=Path, default=META_OUT)
    args = ap.parse_args()

    slots = build_slots()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(slots, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    meta = {
        "ok": True,
        "schema": "kstartup_open_innovation_20460237_hwpx_slots_build_v1",
        "generated_at_utc": slots["generated_at_utc"],
        "slots_path": str(args.out.relative_to(ROOT)).replace("\\", "/"),
        "label_cell_count": len(slots["label_cells"]),
        "table_cell_count": len(slots["table_cells"]),
        "company_summary_table54_cells": slots.get("company_summary_table54", {}).get("cells_filled"),
        "human_verify_fields": slots["human_verify_fields"],
    }
    args.meta.parent.mkdir(parents=True, exist_ok=True)
    args.meta.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    paste_dir = ROOT / "reports/kstartup_open_innovation_20460237_paste_ready"
    paste_dir.mkdir(parents=True, exist_ok=True)
    cs = slots.get("company_summary_table54") or {}
    summary_lines = [
        "기업현황요약 (PMS·HWP table 54 동일 항목)",
        f"기업명: {next((c['value'] for c in slots['table_cells'] if c.get('table_index') == COMPANY_SUMMARY_TABLE and c.get('row') == 0 and c.get('col') == 1), '')}",
        f"대표자: {next((c['value'] for c in slots['table_cells'] if c.get('table_index') == COMPANY_SUMMARY_TABLE and c.get('row') == 0 and c.get('col') == 7), '')}",
        f"지원분야: {cs.get('support_field', '')}",
        f"수요기업: {cs.get('demand_company', '')}",
        f"창업일: {next((c['value'] for c in slots['table_cells'] if c.get('table_index') == COMPANY_SUMMARY_TABLE and c.get('row') == 2 and c.get('col') == 1), '')}",
        f"연락처: {next((c['value'] for c in slots['table_cells'] if c.get('table_index') == COMPANY_SUMMARY_TABLE and c.get('row') == 2 and c.get('col') == 7), '')}",
        f"사업장 주소: {next((c['value'] for c in slots['table_cells'] if c.get('table_index') == COMPANY_SUMMARY_TABLE and c.get('row') == 3 and c.get('col') == 1), '')}",
        f"사업분야(주요 생산품): {next((c['value'] for c in slots['table_cells'] if c.get('table_index') == COMPANY_SUMMARY_TABLE and c.get('row') == 4 and c.get('col') == 1), '')}",
        f"기업 및 제품서비스 특징: {next((c['value'] for c in slots['table_cells'] if c.get('table_index') == COMPANY_SUMMARY_TABLE and c.get('row') == 5 and c.get('col') == 1), '')}",
        "협업 경험: N / 횟수 0 / 대·중견 협업 실적 해당없음",
        f"정량 매출(억원): 2023=0 · 2024={cs.get('revenue_2024_eok', '-')} · 2025=- (human 확인)",
        "정량 고용(명): 2023=1 · 2024=1 · 2025=1",
        f"※ {cs.get('revenue_note', '')}",
    ]
    (paste_dir / "company_summary_table54_paste.txt").write_text(
        "\n".join(summary_lines) + "\n", encoding="utf-8"
    )
    print(json.dumps(meta, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
