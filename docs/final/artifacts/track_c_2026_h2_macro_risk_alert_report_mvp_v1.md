# 2026 H2 매크로 리스크 경보 리포트 — MVP 뼈대 (Track C)

- **schema:** `track_c_2026_h2_macro_risk_alert_report_mvp_v1`
- **status:** `DRAFT_STUB` — 목차·Executive Summary 틀·근거 경로만 동결; 수치·본문은 아티팩트 갱신 후 채움.
- **generated_for:** `docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md` §3.8 MVP
- **disclaimer (fixed):** 본 문서는 투자 자문·매매 지시가 아니며, 결과에 대한 약속을 하지 않습니다. 최종 의사결정은 고객 운영자에게 있습니다 (`TRACK_C` §9·`Not investment advice`).

---

## 1. 목차 (납품본 편집 순서)

1. **Executive Summary** (1p, 아래 §2 템플릿)
2. **범위·한계·면책** — 비자문·비실행·아티팩트 기반 재현
3. **거시·유동성 시나리오 (H2 2026)** — 시나리오 포즈만; 단정적 가격 예측 금지
4. **레짐·스트레스 지표** — 실물 1차 레짐 맵·듀얼 레짐 평가 경로와의 정합
5. **이벤트·뉴스 전방 채널** — Pre-News 스냅샷·(선택) 브리지 산출
6. **Macro Risk Warning API 계약·스모크** — Track C HTTP 계약과 동일 선상의 근거 링크
7. **운영·게이트 헬스** — 매크로 리스크 n8n 일일 점검·실패 로그
8. **멀티렌즈 해설 (보조)** — 사상·명리·로고스는 `[NON_GATING]` 해설; 주문 트리거 아님
9. **납품물·갱신 주기** — PDF/대시보드/이메일 SLA 초안
10. **부록 A — 근거 아티팩트·스크립트 목록** (§3)
11. **부록 B — 용어·브랜드 가드** (`§9` External Messaging 정렬)

---

## 2. Executive Summary (1p 템플릿)

**[FILL] 보고 기간:** 2026-07-01 ~ 2026-12-31 (예시)

**[FILL] 한 줄 포즈:** 거시·레짐·이벤트 채널을 종합한 **시나리오 자세(scenario posture)** 요약 (매매 권유 없음).

| 블록 | 채움 규칙 |
|------|-----------|
| 상위 리스크 테마 (≤5) | 레짐·유동성·지정학·이벤트 중 관측된 축만; 숫자는 아티팩트 인용 |
| 현재 **경보 수준** | `WATCH` / `ELEVATED` / `CALM` 등 사내 라벨 — API 스모크·정책 바인딩 JSON과 용어 정합 |
| 근거 링크 | §3 표의 `latest` JSON·OpenAPI 경로를 보고서 각주로 병기 |
| 불확실성 | 반드시 1문단: 데이터 공백·모델 한계·샘플 구간 |
| 다음 갱신일 | 구독 주기에 맞게 고정 |

**금지:** 특정 자산 매수·매도 지시, 목표가, 확정 수익·성과에 대한 약속.

---

## 3. 근거 아티팩트·스크립트 (Fact-Lock 포인터)

아래는 **레포 SSOT·산출 경로**이다. 본 리포트 본문 수치는 해당 파일이 존재·갱신된 경우에만 인용한다 (`CONSTITUTION`·`P0`와 정합).

| 구분 | 경로 |
|------|------|
| Track C 사업 SSOT | `docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md` |
| Macro Risk Warning OpenAPI | `docs/final/openapi_macro_risk_warning_api_v1.yaml` |
| API 스텁(로컬 스모크) | `scripts/macro_risk_warning_api_stub.py` |
| API 응답 계약·스모크 산출 | `docs/final/artifacts/macro_risk_warning_api_response_contract_v1.json`, `macro_risk_warning_api_smoke_latest.json` |
| 정책 바인딩·액션 매트릭스 | `docs/final/artifacts/macro_risk_warning_policy_binding_latest.json`, `macro_risk_warning_api_decision_action_matrix_v1.json` |
| 실패 드릴 | `docs/final/artifacts/macro_risk_warning_failure_drill_latest.json` |
| n8n 매크로 리스크 일일 점검 | `scripts/Run-MacroRiskN8nDailyCheck.ps1` → `reports/macro_risk_n8n_daily_check_latest.json` |
| 일일 점검 실패 로그 | `reports/macro_risk_n8n_daily_check_failures.jsonl` |
| Pre-News Shadow 체인 | `scripts/run_global_atom_pre_news_shadow_chain_v1.ps1` |
| Pre-News Shadow 투영·입력 | `docs/final/artifacts/pre_news_shadow_projection_latest.json`, `docs/final/artifacts/pre_news_shadow_input_latest.json` |
| Pre-News Shadow 헬스 | `scripts/run_pre_news_shadow_health_chain.ps1` → `docs/final/artifacts/pre_news_shadow_task_health_latest.json` |
| Pre-News Shadow 주간 리포트 | `docs/final/artifacts/pre_news_shadow_weekly_report_latest.json` |
| 레짐 맵·정책 | `data/regimes/regime_map.json`, `data/regimes/regime_fusion_policy.json` |
| Dual-regime 평가 모듈 | `projects/bitcoin-trading/src/integration/dual_regime_api.py` |
| 일일 체인(참고) | `scripts/run_daily_prophecy_then_pre_news_v1.ps1` |

**주의:** 멀티렌즈·명리·사상 산출물은 **해설·연구 레일**로만 인용하고, 실거래·자동 주문과 합선하지 않는다 (`CENTRAL_AGENT_MEMORY_V1`·렌즈 계약).

---

## 4. 다음 채움 순서 (운영)

1. 위 §3 경로에서 **최신 JSON** 존재 확인 (`mtime`/파이프라인 exit 0).
2. §2 Executive Summary 표를 수치·문장으로 채움 (인용 각주에 §3 경로).
3. `py scripts/check_track_c_copy_guard_v1.py` 로 본 파일 및 대외 PDF 초안 복사본 검사.
4. 법무 검토 후 대외 버전 `APPROVED` 표기.
