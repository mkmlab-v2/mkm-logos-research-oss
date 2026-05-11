# MKM 연구(B-track) → 상용/운영(Track A) · 대외 패키징(Track C) 승격 게이트 체크리스트 v1

**역할:** 기획 서술 없이, 레포 SSOT가 고정한 **호출 가능 경로·워크플로·증거 아티팩트**만 나열한다.  
**상위 SSOT:** `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`, `docs/final/P0_COMMERCIALIZATION_TRACKER.md`, `docs/final/COMPRESSION_12M_LEARNINGS_AND_TRACKB_PLAYBOOK_2026-04-08.md` §9.

**전제:** B-track·연구 산출물은 **명시적 승격 절차 없이** Track A 운영 신호·Track C 계약·실매매 파이프라인과 **합선하지 않는다** (`CONSTITUTION` §1.1·격벽).

---

## 표 — 승격 게이트 체크리스트

| ID | 전환(From → To) | 필수 실행·경로 | 증거·아티팩트·통과 조건 | SSOT 근거 |
|----|------------------|----------------|-------------------------|-----------|
| **G0** | 임의 → **헌법 경로 존재** | `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify_p0_constitution_gate_paths.ps1` | **exit 0** — 필수 파일 목록 통과 | `P0_COMMERCIALIZATION_TRACKER.md` 권장 순서 § |
| **G1** | 변경 → **CI 파이프라인 회귀** | `.github/workflows/dual-regime-integrity.yml` (관련 PR 경로 시 실행) | 워크플로 성공 기록(아티팩트 URL 또는 로컬 동등 재현) | `P0` 증거 표 · `CONSTITUTION` 다수 표 |
| **G2** | B-track 압축·복원 → **Track A·대외 주장 가능 여부** | `docs/final/COMPRESSION_12M_LEARNINGS_AND_TRACKB_PLAYBOOK_2026-04-08.md` **§9** (§9.1.1 OpenAPI·성능 잠금 포함) | §9 **체크리스트 완료** 전에는 연구 산출을 상용·프로덕션 팩트로 승격하지 않음 | `P0` 증거 경로 표 |
| **G3** | 로컬 → **압축 KPI·투트랙 무결성** | `scripts/run_compression_automation_chain.ps1` → `scripts/run_ultra_compression_default.py` 등 체인 | `docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json` 등 체인 산출 · 리터럴 시 `MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_LITERAL_V1.json` | `P0` 압축 자동화 체인 절 |
| **G4** | 벤치 → **Track A 대화 비용 시뮬(연계 시)** | `py scripts/run_track_a_conversational_cost_simulation.py` | `docs/final/artifacts/track_a_conversational_cost_simulation_latest.json` · 입력으로 `general_compression_kpi_gate_v2.json` **GO** + `MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json`의 `global_token_saving_rate` 사용 | `P0` L1 표 |
| **G5** | 스텁 → **Track A 섀도우 코퍼스** | `py scripts/run_track_a_shadow_corpus_eval.py` (옵션 `--input-jsonl`) | `docs/final/artifacts/track_a_shadow_corpus_eval_latest.json` · `track_a_shadow_corpus_input_manifest_latest.json` | `P0` |
| **G6** | 운영 관측 → **미터링 밴드 게이트** | `py scripts/check_track_a_metering_band_gate.py` (`warning` \| `block`) | `docs/final/artifacts/track_a_metering_band_gate_latest.json` | `P0` Phase 2 |
| **G7** | API 계약 → **L2 스텁·회귀** | `docs/final/openapi_token_compression_stub_v1.yaml` + `scripts/compression_token_api_stub.py` | `tests/test_compression_token_api_stub.py` 통과 | `P0` L2 표 · `CONSTITUTION` |
| **G8** | JSONL 데이터 → **Track A 허용 행만** | `scripts/core/sovereign_jsonl.py` · `assert_track_a_json_row_allowed` | B-context와 A-context **bulkhead** 위반 없음 | `CONSTITUTION` sovereign iterator 표 |
| **G9** | 멀티 모듈 → **정렬 pytest 번들** | `projects/bitcoin-trading/ops/v2/tasks/run_prophecy_alignment_pytest.ps1` | **exit 0** (직렬: dual-regime 스모크 + harness 실패 시 후속 Step 미실행) | `P0` 순서 표 Step 4–5 |
| **G10** | 머지 전후 → **Fact-Lock 번들** | `scripts/run_fact_lock_bundle.ps1` | exit 0 · 스킵 항목은 “미연결”으로 보고만 | `P0` 주간 권장 |
| **G11** | 기술 산출 → **Track C 대외 패키징** | `docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md` (동결·§3.7) | 법무 디스클레이머·§9 External Messaging · **연구 주장과 상품 주장 분리** | Track C 문서 |
| **G12** | Bench·스테이징 → **실매매·LIVE·외부 과금** | 지휘관 명시 **GO** | `AGENTS.md` · `P0` L3 지휘관 게이트 — 자동 전환 없음 | `P0` L3 |

---

## B-track 가격 방향 예언 레일 — 자동 vs 휴먼 (v1, 2026-05-12)

**범위:** 일일 가설·스코어·히트레이트·`eval_prophecy_promotion_gates`·패널 24h·진화 워치독 등 **관측·연구** 산출. 압축 §9 (`docs/final/COMPRESSION_12M_LEARNINGS_AND_TRACKB_PLAYBOOK_2026-04-08.md` §9)·실매매·Track A 상용·대외 계약 주장과 **합선 금지**; JSON의 `track_wall`·HITL 필드는 해당 산출 SSOT를 따른다.

| 단계 | 자동으로 밀 수 있음 | 사람·고정 정책(자동 합선 금지) | 대표 경로·산출 |
|------|---------------------|-------------------------------|----------------|
| **0 일일 관측** | 가설 번들·OHLCV·`eval_prophecy_promotion_gates_v1`·`fast_promotion_gate_v1`·헬스·proxy streak·`Check-ProphecyPanel24hAlerts`·`check_prophecy_evolution_watchdog_v1` | 스케줄·`-Strict*`·임계·웹훅 env | `scripts/run_btrack_daily_hypothesis_chain.ps1`; `docs/final/artifacts/*prophecy*latest*.json`; `reports/prophecy_*` |
| **1 연구 품질 신호** | pytest·CI·`run_workspace_automation_health.ps1 -IncludeProphecyEvolutionWatchdogSmoke` | 워치독 인자(연령·스트릭·EMA) 합의 후 스케줄에 반영 | `.github/workflows/dual-regime-integrity.yml`; `Register-ProphecyEvolutionWatchdogTask.ps1` |
| **2 게이트 JSON 라벨** | 게이트 스크립트가 `strict_passed`·`auto_promote_ready` 등 **표시만** 기록 | 동 필드만으로 **실매매·본선 설정 자동 변경 없음** | `prophecy_promotion_gates_v1_panel_calibrated_latest.json` 등 |
| **3 Track A·실매매·대외** | — (자동 승격 없음) | 본 문서 **G2·G12**·`projects/bitcoin-trading/docs/final/STAGING_TO_PRODUCTION_PROMOTION_CHECKLIST_2026-03-25.md`·휴먼 승인 JSON | `P0_COMMERCIALIZATION_TRACKER.md`; `scripts/validate_trading_human_execution_approval_v1.py` |

**한 줄 원칙:** 0–2는 매일 스크립트가 증거를 쌓고; **3은 지휘관 GO·법무·스테이징 이후에만** 진행한다.

## 보조 참조(승격과 동일하지 않음)

| 항목 | 경로 | 비고 |
|------|------|------|
| TruthfulQA A/B·게이트 | `scripts/run_truthfulqa_ab_benchmark_v1.py` · `scripts/check_truthfulqa_ab_gate_v1.py` · `scripts/Run-TruthfulQAReproBundleV1.ps1` | B-track·게이트 — `CONSTITUTION` §3.6 |
| LLM 검증 티어 | 로컬·자체 호스팅 우선 → 클라우드 소표본 섀도우 | `P0` LLM 검증 티어 |
| VPS L1 부하 벤치 | `scripts/bench_l1_api_load.py` → `docs/final/artifacts/bench_l1_api_load_latest.json` | `research_only` / draft — SLA 최종은 별도 게이트 |
| 스테이징·거래 승격 | `projects/bitcoin-trading/docs/final/STAGING_TO_PRODUCTION_PROMOTION_CHECKLIST_2026-03-25.md` | 실매매 레일 전용 |

---

**개정:** SSOT 문서 경로 변경 시 본 표의 스크립트 열만 동기화한다. 정책 변경은 `CONSTITUTION`·`P0` 개정에 따른다.

**감사 스냅샷(자동화 보조):** `scripts/build_mkm_promotion_gate_evidence_bundle_v1.py` → `docs/final/artifacts/mkm_promotion_gate_evidence_bundle_v1.json` — G0–G11 경로·스크립트 존재 및 G0 exit code 기록. CI `dual-regime-integrity`에서 P0 직후 실행. **G12 대체 불가.**

**Frozen pointer:** 2026-05-02 초안 — 상위 문서 개정 시 본 파일 상단에 `Revised` 한 줄 추가.
