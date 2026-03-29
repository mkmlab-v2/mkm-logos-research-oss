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
| 4 | 정렬 pytest 번들(Windows): `projects/bitcoin-trading/ops/v2/tasks/run_prophecy_alignment_pytest.ps1` — **터미널에서는 `py` 사용** (`python` 금지 규칙과 일치). |
| 5 | 보급 루틴(해당 시): `scripts/titan-sync.ps1` (레포 루트 기준) |

## 검증 게이트 (Bench)

- **의도**: 문서에 나열된 `tests/test_*.py` 정렬 번들을 통과시키는 것이 본선 게이트다.
- **Windows**: `cd C:\workspace\projects\bitcoin-trading` 후 `py -m pytest …` (스크립트/체크리스트와 동일 목록).

## 워크스페이스 정합 (확인 필요)

다음은 **이 트래커 작성 시점**에 로컬 트리를 점검한 결과다. 브랜치·동기화 후에는 다시 확인한다.

- **현재 본선(2026-03-29 점검)**: `tests/test_dual_regime_api_smoke.py`만 존재. `test_fusion_slice_gate.py`는 미존재(문서 오인용 경로 정리: `MASTER_SITREP_2026-03-29.md` 반영).
- Step 4 스크립트 `ops/v2/tasks/run_prophecy_alignment_pytest.ps1`는 위 스모크 파일만 명시 실행한다.
- `projects/bitcoin-trading/tests/` 아래 **본선 `test_*.py`가 트리에 없을 수 있다** (문서·SITREP에 인용된 경로와 불일치 가능).
- 프로젝트 루트에서 무분별 `py -m pytest -q` 시, `scripts/run_forced_watch_alert_test.py` 등이 수집되어 **수집 단계에서 실패**할 수 있다. 게이트 실행은 **정렬 스크립트 또는 문서에 명시된 파일 목록**으로 제한한다.

**규칙**: `149 passed` / `13 passed` 등 **건수 주장**은 로컬 재실행 또는 CI 아티팩트 없이 보고하지 않는다.

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
