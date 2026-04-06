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
