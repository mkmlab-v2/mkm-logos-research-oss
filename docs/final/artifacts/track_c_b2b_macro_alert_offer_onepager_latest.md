# Track C — 기업용 매크로 조기 경보 구독 (세일즈 시트 초안)

- **generated_at_utc:** `2026-05-16T07:05:35Z`
- **aligned_with:** `docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md` §3.8 · §9 · §9A · §10 항목 2
- **status:** `DRAFT_AUTO`

## 포함 (구독 범위 예시)

- 분기·월간 **거시·레짐 시나리오 브리프** (PDF / 공유 링크)
- **이메일·(옵션) 대시보드** 알림 — 구조화 경보·운영자 포즈 표기 (매매 지시 아님)
- **읽기 전용 경보 API** 는 별도 계약 — 계약 SSOT `docs/final/openapi_macro_risk_warning_api_v1.yaml`

## 제외 (명시)

- 투자 자문, 특정 자산에 대한 매매 지시·목표가, 성과에 대한 약속
- 고객 거래소 API·실키를 당사가 저장·중계하지 않음 (`TRACK_C` §3.8 운영 경계)
- 핵심이론 산식·가중치·중간 피처 기여도·튜닝 규칙 비공개 (`TRACK_C` §9A)

## 신뢰·거버넌스 KPI (요약)

- 재현 가능한 **JSON·로그 경로**를 납기물에 병기 (Fact-Lock)
- 월간 **투명성** 리포트(계약 범위 내): 경보 적시성·정시 납기 등 `TRACK_C` §7과 정합 가능 영역만
- 감사 추적: 고객·시점별 조회 기록(append-only) 및 유출 추적 워터마킹 적용

## 대외 비교 포지셔닝 (Fact-Lock)

- WRING류는 기초모델 내부 표현공간 편향 교정(기초 과학), MKM12 Track C는 운영 파이프라인·정책 바인딩·감사 추적(응용 거버넌스) 전장
- 기술 우열 단정 금지; 상용 문구는 "운영 통제 가능성·감사 가능성" 중심으로 고정
- 모델 내부 개조 없이 API 계약·HITL·로그 증거로 리스크 경보 운영을 검증 가능하게 제공

## Core Theory Protection (Commercial Security Gate, §9A)

- **Model-as-a-Service:** 핵심 엔진은 서버 내부에서만 실행, 대시보드/API는 결과값만 제공
- **응답 최소화:** 점수·사분면·상태 라벨은 제공하되 산식 상세·가중치·중간 계산값은 미제공
- **계약 통제:** NDA, 역공학 금지, 재배포 금지, 파생모델 학습 금지 조항 기본 적용
- **접근 통제:** tenant별 API 키, 권한 분리(RBAC), 엔터프라이즈 옵션(IP allowlist)

## 대외 고정 문구 (§9 English default)

> MKM provides a governance-driven risk warning and scenario posture service that integrates multi-lens analytics. The service supports exposure-control decisions with reproducible artifacts and verification logs. It is not investment advice, does not provide buy/sell instructions, and does not guarantee returns.

## Short copy (§9)

- Risk Warning First, Not Trade Advice.
- Token Efficiency + Risk Posture, with Reproducible Evidence.
- Governance-driven, Artifact-backed, Operator-in-the-loop.

## 가격·계약

- 별도 견적·영업 확정 (본 초안은 의향 표시용)
- 기본 라이선스: `decision-support output license` (core formula license 아님)

## 근거 MVP 뼈대

- `docs/final/artifacts/track_c_2026_h2_macro_risk_alert_report_mvp_v1.md`
