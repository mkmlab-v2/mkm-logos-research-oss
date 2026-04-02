# P0 상용화 트래커 (Bench 우선)

**역할**: 상용화·트레이딩 관련 작업의 **순서·검증 게이트**만 고정한다. 실행 팩트는 매번 로컬/CI로 재확인한다.

## 원칙

1. **순서**: 아래 [순서](#순서)대로만 진행한다.
2. **Bench(모의·테스트) 기본**: 실거래·라이브 실행 전환은 **명시적 지시**가 있을 때만.
3. **팩트 SSOT**: 통과 건수·경로는 **실행 로그** 또는 **트래킹된 파일**이 없으면 인용하지 않는다.

## 순서

| Step | 내용 |
|------|------|
| 1 | 최신 상황: `docs/final/MASTER_SITREP_2026-03-29.md` (또는 당일 SITREP) |
| 2 | 스테이징·승격: `projects/bitcoin-trading/docs/final/STAGING_TO_PRODUCTION_PROMOTION_CHECKLIST_2026-03-25.md` |
| 3 | 실행 규칙·갭: `projects/bitcoin-trading/docs/final/PROPHECY_ALIGNMENT_GAP_MATRIX_2026-03-24.md`, `EXECUTABLE_PROPHECY_RULES_SSOT_2026-03-25.md` |
| 4 | 정렬 pytest 번들(Windows): `projects/bitcoin-trading/ops/v2/tasks/run_prophecy_alignment_pytest.ps1` — **터미널에서는 `py` 사용** (`python` 금지 규칙과 일치). **직렬 게이트**: 1단계 `bitcoin-trading` 내 dual-regime 스모크 + `test_multilens_marginal_utility_harness_v1.py`가 실패하면 2단계 워크스페이스 루트 Fact-Lock(logos snapshot + CROSS_REF + SASANG + 명리 통찰 JSONL + **Thin V2 / 시장 어댑터** 등 명시 목록)은 실행되지 않는다. 건수·버전은 로컬 실행 로그로 확인. 절차 표: `docs/final/MULTI_LENS_INTERMEDIATE_LAYER_WORKLIST.md`. |
| 5 | 보급 루틴(해당 시): `scripts/titan-sync.ps1` (레포 루트 기준) |

## 검증 게이트 (Bench)

- **의도**: 문서에 나열된 `tests/test_*.py` 정렬 번들을 통과시키는 것이 본선 게이트다.
- **Windows**: `cd C:\workspace\projects\bitcoin-trading` 후 `py -m pytest …` (스크립트/체크리스트와 동일 목록).

## 워크스페이스 정합 (확인 필요)

다음은 **이 트래커 작성 시점**에 로컬 트리를 점검한 결과다. 브랜치·동기화 후에는 다시 확인한다.

- **Step 4 스크립트** `projects/bitcoin-trading/ops/v2/tasks/run_prophecy_alignment_pytest.ps1`: (1) `bitcoin-trading`에서 `test_dual_regime_api_smoke.py` + `test_multilens_marginal_utility_harness_v1.py` → 실패 시 종료; (2) 워크스페이스 루트에서 Step 4에 명시된 `tests/test_*.py` 목록만 실행(logos snapshot·CROSS_REF·ENTRY16·명리·만세 포인터·multilens Thin 등). `test_fusion_slice_gate.py` 등 문서·SITREP 전용 경로는 스크립트에 없으면 게이트에 포함되지 않는다.
- **수집 건수 예시(2026-04-02 로컬, 참고용)**: 1단계 19개·2단계 75개 — 목록 변경 시 달라지므로 **고정 수치로 SSOT 삼지 말고** 실행 로그로 확인한다.
- 프로젝트 루트에서 무분별 `py -m pytest -q` 시, `scripts/run_forced_watch_alert_test.py` 등이 수집되어 **수집 단계에서 실패**할 수 있다. 게이트 실행은 **정렬 스크립트 또는 문서에 명시된 파일 목록**으로 제한한다.

**규칙**: `149 passed` / `13 passed` 등 **건수 주장**은 로컬 재실행 또는 CI 아티팩트 없이 보고하지 않는다.

## 운영 브리프 자동화 (월간 체크)

- 러너: `scripts/run_waiting_queue_monthly_check.ps1`
- 생성 순서(팩트락):
  1) `fact_safe_multilens_brief_latest.md` 생성
  2) 월간 체크 로그 JSONL append
  3) `fact_safe_multilens_broadcast_latest.md/.json` 생성 (`--strict-required`)
- 브로드캐스트 필수 필드: `reliability_badge`, `high_reliability_decision`, `gate_reason`, `net`
- 최신 브로드캐스트 산출물:
  - `projects/bitcoin-trading/memory/v2/briefs/fact_safe_multilens_broadcast_latest.md`
  - `projects/bitcoin-trading/memory/v2/briefs/fact_safe_multilens_broadcast_latest.json`

### 주간·월간 SOP (권장 고정, 2026-04)

| 주기 | 러너 | 비고 |
|------|------|------|
| **주간** | `scripts/run_fact_lock_bundle.ps1` | 머지 직후에도 1회 권장. `integrity_guard` + `run_prophecy_alignment_pytest.ps1`와 동일 체인. Multilens P1 주기 갱신 시 동일 스크립트에 `-IncludeP1AB`. |
| **jemaai.cloud 점검 (로컬)** | `scripts/run_jemaai_cloud_completion_chain.ps1` | Fact-Lock·Thin·BTC 앵커·P1(기본)·jemaai MVP 경로 일괄; P1 생략은 `-SkipP1AB`. VPS/nginx는 별도. |
| **월간** | `scripts/run_waiting_queue_monthly_check.ps1` | 브리프·로그·브로드캐스트·(설정 시) Slack. `waiting_queue_monthly_check_log.jsonl`이 팩트 SSOT. |
| **캘린더(운영자)** | 위 두 스크립트 전체 경로를 OS 캘린더·작업 스케줄러 등에 반복 등록 | 레포가 알림을 대신하지 않음; Strategy B로 소프트 스킵 구간은 로그 WARN으로만 남음. |

### Phase B — 픽셀 미디어/예능 방송 (법적·기술적 격벽 고정)

**목표**: `jemaai.cloud` 공개 쇼룸(전광판)은 “투자 리딩”이 아닌 **알고리즘 관찰 예능**으로 포지셔닝하여 대중 트래픽을 확보한다.

**법적 방어선(문구 고정)**:
- 공개 UI는 “매매 지시/권유”가 아니라 **상태 관찰(관측 로그 시각화)**만 제공한다.
- 민감값(금액/노셔널/잔고/실거래 체결가/거래소 UID 등)은 공개 UI에 표시하지 않는다.

**기술적 격벽(데이터 계약 고정)**:
- 공개 프론트는 `public-event.v1` 화이트리스트 필드만 읽는다.
- 실거래 데이터는 직접 송출하지 않고, 반드시 `X-Public-Event-Token` 기반 ingest → `public_event_gateway`의 `latest`를 통해서만 **허용 필드**가 표시된다.

**UI/UX 목표(렌더링 규격 고정)**:
- `Ticker`: 지연 의도/상태 배지/방향 테마/장애 상태(`online|degraded|maintenance`)를 요약 표시.
- `가상 채팅`: 리스크/방향/상태 모드에 따른 “예능 반응”만 생성(민감값 사용 금지).
- `상태 모드`: `Idle / Defend / Attack`을 `risk_level`/`system_status`/`public_signal_direction` 조합으로 매핑하여 캐릭터(픽셀 애니메이션)의 연출 상태로 사용.

### Chronos-Forward KOSPI (산출물 포인터)

- 러너: `scripts/run_chronos_forward_kospi_baseline.ps1` (장시간·에이전트 한계 회피: `-Detached`).
- SSOT: `data/chronos_forward_training/training_result.json`, `data/chronos_forward_training/holdout_2026_result.json` — 완료율·방향일치·오차 등 **수치는 JSON 필드가 팩트**이며, 본 트래커에 숫자를 고정 복사하지 않는다.
- 월간 브리프의 KOSPI/BTC 월간 예측 산출물은 `docs/final/artifacts/prophecy_2026_monthly_kospi_btc_fact_safe_v1.*` 등 별도 아티팩트.

### 소프트 스킵 이행 확정 (권장 B · 2026-04)

**채택:** **권장 B — 핵심 파이프라인 우선.** 주간 `run_fact_lock_bundle.ps1` + 월간 `run_waiting_queue_monthly_check.ps1`가 **exit 0**이면 본선 운영 상태로 본다. 아래 구간은 **레포에 스크립트가 없어 WARN·스킵되는 저우선 공백**이며, **시스템 장애나 코어 오염이 아니다.** 보고 시 **“게이트 미연결 / 미구현 구간”**으로 서술한다. **전략 A(전부 복구)**는 기본 목표로 두지 않는다.

**부분 복구 (전략 A를 쓸 때):** 과금·감사·대외 증빙·쇼룸 운영 등 **요구가 생길 때만** 해당 파일만 추가·연결한다.

| 구간 | B 이행 시 상태 |
|------|------------------|
| B-Track 후단 3스크립트 (`report_logos_timeline_quality_gate.py` 등) | `run_btrack_gate_and_lock.py`가 **파일 없으면 스킵** — 풀 게이트 연결은 미진행 |
| Night Watchman harness (`scripts/night_watchman_harness_v1.ps1`) | 월간 러너가 **파일 없으면 스킵** — 필요 시 스크립트 복구 또는 `-SkipNightWatchmanHarness`를 스케줄에 명시 |
| Billing·cost·regime-switch·fused calibration 등 | **파일 없으면 스킵** — 상용 과금 증빙 필요 시에만 스크립트 추가 검토 |

**심볼 레인 프로필 비교 (`symbol_lane_profile_compare_latest.json`)**

- `dss_delta_count` 등은 **stable vs exploratory 추출 파라미터 차이**로 발생할 수 있다. **시장 구조 변화 단정 금지.**
- 의미 있는 비교: `run_btrack_symbol_lane_gate.py --profile-tag exploratory`에 stable과 다른 `--extract-top-k` / `--extract-min-df` / `--curate-top-k`를 준 뒤 `report_symbol_lane_profile_compare.py` 실행. CLI 한 줄을 런북에 남길 것.

### 2026-04-01 운영 업데이트 (BTC 주력 자동화)

- **주력 라인**: BTC Binance 일일 채점 태스크 활성 (`Bitcoin-WaitingQueue-BTCBinance-Daily`).
- **채점 표준**: `HIT/FAIL/NEUTRAL_DRAW/PENDING_CLOSE` 고정. `PENDING_CLOSE`는 데이터 결손으로 처리.
- **자동 주입 정책**: `DAILY_BTC_BINANCE_D1_RETURN_PCT` 환경변수 우선, 미설정 시 Binance 24h API 조회, 실패 시 `PENDING_CLOSE`.
- **주간 분포 산출물**:
  - `docs/final/artifacts/trinity_weekly_reliability_snapshot_latest.json`
  - `docs/final/artifacts/trinity_scoring_distribution_latest.json`
- **운영 런북(도메인 계획)**:
  - `projects/bitcoin-trading/ops/windows-rehearsal/WAITING_QUEUE_DUAL_BTC_RUNBOOK.md`
  - `projects/bitcoin-trading/ops/windows-rehearsal/DAILY_EXECUTION_INSIGHT_BRIEF_TEMPLATE.md`
- **융합 SOP(Quant → Pixel/NightWatchman)**:
  - 러너: `projects/bitcoin-trading/ops/windows-rehearsal/run_fused_quant_pixel_sop.ps1`
  - dry 태스크: `Bitcoin-Fused-QuantPixel-SOP-Daily`
  - live 태스크: `Bitcoin-Fused-QuantPixel-SOP-Live-Daily`
  - 모드 스위치: `projects/bitcoin-trading/ops/windows-rehearsal/switch_fused_quant_pixel_mode.ps1`

## TurboQuant PoC 보고 규칙

- 러너 템플릿: `scripts/run_rag_turboquant_poc_template.py`
- 산출물: `reports/constitution/btrack_pilot/rag_turboquant_poc_latest.json`
- 팩트락 필드:
  - `synthetic_command_detected`
  - `evidence_tier` (`synthetic_smoke` / `candidate_real_benchmark`)
- **규칙**: `synthetic_smoke` 결과는 파이프라인 검증 용도로만 사용하고, 상용 마진/처리량 수치 근거로 승격하지 않는다.

## Logos 4D 레짐 공명 (SSOT, 워크스페이스 상대 경로)

**프로브**: `scripts/logos_vector_resonance_probe.py` — `--rank-by-regime`, `--regime-map data/regimes/regime_map_btc_ext.json`, `--top-k 100`.

| 역할 | 경로 |
|------|------|
| BTC-ext 레짐 맵 (정의) | `data/regimes/regime_map_btc_ext.json` |
| TOP100 `bull_pump` | `backtest_results/LOGOS_RESONANCE_BULL_PUMP_TOP100_REPORT.json` |
| TOP100 `sideways_accumulation` | `backtest_results/LOGOS_RESONANCE_SIDEWAYS_ACCUMULATION_TOP100_REPORT.json` |
| TOP100 `bear_trend` | `backtest_results/LOGOS_RESONANCE_BEAR_TREND_TOP100_REPORT.json` |
| TOP100 `capitulation` | `backtest_results/LOGOS_RESONANCE_CAPITULATION_TOP100_REPORT.json` |
| 교집합·구분 요약 (파생) | `backtest_results/LOGOS_RESONANCE_REGIME_INTERSECTION_TOP100.json` |

레거시 top-20 산출물(파일명에 `TOP100` 없음)은 동일 `backtest_results/` 아래 `LOGOS_RESONANCE_*_REPORT.json`으로 보관될 수 있다. 본선 인용은 위 **TOP100 + intersection**을 우선한다.

### 통합 레짐 맵 (초안)

- **1차 실물·역사 레이어**: `data/regimes/regime_map.json` — 예: `imf`, `it_bubble`, `lehman`, `covid` 등 30년 QuadFusion 정본 흐름과 연계된 **주(主)** 판도 식별용.
- **BTC-ext 가설·확장 레이어**: `regime_map_btc_ext.json` — `bull_pump`, `sideways_accumulation`, `bear_trend`, `capitulation` 네 ID로 Logos 벡터–지문 정렬·프로브에 사용. Canvas/헌법에서 말한 **1차 실물 우선·2차 보조** 원칙과 동일하게, **BTC-ext 프로브 리포트는 실물 레짐 트리거를 대체하지 않는다**; 리포트·해석·SSOT 경로만 여기에 고정한다.
- **리포트 부착**: 각 TOP100 JSON은 `schema` `logos_resonance_probe_v2`, `rank_mode` `regime_primary`이며 `hits[].verse_id`로 교집합 계산. 파생 `LOGOS_RESONANCE_REGIME_INTERSECTION_TOP100.json`은 동일 `verse_id` 집합에 대한 pairwise·triple·4-way 집계를 담는다.

### 교집합 팩트 (TOP100 기준, 로컬 산출)

- **4개 레짐 공통 `verse_id`**: 0 (네 집합이 서로 불교집합).
- **해석**: 순위가 레짐별 지문에 대해 **서로 다른 상위 100**을 뽑는 구조이면, “범용(universal)” 구절은 **교집합이 아니라** 별도 정의(예: centroid 근접 풀, 또는 낮은 k에서 재스캔)로 잡는 편이 맞다. `distinctive_top100_only_in_regime`는 이 설정에서는 레짐마다 100(전원)이다.

### 해석 시 주의

- 일부 레짐 상위권에서 `cosine_to_regime_fingerprint_4d`가 **음수**로 나올 수 있다(순위는 여전히 코사인 기준).
- `bear_trend` 등은 **이름/고유명사** 구절 비중이 높을 수 있어, 텍스트 레이블 과해석은 피한다.

## 링크

- 루트 헌장 요약: `CLAUDE.md`, `AGENTS.md`
- 체질·구현 경계: `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`
