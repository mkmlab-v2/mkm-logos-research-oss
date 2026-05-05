# Daily execution insight — 1-page brief (template)

**역할:** 운영자(Operator)가 **같은 날짜·같은 앵커**에서 “실행 팩트”와 “가설/연구”를 **한 화면으로 분리**해 기록한다.  
**SSOT:** `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` (1페이지 브리핑 템플릿 행).  
**Non-goals:** 투자권유·가격 단정·LLM 자유 서술. 대외/Track C는 별도 법무·`TRACK_C` 가드.

---

## 0) 메타 (필수)

| 필드 | 값 |
|------|-----|
| `brief_date_utc` | YYYY-MM-DD (UTC 권장) |
| `workspace_anchor` | 예: BTC spot / KOSPI — 한 줄 |
| `mode` | 기본 `OBSERVATION_ONLY` — 본 템플릿은 관측·리허설용 |

---

## 1) 실행 팩트 (Fact — 디스크·스크립트 산출만)

다음은 **붙여넣기 소스** 예시 경로다. 실제 채울 때는 **그날 갱신된 JSON** 경로로 바꾼다.

### 1a) Dual regime (Logos 슬롯) — 브리프에는 **snippet 만**

| 필드 | 소스 JSON 경로 | 브리프에 넣을 필드 |
|------|----------------|---------------------|
| Dual regime 줄 | `multilens_eval_v2_thin` 리포트 행의 `lens_outputs.logos_dual_regime` | **`interpretation_snippet`** |
| 감사 전문 | 동일 객체의 `interpretation` | 브리프 본문 **금지** → 로그/티켓·내부 감사만 |

- 규칙·클립 SSOT: `docs/final/artifacts/LOGOS_DUAL_REGIME_INTERPRETATION_SNIPPET_RULES_V1.json`
- 구현: `scripts/core/logos_dual_regime_interpretation_snippet_v1.py`
- Thin 리포트 러너: `scripts/eval_multilens_harness_v2_thin.py` (`--populate-default-samples` 등)

**오늘의 `interpretation_snippet` (여기만 붙여넣기):**

```
(paste lens_outputs.logos_dual_regime.interpretation_snippet)
```

**수치 스냅샷 (한 줄):** `risk_multiplier_cap` = ___ · `market_shock_confirmed` = ___ · `veto_triggered` = ___

### 1b) 독립 렌즈 융합 스텁 (충돌 서술 — 결정론적 템플릿)

| 필드 | 소스 |
|------|------|
| 충돌 요약 | `docs/final/artifacts/independent_lens_fusion_stub_latest.json` → `conflict_summary.conflict_narrative_guarded` |
| 소수 렌즈 | 동일 → `conflict_summary.minority_lens_ids` |
| Logos verse 앵커 | 동일 → `conflict_summary.logos_evidence_verse_ids` |

**오늘의 한 줄 요약 (붙여넣기):**

```
(paste conflict_narrative_guarded — 운영 브리프용으로 이미 가드됨)
```

### 1c) 독립 렌즈 최신 JSON (정량·배너·veto — 붙여넣기 없음)

자동 생성 브리프(`scripts/build_daily_execution_insight_brief_v1.py`)가 아래 네 파일을 읽어 §1c 표로 넣는다. 수동 채우기 없이 **경로만 확인**하면 된다.

| 렌즈 | 소스 파일 |
|------|-----------|
| 명리 | `docs/final/artifacts/myeongni_independent_lens_latest.json` |
| 사상 | `docs/final/artifacts/sasang_independent_lens_latest.json` |
| 시장 사상 | `docs/final/artifacts/market_sasang_lens_latest.json` |
| 로고스(독립) | `docs/final/artifacts/logos_independent_lens_latest.json` |

**갱신 체인(권장):** `scripts/Run-DailyExecutionInsightBrief_v1.ps1` — 독립 렌즈 러너 → 융합 스텁 → (기본) `emit_myeongni_thin_bridge_line_v1.py --calendar-date auto` → Thin이 `data/multilens_eval/myeongni_independent_lens_thin_bridge_latest.jsonl`로 `--myeongni-jsonl` → `myeongri_core_v2_upgrade.py`(§1e) → 브리프. 격자 겹침만 쓰려면 `-SkipMyeongniThinBridge`. v2 생략은 `-SkipMyeongriV2Upgrade`. (기본 `-SkipIndependentLensRefresh` 없이 실행.)

### 1d) Fact-Lock 거버넌스 스냅샷 (필드 경로 고정)

아래 항목은 `scripts/build_daily_execution_insight_brief_v1.py`가 자동으로 읽어 브리프 표로 기록한다.

| 분류 | 필드 경로 | 소스 파일 |
|------|-----------|-----------|
| 운영 게이트 | `result.overall_go_no_go` | `docs/final/artifacts/a_track_go_nogo_status_latest.json` |
| 운영 단계 | `result.recommended_stage` | `docs/final/artifacts/a_track_go_nogo_status_latest.json` |
| 장애 사유 | `result.failed_reasons` | `docs/final/artifacts/a_track_go_nogo_status_latest.json` |
| 신뢰도 판정 | `snapshot.high_reliability_decision` | `docs/final/artifacts/a_track_go_nogo_status_latest.json` |
| 출력 잠금 | `snapshot.price_output_locked` | `docs/final/artifacts/a_track_go_nogo_status_latest.json` |
| 잠금 체크 | `checks.price_output_unlocked` | `docs/final/artifacts/a_track_go_nogo_status_latest.json` |
| 월간 신뢰도 | `meta.high_reliability_decision` | `docs/final/artifacts/prophecy_2026_monthly_kospi_btc_fact_safe_v1.json` |
| 월간 잠금 | `meta.price_output_locked` | `docs/final/artifacts/prophecy_2026_monthly_kospi_btc_fact_safe_v1.json` |
| 백테스트 최적 | `best_strategy.strategy_id` | `docs/final/artifacts/prophecy_lens_combo_backtest_v1_latest.json` |
| 백테스트 기간 | `best_strategy.metrics.n_days` | `docs/final/artifacts/prophecy_lens_combo_backtest_v1_latest.json` |
| 백테스트 MDD | `best_strategy.metrics.mdd` | `docs/final/artifacts/prophecy_lens_combo_backtest_v1_latest.json` |
| 백테스트 Sharpe | `best_strategy.metrics.sharpe` | `docs/final/artifacts/prophecy_lens_combo_backtest_v1_latest.json` |
| 16상태 감사 | `coverage_summary.states_with_audit` | `data/myeongni/16_STATE_MASTER_PROBE_v1.json` |
| commander 신뢰도 | `scores.confidence` | `reports/commander_myeongni_lens_latest.json` |
| conservative 원칙 | `hard_guardrails.most_conservative_wins` | `docs/final/artifacts/sasang_veto_only_active_config_latest.json` |

**표현 규칙(고정):**
- `GO/HOLD`는 운영 게이트(`overall_go_no_go`) 결과로만 표기.
- `PASS/FAIL`는 개별 체크(`high_reliability_decision` 등) 결과로만 표기.
- "Unverified Items..." 류 운영 문장은 JSON 필드가 아닌 경우 `[HYPOTHESIS]` 또는 `[GOVERNANCE_POLICY]` 태그로 분리.

### 1e) Myeongri core v2 (지장간 가중 / 연구용 신살 오버레이 / 사이즈 권고)

자동 생성 브리프가 아래 파일을 읽어 §1e 표로 넣는다. `shinsal_impact_overlay`는 `[RESEARCH_ONLY]`; `direction_override_allowed`는 항상 거짓.

| 분류 | 필드 경로 | 소스 파일 |
|------|-----------|-----------|
| 스키마 | `schema` = `myeongri_core_v2_upgrade_v1` | `reports/myeongri_core_v2_upgrade_latest.json` |
| 사이즈 권고 | `output.size_multiplier_recommended` | 동일 |
| 방향 오버라이드 | `output.direction_override_allowed` | 동일 |
| 오행 벡터 | `jijangan_weighted_vector.elements.*` | 동일 |
| 연구 신살 | `shinsal_impact_overlay.detected` | 동일 |
| 구조 긴장도 | `neutral_structure_metrics_v1.structural_tension_v1` | 동일 (지지 충·합·천간 합 빈도 기반 B-track 중립 지표) |
| SLKM 투영 | `neutral_structure_metrics_v1.latent_energy_vector_4d` | 동일 (오행→4슬롯; MKM 상용 4D Seed와 동명이인 아님) |
| 신살 로그 | `shinsal_detection_logs.entries` | 동일 |
| 면책 | `b_track_notice` | 동일 (브리프 §1e 인용) |

**갱신:** `scripts/myeongri_core_v2_upgrade.py` (기본 입력 `reports/commander_myeongni_lens_latest.json`). 일일 체인: `Run-DailyExecutionInsightBrief_v1.ps1`가 Thin 이후 기본 실행 (`-SkipMyeongriV2Upgrade`로 생략 가능).

---

## 2) 통찰 / 가설 ([HYPO] — 본선 트리거 아님)

| 항목 | 메모 |
|------|------|
| 가설 한 줄 | |
| 다음 확인 스크립트 또는 아티팩트 | |

---

## 3) 최종 액션 (운영 게이트 언어)

**NOT:** 매매 지시. **YES:** `HOLD` / `WATCH` / `REDUCE` / `정책 프로파일 유지` 등 **문서화된 게이트 출력**만.

| 필드 | 값 |
|------|-----|
| `final_action_label` | |
| `evidence_paths` | 로그·JSON 경로 나열 |

---

## 4) 교차 참조 (자동화 체크 시)

- 멀티렌즈 Thin 계약: `docs/final/artifacts/MULTILENS_EVAL_HARNESS_V2_THIN_CONTRACT.json`
- 융합 스텁 계약: `docs/final/artifacts/INDEPENDENT_LENS_FUSION_STUB_V0_CONTRACT.json`
- Fusion 출력 스키마: `docs/final/schemas/independent_lens_fusion_stub_v0.schema.json`
