# AIDC 제출용 Verifiable Benchmark 1페이지 (심사용)

## 1) 목적 (What we prove)

본 제안은 AI 인프라 의사결정 시스템의 성능을 "주장"이 아닌 "재현 가능한 수치"로 검증하는 것을 목표로 한다.  
본 문서는 AIDC 심사 대응을 위해 1차 축을 "전력 효율(Performance per Watt)"로 고정하고, 2차 축으로 냉각 최적화, 3차 축으로 입지 MCDA를 단계적으로 검증한다.  
검증 범위는 세 가지다.

- 예측 정합성: 신호 방향(예: Long/Short/Hold)과 실제 미래 구간 방향의 일치도
- 위험 방어력: 고위험 구간에서 손실 확대를 얼마나 억제했는지
- 운영 안정성: 비정상 입력 또는 LLM 생성 노이즈 상황에서도 안전 게이트가 의사결정 오류를 줄였는지
- 인프라 효율성: 동일 정확도 조건에서 처리량/전력(throughput per watt) 개선 여부

## 2) 제출용 주장 문구 (심사형)

본 기술은 단순 예측 모델이 아니라, 데이터 기반 위험 게이팅을 포함한 다기준 의사결정(MCDA) 엔진이다.  
동일 데이터셋에서 베이스라인 대비 손실 지표와 의사결정 오류 지표를 비교 검증했으며, 결과는 재현 가능한 스크립트와 산출물로 제출한다.

> 금지 문구: "Zero-Hallucination", "항상 우수", "XX% 개선 확정"  
> 허용 문구: "본 실험 조건에서", "신뢰구간 95% 기준", "통계적으로 유의/비유의"

## 3) 실험 설계 (Protocol)

### 데이터

- 공개 시계열 데이터 2종 이상 (예: BTC OHLCV, KOSPI 지수)
- 기간 고정 (예: 최근 24개월), 타임존 고정, 결측 처리 규칙 문서화
- 공통 스키마: `timestamp, close, signal, regime_id, feature_set_version`

### 비교군

- A군 (Baseline): 일반 신호 생성/필터
- B군 (Treatment): Baseline + 위험 게이트(MCDA/Regime Filter)
- 거래비용/슬리피지 동일 적용

### 검증 방식

- Walk-forward split (학습/검증 분리)
- 랜덤 시드 고정
- 민감도 분석(핵심 파라미터 상/중/하)

## 4) 핵심 KPI (필수)

- 방향 정합성: Hit Rate, Precision, Recall, F1
- 리스크: MDD, CVaR(선택), 변동성, 손실구간 지속시간
- 효율: Turnover, 체결 가정 하 순성과(비용 반영)
- 안정성: 안전 게이트 발동률, 게이트 미발동 시 대비 오류율 변화
- AIDC 전력 효율: GPU 처리량(tokens/s or samples/s), 평균 전력(W), `Performance/W`, 동일 정확도 유지율
- 냉각 연동(2단계): IT Load 대비 Cooling Power 비율, PUE 변화량(실험 구간 기준)
- 운영 신뢰성: SLA 위반률(지연/오류), Fail-safe 전환 성공률

## 4.1) 1차 벤치마크 합격선 (Go/No-Go)

- `Performance/W`: Baseline 대비 상대 개선율을 수치로 제시(신뢰구간 포함)
- 동일 정확도 유지: 기준 정확도 대비 허용 오차 범위 내 유지
- SLA 유지: 지연/오류 임계치 이하를 만족할 것
- 위 3개 중 하나라도 미달이면 "개선 미입증"으로 보고하고 원인 구간을 함께 제출

## 5) 통계 검정 및 보고 규칙

- 각 KPI에 대해 95% 신뢰구간 보고
- A/B 차이는 paired test 또는 bootstrap diff로 검정
- 단일 최고값만 제시하지 않고 평균/중앙값/분산 동시 제시
- 실패 케이스(비유의 또는 성능 악화 구간) 반드시 포함

## 6) 제출 산출물 (Evidence Bundle)

필수 제출 파일:

- `benchmark_manifest.json` (데이터 소스, 기간, 파라미터, 커밋 해시)
- `ab_result_summary.json` (KPI 집계 + 신뢰구간 + p-value)
- `ab_result_timeseries.csv` (시간축별 누적 성과/리스크)
- `repro_command.txt` (단일 재현 명령)
- `environment.lock` 또는 `requirements.txt` (실행 환경 고정)
- `power_profile.csv` (timestamp, gpu_power_w, gpu_util, throughput)
- `aidc_kpi_gate.json` (Go/No-Go 판정, 임계치, 판정 근거)

## 7) 심사위원 대응용 한 문단

본 시스템은 "수익률 극대화" 단일 목적이 아니라, 위험 구간에서의 손실 억제와 의사결정 안정성을 함께 최적화하도록 설계되었다.  
동일한 공개 데이터와 고정된 실험 조건에서 A/B 비교를 수행하고, 신뢰구간과 검정 결과를 포함한 원시 산출물을 제출해 재현성을 보장한다.  
따라서 본 결과는 설명 가능한 운영 성능 지표로 활용 가능하며, 정책/사업 의사결정의 객관적 근거로 사용될 수 있다.

## 8) 즉시 실행 체크리스트 (내부)

- [ ] 데이터 소스 URL 및 라이선스 확정
- [x] 평가 기간/타임존/결측 규칙 1차 고정 (`build_btrack_prophecy_score_from_ohlcv.py` 기준)
- [x] A/B 실행 파라미터 1차 고정 (`neutral_bps=5.0`, `eval_date=auto`)
- [x] 결과물 자동 저장 경로 고정 (`docs/final/artifacts/*_latest.*`, `ab_result_timeseries.csv`)
- [x] 제3자 재현 테스트 1회 통과(동일 커맨드 재실행 기준)
- [x] `power_profile.csv` 1차 생성(전력/활용률 샘플 캡처, 처리량 baseline 대기)
- [x] `aidc_kpi_gate.json` 생성(현 시점 Gate 판정: `NO_GO`)
- [x] Perf/W 예비 실측 반영 (`throughput_samples_per_s`, `gpu_power_w`, `perf_per_w`)

## 11) 실행 현황 스냅샷 (2026-04-06)

- Accuracy(관측 레인): `hit_rate=0.383333`, `n=60`, `p=0.244358` (유의 아님)
- Power/Perf(페어 측정): baseline `perf_per_w=0.346608` vs treatment `perf_per_w=0.279123` (`uplift=-19.470122%`)
- Gate 결과: `NO_GO` (사유: 정확도 유의성 미달 + Perf/W 미개선)
- Integrity 테스트: `test_multilens_sensitive_integrity_gate` 통과
- 운영 헌법 게이트 주의: `automation_registry_reconcile`은 최근 태스크 실행 실패 누적으로 `all_ok=false` 가능

## 12) Fact-Lock 운영 결정 (충돌 회피)

- AIDC 성능 검증 SSOT: `docs/final/artifacts/aidc_perf_ab_summary.json`
- 보조 원시 로그: `docs/final/artifacts/power_profile.csv`
- 운영 자동화 체인과 충돌 가능한 `aidc_kpi_gate.json`은 참고용으로만 유지하고, 강제 덮어쓰기는 수행하지 않음
- 필요 시 후속 파이프라인은 충돌 회피용 별도 파일명(`aidc_kpi_gate_v2.json` 등)으로 분리

## 9) 즉시 실행 일정 (지금 기준 0~6시간)

- 0~1시간: 전력 로그 수집 경로 확정(`power_profile.csv` 스키마 고정)
- 1~2시간: Baseline/Treatment 동일 입력 조건 실행(전력+정확도 동시 기록)
- 2~4시간: `benchmark_manifest.json` / `repro_command.txt` / `aidc_kpi_gate.json` 갱신
- 4~5시간: `ab_result_summary.json` 통계 반영본(핵심 KPI + Wilson 95% CI + p-value)
- 5~6시간: 심사용 본문에 `Performance/W` 결과 반영 + 실패/한계 구간 명시

## 10) 표현 가이드 (심사/투자 겸용)

- 금지: "Risk Zero", "국가 공인 기술 보증", "항상 우수"
- 권장: "본 사업/실험 조건에서", "검증 프로그램 통과", "재현 가능한 로그 기준"
- 권장: "비용 절감 가능성"은 근거 수치(인프라 단가/실험 시간/전력 로그)와 함께 제시

## 12) Cursor CLI + AIDC 운영 분리 (실행 표준)

- 원칙: Cursor CLI는 범용 개발/리뷰 루프, AIDC는 제출형 벤치 실행기로 역할 분리한다.
- Cursor CLI 사용 범위: 코드 수정, 리팩터링, 보안/성능 리뷰, PR 전 점검.
- AIDC 사용 범위: 증빙 산출물 생성/판정(`benchmark_manifest`, `ab_result_summary`, `aidc_kpi_gate`)과 재현 명령 고정.
- 중복 금지: 동일 목적을 Cursor CLI와 AIDC에서 이중 실행하지 않는다(로그 기준 단일화).

권장 최소 실행 시나리오:

1) 개발/수정 단계: `agent` 또는 `agent -p "<작업지시>"`  
2) 벤치 생성 단계: `py scripts/build_btrack_prophecy_score_from_ohlcv.py` + 관련 A/B 실행 스크립트  
3) 판정/제출 단계: `py scripts/update_aidc_kpi_gate.py --label baseline --iterations 30 --measurement-mode subprocess --output-suffix _v2` + `py scripts/update_aidc_kpi_gate.py --label treatment --iterations 30 --measurement-mode subprocess --output-suffix _v2` 실행 후 `docs/final/artifacts/*` 증빙 묶음 갱신

운영 메모:

- AIDC 명칭 기준 SSOT: `scripts/update_aidc_kpi_gate.py`, `docs/final/artifacts/aidc_kpi_gate.json`
- "AIDA CLI"는 현재 저장소 기준 공식 명칭/엔트리 포인트가 확인되지 않아, 문서/자동화는 `AIDC` 기준으로 유지한다.

### 12.1) Cursor CLI 주장 팩트체크 반영 (운영용)

- 확인됨(높음): Headless/비대화형 실행(`agent -p ...`)은 재현 파이프라인의 Step 1 자동화에 직접 활용 가능.
- 확인됨(높음): 모드 분리(`--mode=plan`, `--mode=ask`)와 Cloud handoff(`-c`, `&`)는 장시간 작업 분산에 유효.
- 부분 확인(중간): sandbox 제어(`--sandbox`)는 안전한 커맨드 실행 통제에 유용하나, 현재 레포에서는 기본 정책 우선으로 제한 적용.
- 부분 확인(중간): diff/리뷰 보조 기능은 코드 변경 검증에 유용하나, 본선 판정은 여전히 AIDC 산출물(JSON/CSV)을 SSOT로 유지.
- 검증 필요(낮음): "Remote AI Indexing/원격 터널 인덱싱"은 문서 탐색만으로는 세부 동작을 확정하기 어려워, 운영 표준에는 보류한다.

적용 원칙:

- Cursor CLI는 "코드 생성/수정/검토", AIDC는 "판정/증빙"으로 분리.
- 무한 루프 실험은 금지하지 않되, `iteration_limit`, `time_budget`, `go_no_go_gate`를 둔 bounded loop로만 운용.

## 13) 2주 실행 계획 (재정렬, 2026-04 기준)

### Sprint 목표

- 목표 1: 과장/은유 용어를 공학 용어로 치환하고 대외 문구 리스크를 제거한다.
- 목표 2: A/B 벤치 결과를 제3자가 재현 가능한 증빙 번들로 고정한다.
- 목표 3: `NO_GO` 원인을 분해하고 개선 실험으로 `GO` 가능성을 검증한다.

### Week 1 — 용어/증빙 잠금

#### D1-D2: 문구 리팩터링 잠금

- 담당: 제품/문서 + 엔지니어 리뷰 1인
- 작업:
  - "4D 압축/복원" 표현을 "다기준 리스크 스코어링(MCDA) + 정책형 토큰 절감"으로 치환
  - 금지/허용 문구를 §2, §10 기준으로 일관화
  - 금지 문구 자동 스캔 실행:
    - `rg "Zero-Hallucination|항상 우수|XX% 개선 확정|신비주의 엔진|4D 압축/복원" docs/final`
- 완료 게이트:
  - 대외 제출 스코프(본 문서 + 제출 패키지) 금지 문구 잔존 0건
  - `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`의 구현 서술과 충돌 0건

주의: Fact-Lock/헌법 문서에는 용어 설명 목적의 "금지 문구 예시"가 남을 수 있으므로, 스캔 판정은 `external_submission_scope`(제출 패키지) 기준으로 별도 집계한다.

#### D3-D4: 재현 명령 고정

- 담당: 벤치 오너
- 작업:
  - `benchmark_manifest.json`, `repro_command.txt`, `ab_result_summary.json`, `ab_result_timeseries.csv`, `power_profile.csv`, `aidc_kpi_gate.json` 재생성
  - 동일 입력/시드/비용가정으로 baseline+treatment 2회 반복
- 완료 게이트:
  - 2회 실행에서 Go/No-Go 판정 일치
  - 누락 파일 0건(§6 체크리스트 기준)

#### D5-D7: 통계 검정 재확인

- 담당: 데이터 검증
- 작업:
  - Wilson 95% CI, p-value, bootstrap diff 재계산
  - 비유의/악화 구간을 요약문에 명시
- 완료 게이트:
  - `ab_result_summary.json`에 CI/p-value 필드 누락 0건
  - 실패 케이스 보고 포함

### Week 2 — 개선 실험/판정

#### D8-D10: 개선 실험 (bounded)

- 담당: 엔지니어
- 작업:
  - Track A/B 파라미터 스윕(전략, 강도, cap, must_keep 정책)
  - Perf/W와 정확도 동시 측정
- 완료 게이트:
  - 실험별 `iteration_limit`, `time_budget` 기록
  - 모든 실험에 실패/성공 사유 기록

#### D11-D12: 게이트 판정

- 담당: 벤치 오너 + 리뷰어
- 작업:
  - `aidc_kpi_gate_v2.json` 생성
  - 3대 조건 평가: Perf/W, 동일 정확도 유지, SLA 유지
- 완료 게이트:
  - 3조건 모두 충족 시 `GO`, 하나라도 미달 시 `NO_GO`
  - 판정 근거 경로를 JSON에 명시

#### D13-D14: 제출 패키지 잠금

- 담당: 대외 제출 담당
- 작업:
  - 심사용 한 문단(§7)과 KPI 표를 최신 수치로 갱신
  - "주장"과 "증빙 파일 경로" 1:1 매핑 점검
- 완료 게이트:
  - 외부 공유 패키지에서 과장 문구 0건
  - 제3자 재현 체크 1회 통과

### 운영 원칙 (고정)

- `NO_GO`는 실패가 아니라 품질 신호로 취급하고 그대로 공개한다.
- 수치 없는 주장 금지: 모든 대외 문구는 산출물 경로를 근거로 단다.
- Cursor CLI(코드/리뷰)와 AIDC(판정/증빙) 역할을 혼합하지 않는다.

## 14) 범용 데이터 처리 피벗 실행 계획 (4주)

목적: BTC 테스트베드 성과를 과장 없이 일반 B2B/B2C 데이터 처리 영역으로 확장하되, "90% 압축 의미 보존"은 실험으로 입증되기 전까지 주장하지 않는다.

### 14.1 레일 분리 원칙

- Trading Rail: 기존 BTC/ops 파이프라인 유지(기존 Gate/SSOT 불변)
- General Rail: 범용 문서 코퍼스 전용 벤치 신설(별도 산출물/게이트)
- 승격 규칙: General Rail 결과는 자동으로 Trading Rail에 반영하지 않는다.

### 14.2 Week 1 — 코퍼스/재현성 고정

- [x] 코퍼스 3종 고정: `meeting`, `policy_legal_lite`, `support_faq`
- [x] 공통 스키마 고정: `raw_text`, `domain`, `sensitivity_level`, `expected_key_terms`
- [x] 실험 매니페스트 생성: 데이터 버전, split, seed, 비용 가정, commit hash
- [x] 재현 명령 고정: 단일 명령 2회 실행 시 동일 판정

권장 산출물:
- `docs/final/artifacts/general_compression_benchmark_manifest_v1.json`
- `docs/final/artifacts/general_compression_repro_command_v1.txt`

Week 1 완료 게이트:
- 재현성 체크 통과(동일 입력/시드에서 판정 일치) — `docs/final/artifacts/general_compression_repro_check_v1.json`
- 누락 필드 0건(manifest schema 기준)

### 14.3 Week 2 — 압축 강도 구간 실험(70/80/90%)

- [x] 강도별 A/B 실행: 70%, 80%, 90% 목표 구간 (스윕 `candidate_count=540`)
- [x] KPI 동시 수집: `saving_rate`, `jaccard`, `must_keep_integrity` (추가 KPI는 후속)
- [x] 도메인별 허용오차 표 작성(무관용/완화 구분) — `docs/final/artifacts/general_compression_domain_tolerance_v1.json`

권장 산출물:
- `docs/final/artifacts/general_compression_ab_result_summary_v1.json`
- `docs/final/artifacts/general_compression_ab_result_timeseries_v1.csv`

Week 2 완료 게이트:
- 각 도메인에서 최소 1개 구간이 "품질 허용치 내 + 비용 개선" 충족
- 실패 구간(악화 케이스) 보고 포함

### 14.3.1 실행 스냅샷 (2026-04-07)

- 스윕 결과: `docs/final/artifacts/general_compression_sweep_result_v1.json`
- 판정: `GO` (최적 후보 `strategy=A`, `intensity=high`, `general_max_saving_rate=0.55`, `sensitive_max_saving_rate=0.6`, `hangul_max_saving_rate=0.6`)
- 기준 대비: baseline `saving=0.2963`, `jaccard=0.5531` → best candidate `saving=0.4012`, `jaccard=0.6710`, `sensitive_integrity=1.0`
- 재현성 2회: `general_compression_kpi_gate_v2_run1.json` / `run2.json` 모두 `GO`

### 14.4 Week 3 — 90% Track-B 고압축 검증

- [x] 90% 후보 정책 고정(`must_keep`, cap, strategy/intensity)
- [x] 왜곡/누락/환각 실패 유형 분류 리포트 작성 — `docs/final/artifacts/general_compression_90pct_failure_taxonomy_v1.json`
- [x] 민감 도메인(legal-lite 등)에서 임계 초과 시 자동 `NO_GO` — `docs/final/artifacts/general_compression_domain_guard_gate_v1.json`

권장 산출물:
- `docs/final/artifacts/general_compression_90pct_failure_taxonomy_v1.json`
- `docs/final/artifacts/general_compression_kpi_gate_v2.json`

Week 3 완료 게이트:
- `GO/NO_GO` 판정 JSON 생성
- 판정 근거 파일 경로 100% 명시

### 14.4.1 90% 프로파일 점검 스냅샷 (2026-04-07)

- Failure taxonomy 결과: `decision_90pct_ready = NO_GO`
- 원인: 3개 도메인 모두 `fidelity_below_domain_floor`
- 해석: 90% 고압축은 현재 허용오차 표 기준으로 상용 준비 미달이며, GO 후보(0.55/0.6/0.6) 프로파일을 기본 운영안으로 유지
- Guard gate: `policy_legal_lite` 실패 감지 시 `general_compression_domain_guard_gate_v1`에서 자동 `NO_GO`

### 14.5 Week 4 — 외부 제출 패키지 잠금

- [ ] 외부 onepager에 "통과 지표"만 노출(비유의/실패도 함께 공개)
- [ ] 과장 문구 자동 스캔(`rg`) 통과
- [ ] 가격/비용 시뮬레이션 표 추가(근거 수치 링크 포함)

권장 산출물:
- `docs/final/artifacts/general_compression_external_claims_whitelist_v1.json`
- `docs/final/artifacts/general_compression_pricing_simulation_v1.csv`

Week 4 완료 게이트:
- 대외 패키지 과장 문구 0건
- 제3자 재현 체크 1회 통과

### 14.6 Go/No-Go 판정 규칙 (범용 트랙)

- GO 최소 조건:
  - 비용 절감 지표가 베이스라인 대비 개선(신뢰구간 포함)
  - `must_keep_integrity` 임계치 충족
  - 핵심 task success 저하가 허용 범위 이내
- NO_GO 조건:
  - 90% 고압축에서 의미 왜곡/누락 임계치 초과
  - SLA(지연/오류) 미달
  - 재현 불가 또는 산출물 누락
