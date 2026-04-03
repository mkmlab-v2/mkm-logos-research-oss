# 작전지휘부 동기화 — Logos KOSPI Shadow (L2) 상황 브리지

**schema**: `notebooklm_ops_command_brief_v1`  
**mode**: `OBSERVATION_ONLY` (Fact-Lock: 본 문서는 연구·관측 추적용, 실매매·프로모션 트리거 아님)  
**generated_at_utc**: `2026-04-03T12:30:00Z`

## 한 줄 요약

Logos·KOSPI **섀도우** 파이프라인은 v21에서 **경고 정밀도(warning_precision)를 precrash-zone 정의로 분리**했고, v22·v23에서 **시간적 분할·홀드아웃·번들 평가**를 재현 가능하게 고정했습니다. **수치·게이트 통과 여부는 항상 `logos_kospi_shadow_evaluation_bundle_v23_latest.json`(SSOT)을 따른다.** 스크립트 기본(`DEFAULT_SHADOW_EXTRA`) 기준으로는 **combined는 통과할 수 있으나 temporal 집약은 여전히 미통과**인 경우가 있다(`--bare`는 대체로 전 구간 미통과).

## SSOT 경로 (레포)

| 산출물 | 경로 |
|--------|------|
| 인사이트 브리프 (전체 역사 v1–v23) | `docs/final/artifacts/LOGOS_SHADOW_202003_INSIGHT_BRIEF_V1.md` |
| 평가 번들 v23 (SSOT) | `reports/research/logos_shadow_v1/logos_kospi_shadow_evaluation_bundle_v23_latest.json` |
| 번들 v23 NotebookLM용 MD 래퍼 | `docs/final/artifacts/logos_kospi_shadow_evaluation_bundle_v23_notebooklm.md` (내용 동일, fenced JSON) |
| 공유 평가 라이브러리 | `scripts/logos_shadow_eval_lib.py` |
| 시간적 코스트 게이트 v22 | `scripts/report_logos_shadow_cost_gate_temporal_v22.py` → `logos_kospi_shadow_cost_gate_temporal_v22_latest.json` |
| 회귀 테스트 (v21 메트릭) | `tests/test_logos_kospi_shadow_metrics_v21.py` |

## 스냅샷 수치 (v23 번들, `min_cost_efficiency_score=0.35`)

**정밀도 정의**: `precrash_zone_precision` (v21 이후; 방향 적중률과 혼동 금지).  
**주의**: 아래는 **재현 가능한 스냅샷**이며, 최신 판정·소수점은 **`reports/research/logos_shadow_v1/logos_kospi_shadow_evaluation_bundle_v23_latest.json`** 및 동일 조건으로 재실행한 결과가 SSOT다.

### A) `--bare` (추가 인자 없음; `report_logos_shadow_evaluation_bundle_v23.py --bare` → `…_v23_bare_baseline.json`과 동일 재현)

- **Temporal (t1–t3)**: `cost_efficiency_score` ≈ `0.068596`, `pass_cost_gate`: **false**
- **Holdout (h1–h4)**: `cost_efficiency_score` ≈ `0.095507`, `pass_cost_gate`: **false**
- **Combined (7 windows)**: `cost_efficiency_score` ≈ `0.084797`, `pass_cost_gate`: **false**

### B) 스크립트 기본 `DEFAULT_SHADOW_EXTRA` (`extra_args` 비우면 자동 적용; `…_v23_latest.json` SSOT, 2026-04-03 재생성 기준)

- **Temporal (t1–t3)**: `cost_efficiency_score` ≈ **`0.127156`**, `pass_cost_gate`: **false**
- **Holdout (h1–h4)**: `cost_efficiency_score` ≈ **`0.590553`**, `pass_cost_gate`: **true**
- **Combined (7 windows)**: `cost_efficiency_score` ≈ **`0.393851`**, `pass_cost_gate`: **true**

*NotebookLM·질의 전에 반드시 확인: B가 현재 “latest” 기본 스택이며, A는 레거시/베이스라인 비교용이다. 혼동 시 “전 구간 미통과”라는 잘못된 전제로 답이 나올 수 있다.*

## 거버넌스

- `OBSERVATION_ONLY` 유지. 게이트 미통과는 **모델·라벨·임계·비용식 재검토** 전까지 프로모션 근거로 사용하지 않음.
- Vault 미러: `scripts/sync_notebooklm_sources_to_mkm_data_vault.ps1`에 본 브리지·브리프·번들 JSON 경로 포함 시 `G:\...\vault\notebooklm_sources\`에 반영.

---

## NotebookLM 질의 세트 (의견·리스크·다음 스텝)

아래는 **작전지휘부 노트북**에 소스가 반영된 뒤, 채팅 또는 `notebook_query`에 그대로 넣어 **우선순위와 리스크**를 묻는 용도다.

*전제(SSOT `v23_latest`·`DEFAULT_SHADOW_EXTRA`): `temporal_pass`는 미통과인 경우가 많고, `holdout_pass`·combined는 통과할 수 있다. 질문 2는 “둘 다 실패하는 스택(bare)”과 “시계열만 실패하는 스택(latest)”을 구분해 답할 것.*

1. **게이트 철학**: `min_cost_efficiency_score=0.35`와 계수(load 4.8, false 1.5)가 *희소 경고·고회상* 설정에서 과도하게 보수적인지, 아니면 **의도적으로 높은 바**가 맞는지, 근거를 한 단락으로 정리해 달라.
2. **최우선 개선 축**: `temporal_pass` 실패와 `holdout_pass` 실패를 **동시에** 가정할 때와, **latest처럼 temporal만 실패**할 때 **우선순위가 같은지** 비교해 달라. 동일 스텁 렌즈·라벨 정의 전제에서 (라벨·임계·캘리브레이션·피처) 무엇을 먼저 손댈지.
3. **최근 구간(t3, 2023–2024)**: `recent_era_precrash_zone_precision`이 구간에 따라 변동할 때, **“최근 레짐 전용 서브게이트”**를 두는 것이 연구상 타당한지, 아니면 **단일 게이트 유지**가 낫는지.
4. **방향 vs precrash**: `hit_direction_rate`와 `precrash_zone_precision`이 벌어지는 구조에서, **연구 리포트**에 어떤 지표를 “대시보드 1순위”로 둘지 권고.
5. **비용·거짓 경보**: `false_alert_density`가 높은 창구에서의 운영 부담을 줄이기 위한 **비모델적** 완화(밀도 캡, 쿨다운, 인간 확인) 중, **섀도우 단계에서 허용 가능한 것**을 나열해 달라 (본선 바인딩 없음 전제).

---

**끝.** (동기화 시각·번들 해시는 로컬 Git/파일 타임스탬프로 검증.)
