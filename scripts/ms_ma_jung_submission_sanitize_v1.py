#!/usr/bin/env python3
"""Sanitize MS ma-jung HWPX slot text for K-Startup external submission (not internal paste SSOT)."""

from __future__ import annotations

import re

# One-line public disclaimer (no 성경/명리/사상, no Track A/B, no [HYPO]).
EXTERNAL_DISCLAIMER = (
    "본 계획서·시연 자료는 클라우드 B2B PoC 범위이며, 상용 SLA·투자 수익·자동 매매를 보장하지 않습니다. "
    "압축 성능 수치(약 47.5%, Jaccard 약 0.89)는 동일 조건 40건 벤치마크 기준이며, "
    "모든 고객·실시간 요청에 동일하게 적용된다고 단정하지 않습니다."
)

_ANN_BLOCK_RE = re.compile(
    r"근거:\s*중소벵처기업부 공고 제2026-329호[\s\S]*?(?=\n\n[A-Za-z가-힣【]|\Z)",
    re.MULTILINE,
)

_REPLACEMENTS: list[tuple[str, str]] = [
    ("[HYPO]", ""),
    ("B-track↔Track A·실매매 자동 합선 없음", "연구·운영·실거래 영역 분리"),
    ("B-track↔Track A", "연구·운영 분리"),
    ("B-track ", "연구 "),
    ("B-track", "연구 검증"),
    ("Track A ", "운영 벤치 "),
    ("Track A", "운영 벤치"),
    ("Track B", "연구 검증"),
    ("pytest", "자동 회귀 검증"),
    ("exit 0", "검증 통과"),
    ("M1–M28 CLOSED", "개발 마일스톤 완료"),
    ("M1 ", "1단계 "),
    ("M2 ", "2단계 "),
    ("M3 ", "3단계 "),
    ("M4 ", "4단계 "),
    ("M5 ", "5단계 "),
    ("RQ-019 ", ""),
    ("Fact-Lock", ""),
    ("fact-lock", ""),
    ("SSOT", "기준"),
    ("human review gate", "법무·대표 검토"),
    ("human gate", "법무·대표 승인"),
    ("Zero Leak", ""),
    ("wire OFF", ""),
    ("wire [HYPO]", "선택적 연구 기능"),
    ("auto-promote", "자동 상용 전환"),
    ("auto_promote", "자동 상용 전환"),
    ("T37:", ""),
    ("T4)", ""),
    ("(+현금33M→총288M, T4)", ""),
    ("(+현금33M→총288M)", ""),
    ("제출 전 마스킹·실명 기재", "학력·경력 기재"),
    ("제출 전 마스킹 정책 적용", ""),
    ("(제출 전 실명·마스킹 정책 적용)", ""),
    ("MKM (예시 — 제출 전 실명·마스킹 정책 적용)", "[기업명 기재]"),
    ("MKM (제출 전 실명·마스킹)", "[기업명 기재]"),
    ("(제출 전 실주소·마스킹 정책 적용)", "[사업장 주소 기재]"),
    ("(예시 대체)", ""),
    ("예시 인력 표는 제출 전 실명·역량으로 교체", "인력 표는 실명·역량으로 기재"),
    ("※ 하단 집행 표(T37) 금액은 제출 전 확정·재기재.", ""),
    ("showroom HTML·HWPX·paste Fact-Lock", "정적 시연·사업계획서"),
    ("HWPX·면책·마스킹 검수 후", "사업계획·면책 검수 후"),
    ("마스킹·15p·한컴 최종", "최종 검수"),
    ("[구현·계약 SSOT — 대외 경로 비노출]", ""),
    ("paste·MS 본문에만 Fact-Lock 수치", ""),
    ("성경·명리·사상 렌즈는 보조 해설이며 실전 주문 트리거가 아닙니다.", ""),
    ("성경·명리·사상", ""),
    ("Seed·Label·Formula·Field(3+1)", "데이터·정책·운영 환경"),
    ("FAIL-COMP-004", ""),
    ("| 레인 | 역할 | 대외·서류 |", ""),
    ("|------|------|-----------|", ""),
    ("MKM-V2-Wire-Shadow-Metering-Weekly(Ready)", "주간 운영·비용 점검"),
    ("MKM-V2-Wire", "주간 운영 점검"),
    ("research_only", "연구 전용"),
    ("bulkhead", "운영 격리"),
    ("hydration", "데이터 동기화"),
    ("shadow metering", "비용·사용량 관측"),
    ("active KPI", "운영 지표"),
    ("showroom HTML", "정적 시연 페이지"),
    ("paste Fact-Lock", "사업계획서 검수"),
    ("human gate", "법무·대표 승인"),
    ("auto-promote", "자동 상용 전환"),
    ("auto_promote", "자동 상용 전환"),
    ("OI·", ""),
    ("wire OFF", ""),
    ("wire profile", "연동 프로파일"),
    ("wire PoC", "B2B 연동 PoC"),
    ("wire API", "B2B 연동 API"),
    ("wire roundtrip", "패킷 왕복 검증"),
    ("wire 시퀀스", "연동 시퀀스"),
    ("inter-agent wire", "에이전트 간 연동"),
    ("codebook shard", "도메인 정책"),
    ("residual_meta", "메타데이터"),
    ("evaluate_report", "품질 평가 리포트"),
    ("identity fallback", "기본값 복귀"),
    (".env", "환경 설정"),
    ("repo 경로", "내부 저장소"),
    ("내부 repo", "내부 저장소"),
    ("Fact-Lock 증거", "검증 증빙"),
    ("격벽", "영역 분리"),
    ("마스킹·15p·한컴 최종", "최종 검수"),
    ("[기업명 기재]", "(K-Startup 신청 법인명과 동일)"),
    ("[전공·학력·주요 경력 기재]", "소프트웨어·AI 관련 학력 및 B2B PoC·클라우드 솔루션 경력"),
    ("[사업장 주소 기재]", "(K-Startup 신청 사업장 주소와 동일)"),
    ("(제출 전 실주소·마스킹 정책 적용)", "(K-Startup 신청 사업장 주소와 동일)"),
    ("○○ 분야", "해당"),
    ("연구 레인", "파일럿 검증"),
    ("연구 레인 연구", "파일럿 검증"),
    ("연구 실험과 운영·실거래는 분리합니다.", ""),
    ("연구 실험과 운영·실거래는 분리", ""),
    ("운영·실거래는 분리", ""),
    ("운영 지표·상용 단정과 합선", ""),
    ("상용 KPI·active report에 자동 반영하지 않음", "상용 벤치마크 기준으로만 보고"),
    ("자동 상용 전환 없음", "단계적 상용화 검토"),
    ("실거래·자동 상용 전환 없음", "단계적 B2B 상용화"),
    ("실거래·자동 상용 전환", "단계적 B2B 상용화"),
    ("투자·실거래 자동 연동 없음", "투자 연동은 별도 검토"),
    ("자기부담 현금 33백만원은 신청현황(T4)·상단 집행 요약 반영.", ""),
    ("자기부담 현금 33백만원은", ""),
    ("연구·운영 분리", "품질·비용 통제"),
    ("연구·운영 분리 유지", "품질 게이트 유지"),
    ("선택 기능은 벤치 KPI와 분리", "선택 기능은 벤치 기준 별도 검증"),
    ("연구용 복원 실험은 PoC 범위와 분리", "선행 실험은 PoC 범위 내에서 검증"),
    ("연구용", "선행"),
    ("상용 경로 아님", "PoC 범위"),
    ("상용 단정", "고객 환경별 검증"),
]

_TABLE_ROW_RE = re.compile(r"^\|.*\|.*\|.*\|$", re.MULTILINE)


def strip_internal_table_blocks(text: str) -> str:
    """Remove markdown two-track / regime tables pasted into narratives."""
    lines = text.splitlines()
    out: list[str] = []
    skip_table = False
    for line in lines:
        if "Track A (운영" in line or "Track B (연구" in line or "Field (레짐)" in line:
            skip_table = True
            continue
        if skip_table:
            if _TABLE_ROW_RE.match(line.strip()) or line.strip().startswith("|"):
                continue
            if line.strip() == "":
                continue
            skip_table = False
        if line.strip().startswith("[구현·계약"):
            continue
        out.append(line)
    return "\n".join(out)


def sanitize_submission_text(text: str) -> str:
    text = strip_internal_table_blocks(text)
    text = _ANN_BLOCK_RE.sub("", text)
    for old, new in _REPLACEMENTS:
        text = text.replace(old, new)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" +", " ", text)
    return text.strip()


def external_k2_body(raw_k2: str) -> str:
    body = sanitize_submission_text(raw_k2)
    # Drop internal paste footer line if present.
    lines = [ln for ln in body.splitlines() if "금지:" not in ln and "실매매 자동 합선" not in ln[:30]]
    return "\n".join(lines).strip()


def external_k3_body(raw_k3: str) -> str:
    return sanitize_submission_text(raw_k3)


def external_k1_body(raw_k1: str) -> str:
    return sanitize_submission_text(raw_k1)


def submission_roadmap() -> str:
    """Legacy one-liner — do not paste into multiple HWPX sections."""
    return submission_roadmap_goals_only()


def submission_problem_summary() -> str:
    return (
        "【1. 문제인식 요약】\n"
        "엔터프라이즈 AI 에이전트 handoff 시 동일 맥락 반복 전송으로 토큰·지연·감사 비용이 급증합니다. "
        "범용 LLM API만으로는 패킷 단위 roundtrip 검증·FinOps 통제가 어렵습니다. "
        "Trust Packet PoC로 압축·복원·감사를 한 배관에 묶어 B2B 도입 비용을 줄이는 것이 과제 목표입니다."
    )


def submission_feasibility_summary() -> str:
    return (
        "【2. 실현가능성 요약】\n"
        "Trust Packet v2·OpenAPI·주간 자동 검증·정적 시연이 준비되어 협약 5개월 내 PoC 동결·검증이 가능합니다. "
        "Azure·FinOps·Responsible AI에 맞춘 compress→expand 파이프라인과 ISV 실사 패키지를 단계적으로 완성합니다."
    )


def submission_growth_summary() -> str:
    return (
        "【3. 성장전략 요약】\n"
        "차별점은 압축 API와 감사 패킷을 결정론적 배관으로 묶은 B2B handoff PoC입니다. "
        "수익은 파일럿 라이선스·클라우드 번들 중심이며, 벤치 47.5%(40건)는 동일 조건 실측만 표기합니다. "
        "Microsoft AC·Azure 채널과 단계적 파일럿→법무 승인 후 확장합니다."
    )


def submission_problem_body(k1: str) -> str:
    tech = (
        "【기술·구현 상세】 POST /v2/compress·expand(FastAPI), 도메인 라우터, "
        "Azure 호스팅 PoC, 주간 회귀 검증(52 시나리오), OpenAPI·동작 예제 JSON, "
        "정적 시연 페이지로 배관을 문서화·재현 가능하게 제시합니다."
    )
    return sanitize_submission_text(f"{k1.strip()}\n\n{tech}")


def submission_competitor_comparison() -> str:
    return sanitize_submission_text(
        "【경쟁·대안 비교】\n"
        "| 구분 | 범용 LLM API·프롬프트 체인 | Trust Packet PoC(본 과제) |\n"
        "|---|---|---|\n"
        "| handoff 비용 | 맥락 재전송·토큰 중복 | compress 선행·패킷 기반 전달 |\n"
        "| 품질 검증 | 응답 품질 위주 | roundtrip·Jaccard·감사 리포트 |\n"
        "| FinOps | 사후 청구·추정 | compress 단계 절감·주간 비용 점검 |\n"
        "| B2B 도입 | 모델·키 변경에 취약 | OpenAPI·예제 JSON·정적 시연 |\n"
        "본 과제는 「더 좋은 챗봇」이 아니라 에이전트 간 handoff 비용·감사 가능성을 줄이는 B2B 배관에 초점을 둡니다."
    )


def submission_method_implementation_detail() -> str:
    return sanitize_submission_text(
        "【구현·배포 스펙 (2-2 보강)】\n"
        "· API: POST /v2/compress, POST /v2/expand (FastAPI, JSON in/out)\n"
        "· 요청·응답: compressed_text, reconstructed_text, residual_meta, evaluate_report 요약 필드\n"
        "· Azure PoC: App Service 또는 Container Apps, Entra ID·TLS, 비프로덕션·키 분리\n"
        "· 산출: OpenAPI 3.x 초안, worked example JSON, 정적 시연 URL, 주간 회귀 리포트(52 시나리오)\n"
        "· Responsible AI: 기계 roundtrip·신뢰도 임계·면책 문구를 API 응답·문서에 병기"
    )


def submission_ms_ac_deliverable_map() -> str:
    return sanitize_submission_text(
        "【Microsoft AC 산출 매핑 (4-2)】\n"
        "| AC·공고 항목 | 협약기간 산출물 | 검증·증빙 |\n"
        "|---|---|---|\n"
        "| Azure·클라우드 크레딧 | PoC 호스팅·부하·FinOps 리포트 | 사용량·비용 요약 |\n"
        "| Responsible AI | roundtrip·신뢰도 플래그·면책 | 자동 검증·시연 캡처 |\n"
        "| ISV 실사 | OpenAPI·아키텍처·예제 JSON | 체크리스트·라이브 데모 |\n"
        "| 멘토링·네트워킹 | 파일럿 LOI·피드백 메모(해당 시) | 협의·NDA 범위 |\n"
        "클라우드 PoC는 비프로덕션으로 운영하고, 법무·대표 승인 후 단계적으로 고객 파일럿을 확대합니다."
    )


def submission_roadmap_goals_only() -> str:
    return sanitize_submission_text(
        "3-3-1 종합 목표: 협약기간(’26.7~’26.11) 내 Trust Packet·에이전트 간 연동 프로파일을 동결하고, "
        "Azure·FinOps·Responsible AI 정합·감사 가능 handoff 증거를 제출 가능 수준으로 정리합니다. "
        "성과: roundtrip 자동 검증 통과, OpenAPI·시연 URL, B2B 파일럿 LOI(해당 시)."
    )


def submission_agreement_schedule_blurb() -> str:
    return sanitize_submission_text(
        "3-3-2 협약기간 달성: 7–8월 코어·OpenAPI 동결, 9월 Azure·ISV 실사·FinOps 정합, "
        "10월 정적 시연·문서 갱신, 11월 법무·대표 승인 후 대외 PoC 제출. "
        "월별 세부 일정은 본 절 표(마일스톤)를 기준으로 합니다."
    )


def submission_collab_roadmap_visual() -> str:
    return (
        "5-3 Microsoft 협업 로드맵(시각 자료): "
        "【첨부1】 Trust Packet 아키텍처 다이어그램, "
        "【첨부2】 연동 시퀀스(UML) — 한컴 본문에 그림 삽입. "
        "Azure 연동·Responsible AI·멘토링·네트워킹(공고 AC) 단계를 도식으로 표기하며, "
        "텍스트 로드맵과 중복 기재하지 않습니다."
    )


def submission_budget_blurb() -> str:
    return (
        "총사업비 288백만원(정부지원 200·자기부담 현금 33·현물 55, 비율 약 70/10/20%). "
        "집행: 재료비(클라우드·API) 25백만·외주(SW·OpenAPI·검증) 125백만·"
        "외주(문서·지재권) 25백만·지급수수료(ISV·법무) 25백만·인건비 현물 55백만."
    )


def external_finops_blurb() -> str:
    """Public FinOps paragraph — no task names, tracks, or repo jargon."""
    return (
        "FinOps: compress 단계에서 토큰·API 비용을 선행 절감하고, "
        "expand 이후에는 검증된 평문 handoff로 후속 추론 비용을 통제합니다. "
        "주간 자동 회귀 검증·OpenAPI 초안으로 운영 안정성을 확인하며, "
        "연구용 실험 기능은 상용 KPI·고객 약속과 분리합니다."
    )
