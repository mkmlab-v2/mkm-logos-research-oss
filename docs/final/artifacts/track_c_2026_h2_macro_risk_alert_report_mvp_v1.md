# Track C 2026 H2 Macro Risk Alert Report (MVP v1)

- generated_at_utc: `2026-05-05T13:50:00Z`
- status: `MVP_SKELETON_LOCKED`
- aligned_with: `docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md` §3.8 · §7 · §9 · §9A · §12
- audience: `B2B decision-makers (C-level / risk / strategy / operations)`

## 1) Executive Summary (1 page)

- This report provides governance-driven macro risk warning and scenario posture support.
- It is designed to shorten decision lead time and improve consistency under uncertainty.
- It is not investment advice, does not provide buy/sell instructions, and does not guarantee returns.

## 2) Scope and Non-Scope

<!-- track_c_mvp_section_2_auto_v1 -->
_본 절은 `build_track_c_macro_risk_mvp_filled_v1.py`가 디스크 아티팩트에서 생성했습니다. 생성 시각(UTC): `2026-05-16T07:05:35Z`._

**Core theory protection:** 본 요약은 의사결정 보조 산출물만 포함하며, 핵심 산식·가중치·중간 계산 기여도는 비공개 운영 원칙(`TRACK_C` §9A)을 따른다.

**보고 기간:** 2026-07-01 ~ 2026-12-31 — Track C §3.8 MVP 범위(시나리오·경보 브리프). 특정 시점 스냅샷 수치는 인용한 JSON 기준.

**한 줄 포즈(스모크 스냅샷):** 구조화 경보 `decision_state=WATCH`, `risk_warning_level=elevated`, `confidence_band=medium`, 운영자 포즈 `watch_tighten` — 매매 지시·자동 실행 아님 (`macro_risk_warning_api_smoke_latest.json`, `timestamp_utc=2026-05-14T22:28:04.089149Z`).
- 레짐 맥락(스모크): `primary_regime_id=post_covid_normalization`

| 스모크 insight_7 축 (상위) | 값 |
|---|---|
| `market_liquidity_stress` | 0.5802 |
| `volatility_regime_shift` | 0.5502 |
| `tail_event_pressure` | 0.5402 |
| `crowd_positioning_fragility` | 0.5202 |
| `funding_pressure_signal` | 0.4702 |

| 블록 | 내용 |
|------|------|
| 상위 리스크 테마 (≤5) | 유동성 스트레스·교차자산 괴리·변동성 레짐·테일 압력 등 — 위 스모크 `insight_7` 수치 인용 |
| 현재 경보 수준(스모크) | `decision_state=WATCH`, `risk_warning_level=elevated` — 운영 라벨은 정책 바인딩 JSON과 정합 확인 |
| 근거 링크 | `docs/final/artifacts/macro_risk_warning_api_smoke_latest.json`, `reports/macro_risk_n8n_daily_check_latest.json`, `docs/final/artifacts/pre_news_shadow_task_health_latest.json`, `docs/final/artifacts/pre_news_shadow_weekly_report_latest.json` |
| 불확실성 | n8n 일일 점검 `overall=pass`; `n8n_health=pass`; 스냅샷 시각 `2026-05-15T09:50:37.2220279Z`; Pre-News 작업 건강도 `healthy=True`, `result_category=OK` (`generated_at_utc=2026-05-14T21:50:03Z`); 주간 리포트 창 `7d`, 창 내 실행 `3`회 (`generated_at_utc=2026-05-14T21:30:05Z`); 과거 스냅샷은 현재 시장과 다를 수 있음; 법무 검토 전 대외 확정 금지. |
| 다음 갱신 | 일일 체인·스케줄 실행 시 (운영 캘린더와 정합); Pre-News 작업 `next_run_time=2026-05-15T21:30:00Z` 참고 |

**금지:** 특정 자산 매수·매도 지시, 목표가, 성과에 대한 약속.
<!-- /track_c_mvp_section_2_auto_v1 -->

## 2b) Logos Deep Narrative Module (premium, `[NON_GATING]`)

<!-- track_c_mvp_logos_module_auto_v1 -->
_본 절은 `build_track_c_macro_risk_mvp_filled_v1.py`가 Logos 아티팩트에서 생성했습니다. UTC `2026-05-16T07:05:35Z`._

**포지션:** §3.8 매크로 경보 구독의 **프리미엄 모듈** — 고전/철학 코퍼스(Logos) **스트레스 테스트·심층 리스크 내러티브**. 예언·종교·매매 지시 아님. 성경/Logos 렌즈는 **`[NON_GATING]`** — 최종 포즈는 Field(실물 레짐)+운영 게이트.

| 항목 | 값 |
|------|-----|
| Logos insight bundle | `generated_at_utc=2026-05-15T23:35:08Z`, `research_only=True`, `non_gating=True`, `degraded=False` |
| Query fingerprint | `sha256:0bc67d9556b3f0a7740fcf915af345854e48f6167…` |
| Commander deep report | `snapshot_utc=2026-05-16T06:41:32Z`, `schema=logos_track_b_commander_deep_report_v1` |

**대외 1-pager:** `docs/final/artifacts/track_c_logos_deep_risk_narrative_offer_onepager_v1_latest.md` (재생성: `py scripts/build_track_c_logos_b2b_offer_onepager_v1.py`). **합본:** `track_c_combined_b2b_offer_onepager_v1_latest.md`.

**금지:** “성경이 시장을 예측”, 실시간 신탁, Logos 단독 시그널 상품 포장.
<!-- /track_c_mvp_logos_module_auto_v1 -->

## 3) Operational Governance Frame

- Authority model: `human-on-the-loop` with operator final authority
- Policy model: `policy-as-code` + bounded execution context
- Audit model: append-only trace + reconstruction-oriented evidence paths
- Exception model: queue-based handling with explicit escalation ownership

## 4) KPI Snapshot (Contract-Ready)

- Lead-time KPI: warning-to-decision lead-time delta
- Delivery KPI: on-time report delivery rate
- Reliability KPI: alert timeliness and missed-alert rate (within contract scope)
- Governance KPI:
  - exception handling lead time
  - audit log reconstruction success rate

## 5) Evidence Map (Fact-Lock)

- Core business plan and guardrails: `docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md`
- API contract pointer: `docs/final/openapi_macro_risk_warning_api_v1.yaml`
- B2B onepager (aligned): `docs/final/artifacts/track_c_b2b_macro_alert_offer_onepager_latest.md`
- NotebookLM source policy: `docs/NotebookLM_sources_manifest.md`

## 6) Delivery Format (MVP)

- PDF brief (weekly/monthly cadence, contract-defined)
- Email alert digest (structured, non-instructional)
- Optional dashboard access (read-only risk posture view)

## 7) Legal and Messaging Lock

- Not investment advice
- No buy/sell instructions
- No guarantee of returns
- Final decisions remain with client operators

## 8) 14-Day Execution Plan

1. Lock scope/non-scope language across offer sheet, report, and API intro text
2. Freeze KPI field definitions and reporting cadence
3. Validate evidence links and regenerate stale pointers
4. Run one internal audit reconstruction drill and attach result summary

## 9) Client-Facing Fixed Paragraph

MKM provides a governance-driven risk warning and scenario posture service that integrates multi-lens analytics. The service supports exposure-control decisions with reproducible artifacts and verification logs. It is not investment advice, does not provide buy/sell instructions, and does not guarantee returns.

