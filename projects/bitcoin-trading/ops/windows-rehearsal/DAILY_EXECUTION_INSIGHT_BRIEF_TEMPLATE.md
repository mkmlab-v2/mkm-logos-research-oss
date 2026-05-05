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

**갱신 체인(권장):** `scripts/Run-DailyExecutionInsightBrief_v1.ps1` — 독립 렌즈 러너 → 융합 스텁 → (기본) `emit_myeongni_thin_bridge_line_v1.py --calendar-date auto` → Thin이 `data/multilens_eval/myeongni_independent_lens_thin_bridge_latest.jsonl`로 `--myeongni-jsonl` → 브리프. 격자 겹침만 쓰려면 `-SkipMyeongniThinBridge`. (기본 `-SkipIndependentLensRefresh` 없이 실행.)

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
