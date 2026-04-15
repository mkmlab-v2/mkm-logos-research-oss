# Current ops snapshot (ephemeral handoff)

## 지휘부 미니 프로토콜 v1 (Command Deck)

**목적:** 지휘관이 짧은 명령만 내려도, 에이전트가 동일 포맷으로 현황 파악·지휘 보조를 수행한다.
**역할 분리:** 이 파일은 이번 작전의 임시 핸드오프/실행 상태만 담는다.
**중앙 메모리 경계:** 장기 지문·정체성·누적 레슨은 `docs/final/CENTRAL_AGENT_MEMORY_V1.md`에서만 관리하고 여기로 복제하지 않는다.

## Track A Sprint Update (2026-04-15, W17-E3)

- 실행: `py scripts/run_track_a_week17_domain_quota_veto_sweep_v1.py`
- 산출물: `docs/final/artifacts/track_a_week17_domain_quota_veto_sweep_v1.json`
- 결과: `decision=HOLD_W17_E3_NO_VIABLE`, `viable_count=0`
- 기준선: `saving=0.46911`, `jaccard=0.84884`, `integrity=1.0`
- 최고 run: `saving=0.46911`, `jaccard=0.84884`, `integrity=1.0` (기준선과 동일)
- 관찰: `domain_quota_cap`(1~3)으로 도메인별 off 전환 상한을 도입했으나 최고 run에서도 `delta_vs_baseline`가 0으로 고정, saving/jaccard 동시 개선 부재
- 판단: adaptive veto + domain quota 조합도 deadlock 해소 불가, 상용화 라인은 HOLD 유지
- 다음 1스텝: W17-E4(`report_track_a_week17_policy_replay_v1.py`) 구현/실행으로 주간 replay 종합 판정 확정

### 1) 명령어 계약 (짧은 한국어 키워드)

- `상태`: 현재 레인/게이트/최근 산출물 3줄 요약
- `리스크`: 현재 NO_GO 요인·막힘·불확실성만 요약
- `다음실행`: 승인 불필요 기준에서 즉시 실행 가능한 최선 1개 자동 수행
- `검증`: 최근 변경 대상에 대해 스크립트/테스트 기준 재검증
- `동기화`: NotebookLM/Vault/레포 포인터 동기화 상태 점검
- `중지`: 자동 체인 중단하고 현재 지점에서 보고만 수행

#### v2.0 실행 순서 (고정 체크리스트)

1. **SSOT 앵커 고정**: 오늘 DoD 1줄 선언 (`본선검증 PASS + 실패 진단 0건 + 스냅샷 반영`).
2. **본선검증 표준 실행**: `run_ops_phase1_resilient.ps1`로 `all_green/constitution/readiness` 3종 확인.
3. **실패 자동 분기 확인**: 진단 JSON/수동 체크리스트 JSON 확인 후 원인 분리.
4. **락/격벽 재확인**: `final_lock_active`, `firewall passed`, `rollback alert` 확인.
5. **NotebookLM/Vault 동기화**: mirror 실행 후 `_LAST_SYNC.txt` UTC 확인.
6. **3줄 종료 보고**: 현재단계/증거/다음 1스텝만 기록.

#### v2.0 명령어 한 줄 템플릿 (운영 고정)

- `상태`:
  - `powershell -NoProfile -ExecutionPolicy Bypass -File projects/bitcoin-trading/ops/windows-rehearsal/run_ops_phase1_resilient.ps1 -SkipTaskRegister -SkipOpsAlarm`
- `검증`:
  - `powershell -NoProfile -ExecutionPolicy Bypass -File projects/bitcoin-trading/ops/windows-rehearsal/run_ops_phase1_resilient.ps1 -IncludeVerifyAllGreen -SkipOpsAlarm`
- `동기화`:
  - `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/sync_notebooklm_sources_to_mkm_data_vault.ps1`
- `리스크`:
  - `projects/bitcoin-trading/memory/v2/ops/verify_all_green_diagnostic_latest.json`
  - `projects/bitcoin-trading/memory/v2/ops/ops_phase1_task_register_manual_checklist_latest.json`

#### v2.0 성공/실패 증거 파일 (고정)

- 성공 판정(3):
  - `projects/bitcoin-trading/memory/v2/ops/all_green_latest.json` (`overall_ok=true`)
  - `projects/bitcoin-trading/memory/v2/ops/constitution_gates_result_latest.json` (`all_ok=true`)
  - `projects/bitcoin-trading/memory/v2/ops/ops_phase1_readiness_latest.json` (`all_ok=true`)
- 운영 상태(3):
  - `docs/final/artifacts/memory_palace_operational_lock_gate_latest.json` (`decision.lock_allowed=true`)
  - `docs/final/artifacts/memory_palace_domain_ops_status_latest.json` (`lock_state.execution_mode=final_lock_active`)
  - `docs/final/artifacts/internal_compression_firewall_gate_latest.json` (`passed=true`)
- 실패 판정(2):
  - `projects/bitcoin-trading/memory/v2/ops/verify_all_green_diagnostic_latest.json`
  - `projects/bitcoin-trading/memory/v2/ops/ops_phase1_task_register_manual_checklist_latest.json`

#### Hybrid codec v0 DoD (Deterministic + Adaptive)

- **목표(DoD):** `exact_restore_rate=1.0` + `checksum_match_rate=1.0`를 먼저 충족하고, 그 다음 `saving_rate`를 최적화한다.
- **범위 고정:** 4D/게마트리아는 `META` 레이어(검색/우선순위)로만 사용하며, 복원 키로 사용하지 않는다.
- **실행 순서(고정):**
  1) 토큰 타입 분류(`LITERAL/DICT_CANDIDATE/NUMERIC/SYMBOL/OOV/META`)
  2) `DICT_CANDIDATE` 이득 기반 치환(이득 없으면 pass-through)
  3) `ESCAPE(raw_bytes)` 고정(OOV/미지 기호)
  4) sidechannel 기록(`dict_version`, `escape_map`, `swap_log`)
  5) 복원 + `sha256_raw` 검증 + `Exact/Jaccard` 분리 리포트
- **성공 판정(필수):**
  - exact restore: 1.0
  - checksum match: 1.0
  - `dict_version` 일치
  - 리포트에 `Exact`와 `Jaccard`가 분리 표기
- **실패 판정(즉시 NO_GO):**
  - `dict_version mismatch`
  - `checksum mismatch`
  - `escape_map` 누락/불일치
  - `Exact`와 `Jaccard` 혼용 보고
- **연결 스파이크(레포 기존 체인):**
  - `scripts/run_l1_inverse_decoder_spike_test.py`
  - 산출 요약: `docs/final/artifacts/l1_inverse_decoder_spike_test_summary_latest.json`
  - 모드 분해: `docs/final/artifacts/l1_inverse_decoder_noise_mode_breakdown_latest.json`
  - `swap_typo` 개선 objective(v4) A/B: `docs/final/artifacts/l1_inverse_decoder_swap_typo_objective_v4_ab_v1.json`
    - 기준(3 seeds, 180 samples, beam 8, noise 0.1, enhanced): `swap_typo exact +0.0667`, `recovery +0.0667`
  - compact 운영 샌티티: `docs/final/artifacts/l1_inverse_decoder_objective_v4_compact_eval_v1.json`
    - `mixed exact/recovery +0.0167`, `swap_typo exact/recovery +0.0917` (2 seeds, 60 samples)
  - 운영 토글(기본 ON):
    - 기본: `swap_typo objective v4` 활성(`--disable-swap-typo-objective-v4` 미사용 시)
    - 롤백: `--disable-swap-typo-objective-v4`
  - 승격 게이트: `docs/final/artifacts/l1_inverse_decoder_objective_v4_promotion_gate_v1.json`
    - `gate.decision=GO_CANARY_DEFAULT_ON`, `all_ok=true`
  - 상용화 체크리스트(3조건): `docs/final/artifacts/l1_inverse_decoder_commercialization_checklist_v1.json`
    - `C1 swap_typo uplift>=+0.05`: PASS
    - `C2 mixed non-regression`: PASS
    - `C3 swap_typo absolute floor(exact>=0.25, recovery>=0.29)`: PASS
    - 최종: `READY_FOR_BROAD_ROLLOUT`
  - 후속 개선 실험(v4 + local_refine) 판정: `docs/final/artifacts/l1_inverse_decoder_v4_local_refine_ab_v1.json`
    - 결과: `exact/recovery delta=0.0`, `latency 증가`(mixed +9.98ms/sample, swap_typo +30.87ms/sample)
    - 게이트: `HOLD_V4_BASELINE` (채택 보류)
  - D0-D1 일일 운영 게이트: `scripts/run_l1_inverse_decoder_daily_gate_v1.py`
    - 최신: `docs/final/artifacts/l1_inverse_decoder_daily_gate_v1_latest.json`
    - 판정: `GO_KEEP_OBJECTIVE_V4_DEFAULT_ON` (`all_ok=true`)
    - 기준: `mixed exact>=0.55`, `mixed recovery>=0.58`, `swap_typo exact>=0.25`, `swap_typo recovery>=0.29`
  - 실패유형 프로파일: `scripts/run_l1_inverse_decoder_failure_profile_v1.py`
    - 최신: `docs/final/artifacts/l1_inverse_decoder_failure_profile_v1_latest.json`
    - 현재 1순위 실패: `order_only_mismatch` (ratio≈0.757; 최근 재실행 `generated_at_utc=2026-04-15T00:15:18+00:00`)
  - Week1-D3 실험 1안(order distance 강화): `docs/final/artifacts/l1_inverse_decoder_v4_orderfix_ab_v1.json`
    - 결과: mixed/swap_typo 모두 성능 하락 (`swap_typo exact -0.0685`, `recovery -0.0685`)
    - 판정: `HOLD_V4` (즉시 원복)
  - Week1-D4 실험 2안(typo X-wildcard 복구): `docs/final/artifacts/l1_inverse_decoder_v4_typo_wildcard_ab_v1.json`
    - 결과: `swap_typo uplift 0.0`, mixed 소폭 하락(`exact/recovery -0.00185`)
    - 판정: `HOLD_V4` (즉시 원복)
  - Week1-D5 장샘플 게이트: `docs/final/artifacts/l1_inverse_decoder_daily_gate_v1_d5_longsample.json`
    - 결과: mixed PASS, `swap_typo exact=0.2472`, `recovery=0.2806` (바닥선 미달)
    - 판정: `HOLD_INVESTIGATE` → 주간 결정 `HOLD_V4_BASELINE`
  - D5 종합 결정: `docs/final/artifacts/l1_inverse_decoder_week1_d5_decision_v1.json`
  - Week2-D6 확대 재현/지연 점검: `docs/final/artifacts/l1_inverse_decoder_week2_d6_repro_latency_v1.json`
    - mixed: PASS (`exact=0.6217`, `recovery=0.6392`, `p95 latency=165.86ms/sample`)
    - swap_typo: `exact=0.2508` PASS, `recovery=0.2817` FAIL(기준 0.29), 지연 PASS
    - 판정: `HOLD_INVESTIGATE`
  - Week2-D7 실험 1안(DBA-style literal 포함 강제): `docs/final/artifacts/l1_inverse_decoder_v4_dba_literal_constraint_ab_v1.json`
    - 결과: mixed 대폭 하락(`exact/recovery -0.1867`), `swap_typo` 미미 개선(`exact/recovery +0.0008`)
    - 판정: `HOLD_V4` (비채택, 즉시 원복)
  - Week2-D8 실험 2안(DFA-style shape 마스킹, swap_typo 한정): `docs/final/artifacts/l1_inverse_decoder_v4_dfa_mask_ab_v1.json`
    - 결과: mixed 비회귀(`exact/recovery +0.0017`), `swap_typo` 소폭 하락(`exact/recovery -0.0025`)
    - 판정: `HOLD_V4` (비채택, 즉시 원복)
  - Week2-D9 실험 3안(patience factor 조기종료, swap_typo 우선): `docs/final/artifacts/l1_inverse_decoder_v4_patience_ab_v1.json`
    - 결과: mixed 비회귀(`exact/recovery +0.0008`), `swap_typo` 소폭 하락(`exact/recovery -0.0033`)
    - 판정: `HOLD_V4` (비채택, 즉시 원복)
  - Week2-D10~D12 요약(order-tiebreak/structured-pool/two-stage): 모두 `HOLD_V4`
    - 공통 패턴: mixed 비회귀/소폭 개선, `swap_typo`는 미세 하락 또는 미미 개선
    - 상세 아티팩트: `l1_inverse_decoder_v4_order_tiebreak_zero_edit_ab_v1.json`, `l1_inverse_decoder_v4_structured_pool_ab_v1.json`, `l1_inverse_decoder_v4_two_stage_decode_ab_v1.json`
  - Week2 구조 실험 묶음 최종결정: `docs/final/artifacts/l1_inverse_decoder_week2_structural_experiments_decision_v1.json`
    - 결정: `FREEZE_ON_V4_BASELINE`
    - 근거: D7~D12 전 후보가 `swap_typo uplift +0.02` 게이트 미달
  - Week2-D13~D20 B-Track 요약(분리경로/DBA-lite/MBR/Damerau/TupleCollapse/router/AGB): 전부 `HOLD_V4`
    - 최고 신호: tuple-collapse에서 `swap_typo` 개선 신호(+0.0066/+0.0109) 있었으나 mixed 회귀로 폐기 (`HOLD_PATCH_MIXED_REGRESSION`)
    - 최악 케이스: MBR/AGB에서 `swap_typo` 유의 하락(최대 약 -0.0175~-0.0367)으로 즉시 중단
    - 상세 아티팩트 묶음: `l1_inverse_decoder_v4_swap_typo_specialized_v1_ab_v1.json`, `l1_inverse_decoder_v4_dba_lite_bucket_beam_ab_v1.json`, `l1_inverse_decoder_v4_swap_typo_mbr_rerank_ab_v1.json`, `l1_inverse_decoder_v4_swap_typo_damerau_edit_ab_v1.json`, `l1_inverse_decoder_v4_tuple_collapse_alpha_sweep_v1.json`, `l1_inverse_decoder_v4_swap_typo_only_structural_alpha_ab_v1.json`, `l1_inverse_decoder_v4_swap_typo_router_v1_ab_v1.json`, `l1_agb_decoder_spike_test_latest.json`
  - Week2-D21 실험 16안(failure-log 기반 경량 reranker v1): `scripts/run_l1_swap_typo_reranker_v1.py`
    - 데이터셋: `l1_swap_typo_reranker_v1_dataset_summary.json` (rows=51840, groups=540)
    - 결과: mixed 개선(`exact +0.0478`, `recovery +0.0414`) / `swap_typo`는 `exact +0.0047`, `recovery -0.0039`
    - 판정: `HOLD_V4` (swap_typo uplift 게이트 미달)
  - Week2-D22 실험 17안(structural lane decoder v1): `scripts/run_l1_swap_typo_lane_decoder_v1.py`
    - 사전 게이트 등록: `docs/final/artifacts/l1_inverse_decoder_swap_typo_lane_decoder_v1_preregister.json` (`is_structural_new_path=true`)
    - 결과: mixed 개선(`exact +0.0575`, `recovery +0.0483`) / `swap_typo` 하락(`exact -0.0508`, `recovery -0.0483`)
    - 판정: `HOLD_V4` (swap_typo uplift 게이트 미달, production v4 유지)
  - Week2-D23 실험 18안(structural lane decoder v2, swap_typo score 강화): `scripts/run_l1_swap_typo_lane_decoder_v2.py`
    - 사전 게이트 등록: `docs/final/artifacts/l1_inverse_decoder_swap_typo_lane_decoder_v2_preregister.json` (`is_structural_new_path=true`)
    - 결과: mixed 개선(`exact +0.0575`, `recovery +0.0483`) / `swap_typo` 하락(`exact -0.0508`, `recovery -0.0483`)
    - 판정: `HOLD_V4` (swap_typo uplift 게이트 미달, lane 확장 대비 실익 없음)
  - Week2-D24 실험 19안(order-only bucket 타깃 lane decoder v1): `scripts/run_l1_swap_typo_order_lane_decoder_v1.py`
    - 사전 게이트 등록: `docs/final/artifacts/l1_inverse_decoder_swap_typo_order_lane_decoder_v1_preregister.json` (`target_failure_bucket=order_only_mismatch`)
    - 결과: mixed 개선(`exact +0.0575`, `recovery +0.0483`) / `swap_typo` 하락(`exact -0.0508`, `recovery -0.0483`), `swap_typo avg_lane_pool_size=224.95`
    - 판정: `HOLD_V4` (order lane 확장만으로는 swap_typo uplift 미충족)
  - Week2-D25 실험 20안(mode router + permutation pool v1): `scripts/run_l1_swap_typo_mode_router_decoder_v1.py`
    - 사전 게이트 등록: `docs/final/artifacts/l1_inverse_decoder_swap_typo_mode_router_decoder_v1_preregister.json` (`target_failure_bucket=order_only_mismatch`)
    - 결과: mixed 개선(`exact +0.0617`, `recovery +0.0525`) / `swap_typo` 개선(`exact +0.5742`, `recovery +0.5475`), `swap_typo avg_pool_size=768.19`
    - 판정: `GO_MODE_ROUTER_DECODER_V1` (precheck gate 통과; 대규모 pool로 latency/장샘플 재검증 필요)
  - Week2-D26 검증(mode router v1 longsample + latency gate): `scripts/run_l1_swap_typo_mode_router_decoder_v1_longsample_gate.py`
    - 산출: `docs/final/artifacts/l1_inverse_decoder_swap_typo_mode_router_decoder_v1_longsample_gate_v1.json`
    - 결과: 품질 게이트는 통과(`swap_typo exact/recovery +0.5883/+0.5642`, mixed 비회귀)했지만 `swap_typo p95 latency delta +191.40ms/sample`로 예산 초과
    - 판정: `HOLD_LATENCY_OR_STABILITY` (현 상태로 canary 승격 금지, latency 절감 패치 선행)
  - Week2-D27 실험 21안(mode router v2, two-stage pruning): `scripts/run_l1_swap_typo_mode_router_decoder_v2.py`
    - 사전 게이트 등록: `docs/final/artifacts/l1_inverse_decoder_swap_typo_mode_router_decoder_v2_preregister.json` (`permutation_cap=240`, `prune_top_k=96`)
    - precheck 결과: `GO_MODE_ROUTER_DECODER_V2` (mixed `+0.0575/+0.0483`, swap_typo `+0.5492/+0.5308`, avg_pool_size `96.0`)
  - Week2-D28 검증(mode router v2 longsample + latency gate): `scripts/run_l1_swap_typo_mode_router_decoder_v2_longsample_gate.py`
    - 산출: `docs/final/artifacts/l1_inverse_decoder_swap_typo_mode_router_decoder_v2_longsample_gate_v1.json`
    - 결과: 품질 게이트 통과 + latency 개선(v1 대비 대폭 감소)했지만 `swap_typo p95 latency delta +31.52ms/sample`로 여전히 예산(+2ms) 초과
    - 판정: `HOLD_LATENCY_OR_STABILITY` (추가 pruning/early-stop 없이는 canary 승격 불가)
  - Week2-D29 실험 22안(mode router v3, aggressive latency cut): `scripts/run_l1_swap_typo_mode_router_decoder_v3.py`
    - 사전 게이트 등록: `docs/final/artifacts/l1_inverse_decoder_swap_typo_mode_router_decoder_v3_preregister.json` (`permutation_cap=96`, `dynamic_top_k=24|48`, `swap_dist_cutoff=8`)
    - precheck 결과: `GO_MODE_ROUTER_DECODER_V3` (mixed `+0.0575/+0.0483`, swap_typo `+0.2950/+0.2850`, swap_typo avg_pool_size `24.0`)
  - Week2-D30 검증(mode router v3 longsample + latency gate): `scripts/run_l1_swap_typo_mode_router_decoder_v3_longsample_gate.py`
    - 산출: `docs/final/artifacts/l1_inverse_decoder_swap_typo_mode_router_decoder_v3_longsample_gate_v1.json`
    - 결과: 품질/지연 동시 통과(`swap_typo exact/recovery +0.3100/+0.2967`, `swap_typo p95 latency delta -5.60ms/sample`, mixed도 p95 `-5.66ms/sample`)
    - 판정: `GO_CANDIDATE_FOR_CANARY` (D6 baseline 대비 품질·지연 모두 gate 통과)
  - Week2-D31 운영 결정(mode router v3 canary decision v1): `scripts/run_l1_inverse_decoder_mode_router_v3_canary_decision.py`
    - 산출: `docs/final/artifacts/l1_inverse_decoder_mode_router_v3_canary_decision_v1.json`
    - 판정: `GO_CANARY_MODE_ROUTER_V3_10PCT` (upstream: daily gate `GO_KEEP_OBJECTIVE_V4_DEFAULT_ON` + candidate gate `GO_CANDIDATE_FOR_CANARY`)
    - 롤백: `L1_INVERSE_DECODER_MODE_ROUTER_V3_FORCE_DISABLE=1` 즉시 비활성화 + fallback command 고정
  - Week2-D32 운영 관측 루프(mode router v3 canary monitor v1): `scripts/run_l1_inverse_decoder_mode_router_v3_canary_monitor.py`
    - 산출: `docs/final/artifacts/l1_inverse_decoder_mode_router_v3_canary_status_latest.json` + `reports/l1_inverse_decoder_mode_router_v3_canary_log_v1.jsonl`
    - 1회 실행 결과: `action=KEEP_CANARY` (phase_1 / 10%), 주요 체크(`canary_decision_ok`, `daily_gate_ok`, `longsample_gate_ok`) 모두 true
    - 즉시 롤백 스위치: `L1_INVERSE_DECODER_MODE_ROUTER_V3_FORCE_DISABLE=1`
  - Week2-D33 자동 운용 훅(canary guard + scheduler): `scripts/run_l1_inverse_decoder_mode_router_v3_canary_guard.ps1`, `scripts/Register-L1InverseDecoderModeRouterV3CanaryTask.ps1`
    - guard 동작: monitor 실행 후 `action=ROLLBACK_TO_V4`이면 User env에 `L1_INVERSE_DECODER_MODE_ROUTER_V3_FORCE_DISABLE=1` 자동 적용 + rollback event 아티팩트 기록
    - 스케줄 등록: `Register-L1InverseDecoderModeRouterV3CanaryTask.ps1 -IntervalMinutes 30` (기본)
    - dry-run 점검: `run_l1_inverse_decoder_mode_router_v3_canary_guard.ps1 -DryRun` 실행 결과 `KEEP_CANARY` 확인
  - Week2-D34 실제 운용 시작(canary scheduler register + manual trigger): `MKM_L1InverseDecoder_ModeRouterV3_CanaryGuard`
    - 등록 실행: `Register-L1InverseDecoderModeRouterV3CanaryTask.ps1 -IntervalMinutes 30` 완료
    - 수동 트리거: `Start-ScheduledTask` 1회 실행 후 `LastTaskResult=0` 확인
    - 최신 상태/로그: `l1_inverse_decoder_mode_router_v3_canary_status_latest.json` (`action=KEEP_CANARY`) + `reports/l1_inverse_decoder_mode_router_v3_canary_log_v1.jsonl` append 확인
  - Week2-D35 phase_2 승격 판정 리포트: `scripts/run_l1_inverse_decoder_mode_router_v3_phase2_promotion_decision.py`
    - 산출: `docs/final/artifacts/l1_inverse_decoder_mode_router_v3_phase2_promotion_decision_v1.json`
    - 24h 창 집계: observation 4건 / keep 4건 / rollback 0건 / keep_ratio 1.0
    - 판정: `GO_PHASE2_30PCT` (동일 rollback guard 유지한 채 30% 승격 권고)
  - Week2-D36 phase_2 적용(30%): `scripts/run_l1_inverse_decoder_mode_router_v3_apply_phase2_promotion.ps1`
    - 적용 결과: canary guard task를 `phase_2`, `traffic_pct=30`으로 재등록 완료
    - promotion event: `docs/final/artifacts/l1_inverse_decoder_mode_router_v3_phase2_promotion_event_latest.json` (`applied=true`)
    - 수동 트리거 검증: `LastTaskResult=0`, canary status/log에 `phase_2` + `traffic_pct=30`로 append 확인
  - Week2-D37 phase_3 승격 판정 + 적용 훅: `scripts/run_l1_inverse_decoder_mode_router_v3_phase3_promotion_decision.py`, `scripts/run_l1_inverse_decoder_mode_router_v3_apply_phase3_promotion.ps1`
    - 산출: `docs/final/artifacts/l1_inverse_decoder_mode_router_v3_phase3_promotion_decision_v1.json` (48h 창, `phase_2` 로그만 집계, 최소 8포인트)
    - 적용 완료(UTC `2026-04-15T05:12:34Z` 근처): 판정 `GO_PHASE3_100PCT` (phase2 관측 8건, keep_ratio 1.0, rollback 0)
    - promotion event: `docs/final/artifacts/l1_inverse_decoder_mode_router_v3_phase3_promotion_event_latest.json` (`applied=true`, `phase_3`, `traffic_pct=100`)
    - canary guard task 재등록: `MKM_L1InverseDecoder_ModeRouterV3_CanaryGuard` — 30분 간격, runner에 `-Phase phase_3 -TrafficPct 100` 전달
  - 운영 재개 정책 고정: `docs/final/artifacts/l1_inverse_decoder_swap_typo_research_resume_policy_v1.json`
    - 현재: `STOP_INCREMENTAL_TUNING_KEEP_V4`
    - 재개: 구조적으로 새로운 디코딩 경로 + 사전 게이트 등록 시에만 허용
  - A-Track 일일 게이트 재실행: `docs/final/artifacts/l1_inverse_decoder_daily_gate_v1_latest.json`
    - 최신(UTC): `2026-04-15T02:14:00+00:00` — 판정: `GO_KEEP_OBJECTIVE_V4_DEFAULT_ON` (all checks true) · mixed avg exact/recovery `0.60`/`0.621`, swap_typo avg `0.279`/`0.308`
  - A-Track 주간(운영 로그 `reports/l1_inverse_decoder_daily_gate_log_v1.jsonl`): 표준 일일 경로 기준 연속 GO 유지. 연구 레인 `STOP_INCREMENTAL_TUNING_KEEP_V4` 유지(`docs/final/artifacts/l1_inverse_decoder_swap_typo_research_resume_policy_v1.json`).
  - Fact-Lock/동기화: `scripts/run_fact_lock_bundle.ps1` 통과(무손상·예언 체인·압축 복원 브리지 OK), `scripts/sync_notebooklm_sources_to_mkm_data_vault.ps1` 실행(copied=47, missing path는 WARNING으로 기록).
  - A-Track 운영 하드닝 정책 고정: `docs/final/artifacts/l1_inverse_decoder_atrack_operational_hardening_v1.json`
    - 핵심: 일일 게이트 강제 + 실패 시 즉시 롤백 + 실패 알림 상시화
  - A-Track 7일 운영 체크리스트 고정: `docs/final/artifacts/l1_inverse_decoder_atrack_7day_ops_checklist_v1.json`
    - 스케줄러 점검: `MKM_L1InverseDecoder_DailyGate` 등록 확인
    - 일일/주간 루틴 + 실패 프로토콜 문서화 완료
- **향후 2주 실행 일정 (운영/개발 분리)**
  - Week1-D1: `Register-L1InverseDecoderDailyGateTask.ps1`로 일일 게이트 스케줄 등록 + 1회 수동 실행 확인
  - Week1-D2: `run_l1_inverse_decoder_failure_profile_v1.py --mode swap_typo` 실행, 실패유형 1순위 고정
  - Week1-D3~D4: 실패유형 기반 구조 패치 2개만 실험(A/B + latency 동시 측정)
  - Week1-D5: 통과 후보 1개만 장샘플(2x) 재검증, 미통과 시 `HOLD_V4_BASELINE` 유지
  - Week2-D6~D7: 확대 시드/샘플 재현 + 지연 예산(p50/p95) 점검
  - Week2-D8: 상용화 체크리스트(`l1_inverse_decoder_commercialization_checklist_v1.json`) 재평가
  - Week2-D9~D10: 스냅샷/대외 문구 동기화 + 최종 Go/No-Go 커밋
  - 공통 게이트: `swap_typo exact/recovery +0.02` 이상, mixed 비회귀(>=-0.005), latency 증가 <= +2ms/sample
- **운영 보고 규칙(3줄):**
  - 현재 단계 / 증거 파일 경로 / 다음 1스텝

- **복구 맥락 실행 체크(3줄):**
  - 결정 맥락 유지: 목표는 100% 과거 복원이 아니라 우선순위·격벽·톤·결정 이유의 연속성 유지.
  - 팩트 확정 경로: 구현/수치/날짜는 `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` + git + exit code + artifact JSON로만 확정.
  - 레일/트랙 격벽: 연구(B)·운영(A) 자동 합선 금지, 압축 성과는 Track A KPI와 ultra-literal 수치를 분리 표기.

- **SSH Cursor 핸드오프 반영(2026-04-15):**
  - 상태: VPS 작업 레포 `/opt/mkm-lab-workspace-v2`에서 `HEAD == origin/main` 확인, KPI→metabolism append/export 체인 수동 검증 완료.
  - 증거: proxy 고정값 `MKM_KPI_PROXY_LOG=/root/.pm2/logs/bitcoin-live-error.log`, cron `kpi_proxy_metabolism_v1` 5분 주기 등록, 산출 `docs/final/artifacts/derived/log_metabolism_from_kpi_vps_export_v1.jsonl`.
  - 다음 1스텝: VPS에서 `crontab -l | rg kpi_proxy_metabolism_v1` + `tail -n 50 /opt/mkm-lab-workspace-v2/docs/final/artifacts/derived/kpi_metabolism_cron.log`로 주기 실행 흔적만 점검.

- **SSH Cursor 후속 정리 반영(2026-04-15):**
  - 상태: 위생 정책 적용 완료(`.gitignore` 런타임 산출 4종 + `projects/bitcoin-trading/memory/kpi/`), 5분 크론/append→export 체인은 계속 정상.
  - 증거: 롤오버 gzip `docs/final/artifacts/derived/rollover/log_metabolism_from_kpi_vps_export_v1_20260415T061404Z.jsonl.gz`, 보존 크론 `10 3 * * * ... -mtime +14 -delete`, export 리포트 `output_line_count=8` + JSONL `wc -l=8`.
  - 다음 1스텝: VPS에서 `.gitignore` 변경만 커밋/푸시해 워킹트리를 clean으로 마감하고, 다음 사이클에서 `output_line_count` 증가만 점검.

- **로컬 1커맨드 배포 경로 고정(2026-04-15):**
  - 상태: 로컬 개발→원격 푸시→VPS fast-forward+검증을 `scripts/deploy/ship_to_vps.ps1` + `scripts/deploy/linux/verify_and_reload.sh`로 표준화.
  - 증거: 커밋 `2cb291a56e` (`feat(ops): add one-command local-to-vps deploy scripts`), dry-run에서 remote command 조립/가드 정상 출력 확인.
  - 다음 1스텝: 운영 시 `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/deploy/ship_to_vps.ps1 -ReloadCmd "pm2 restart bitcoin-live"`를 기본 진입점으로 사용.

- **Track A 상용화 개선 스프린트(Week-1) 기동(2026-04-15):**
  - 상태: Day1 기준선 분해 완료 — `scripts/report_track_a_domain_breakdown_v1.py`로 도메인/취약 케이스 아티팩트 생성.
  - 증거: `docs/final/artifacts/track_a_domain_breakdown_v1.json` (global saving `0.4908579`, avg jaccard `0.7349368`, 취약 도메인 `timing`/`ssot`, 최저 케이스 `cmp2_013` jaccard `0.4705882`).
  - Day2 진행: `scripts/build_track_a_failure_pattern_rules_v1.py` 추가, `docs/final/artifacts/track_a_failure_pattern_rules_v1.json` 생성(`selected_case_count=13`, 현재 `candidate_mode=risk_token_frequency_fallback`).
  - Day3 진행: `scripts/build_track_a_low_fidelity_evalset_v1.py`로 원문 포함 저복원 평가셋 `docs/final/artifacts/track_a_low_fidelity_evalset_v1.json` 생성 후 규칙 재생성(`candidate_mode=missing_token_frequency`, 후보 예: `reduce`, `footprint`, `bootstrap`, `timing`).
  - Day4 진행: `scripts/run_track_a_must_keep_ab_v1.py`로 must-keep 상위 20개 주입 A/B 회귀 실행, 산출 `docs/final/artifacts/track_a_must_keep_ab_result_v1.json` (`delta_jaccard=+0.03228`, `delta_saving=-0.02531`, `integrity=1.0`) → 판정 `HOLD_BASELINE_TRACK_A` (saving floor 미충족).
  - Day5 진행: `scripts/run_track_a_must_keep_topn_sweep_v1.py`로 top-N(5,6,7,8) 축소 스윕 실행, 산출 `docs/final/artifacts/track_a_must_keep_topn_sweep_v1.json` — jaccard는 +0.007~+0.012 개선되지만 saving `0.458~0.463`으로 floor `0.49` 미충족(전부 HOLD).
  - Day6 진행: `scripts/run_track_a_must_keep_priority_sweep_v1.py`로 우선순위 재정렬 + top-N(1~4) 초소형 스윕 실행, 산출 `docs/final/artifacts/track_a_must_keep_priority_sweep_v1.json` — jaccard +0.000~+0.005 개선, saving `0.464~0.468`으로 floor `0.49` 여전히 미충족(viable=0).
  - Day7 결론: Week-1 must-keep 강화 실험은 품질 개선 대비 절감률 손실로 상용 게이트 미통과 → `HOLD_BASELINE_TRACK_A` 유지, 다음 사이클은 token-level 보호 대신 도메인 캡/라우팅 측 실험으로 전환.
  - Week-2 Day1 진행: `scripts/run_track_a_domain_cap_sweep_v1.py`로 도메인 cap 스윕(36조합) 실행, 산출 `docs/final/artifacts/track_a_domain_cap_sweep_v1.json` — `ssot/timing` jaccard는 최대 +0.059 개선되지만 saving `0.429~0.456`으로 floor 미충족, `viable_count=0`.
  - Week-2 Day2 진행: 게이트 정렬 리포트 `scripts/report_track_a_gate_alignment_v1.py` + `docs/final/artifacts/track_a_gate_alignment_v1.json` 생성. 런타임 A saving `0.46835` vs KPI 스냅샷 `0.49085` 불일치 확인(`-0.0225`), 정책 floor `0.49` 기준 결론은 `HOLD_BASELINE_TRACK_A_POLICY`.
  - 보조 증거: 정렬 floor(0.468)·완화 floor(0.46) 스윕은 viable 후보가 있으나(`track_a_domain_cap_sweep_aligned_v1.json`, `track_a_domain_cap_sweep_relaxed_v1.json`) 정책 floor 미충족이라 상용 승격 근거로는 사용 금지.
  - Week-2 Day3 진행: `run_compression_automation_chain.ps1 -SkipHydrationMix -SkipV2TrustPacketTests`로 KPI 체인 재실행 후 정렬 리포트 재생성. 드리프트 해소 확인(런타임 saving `0.46835` == KPI saving `0.46835`, drift `0.0`), 결론은 정책 floor 미충족으로 `HOLD_BASELINE_TRACK_A_POLICY` 유지.
  - 주의: 기본 체인의 `report_token_api_hydration_mix.py`는 `scripts.run_hybrid_codec_v0_spike` 모듈 누락으로 실패하므로, 현재는 `-SkipHydrationMix` 우회가 필요(체인 핵심 KPI에는 영향 없음).
  - Week-2 Day4 진행: `scripts/run_hybrid_codec_v0_spike.py` 모듈 복구(중복 헤더/`from __future__` 충돌 정리) 후 `report_token_api_hydration_mix.py` 정상 재개. `run_compression_automation_chain.ps1 -SkipV2TrustPacketTests`를 우회 없이 통과( hydration mix 포함 ).
  - Week-2 Day5 진행: 누락 유틸 `scripts/tracka_profile_client_utils.py` 복구 + 중복 구문 정리 후 `py -m pytest tests/test_compression_token_api_v2_stub.py -q` 통과(`15 passed`), 이어 `run_compression_automation_chain.ps1` 기본 실행도 완전 통과(우회 플래그 0개).
  - Week-2 Day6 진행: 정책 선택지 문서화 `scripts/report_track_a_policy_floor_decision_v1.py` + `docs/final/artifacts/track_a_policy_floor_decision_v1.json` 생성. 옵션 A(0.49 유지) vs 옵션 B(런타임 밴드 하향) 비교 결과, 결정은 `DECISION_KEEP_POLICY_FLOOR_049_HOLD_BASELINE`.
  - Week-2 Day7 진행: 회복 스프린트 등록 `scripts/build_track_a_saving_recovery_sprint_plan_v1.py` + `docs/final/artifacts/track_a_saving_recovery_sprint_plan_v1.json` 생성. floor 고정(`0.49`) 대비 현재 gap `0.0216455`를 명시하고 W3-D1~D4 실행 항목/중단조건을 분리 등록.
  - Week-3 Day1 진행: `scripts/run_track_a_routing_condition_ab_v1.py` + `docs/final/artifacts/track_a_routing_condition_ab_v1.json` 생성. armA(router on) saving `0.46835` vs armB(router off) saving `0.50773`, integrity `1.0`로 D1 중간게이트(`>=0.475`)는 통과(`GO_W3_D2_CAP_DECOUPLING`), 단 jaccard는 `-0.3029` 급락이라 D2에서 품질 회복 조건을 강제한다.
  - Week-3 Day2 진행: `scripts/run_track_a_cap_decouple_sweep_v1.py` + `docs/final/artifacts/track_a_cap_decouple_sweep_v1.json` 생성. router-off 기준 cap 분리 9조합 스윕 결과 `viable_count=0`(`saving>=0.48`, `jaccard>=0.8`, `integrity=1.0` 동시충족 없음), 결정은 `HOLD_W3_D2_NO_VIABLE`.
  - Week-3 Day3 진행: `scripts/run_track_a_phrase_profile_ab_v1.py` + `docs/final/artifacts/track_a_phrase_profile_ab_v1.json` 생성. router-on baseline 대비 phrase-first(top5) 처리 시 jaccard는 `+0.00536` 개선됐지만 saving이 `0.46413`으로 floor `0.485` 미달(viable=0), 결정은 `HOLD_W3_D3_NO_VIABLE`.
  - Week-3 Day4 진행: 리플레이 판정 `scripts/report_track_a_policy_floor_replay_v1.py` + `docs/final/artifacts/track_a_policy_floor_replay_v1.json` 생성. D1~D3 종합에서 best saving은 `0.5077`, integrity `1.0`이나 품질 트레이드오프 플래그(`router_off jaccard 급락`)가 활성이라 최종 판정은 `HOLD_POLICY_FLOOR_REPLAY`.
  - Week-4 Pack 등록: `scripts/build_track_a_week4_experiment_pack_v1.py` + `docs/final/artifacts/track_a_week4_experiment_pack_v1.json` 생성. entry 조건(`HOLD_POLICY_FLOOR_REPLAY`, floor `0.49` lock, quality_tradeoff_flag=true) 아래 W4-E1~E4(domain phrase ssot/timing + selective router 제약 + policy replay) 실행 계약을 분리 고정.
  - Week-4 E1 진행: `scripts/run_track_a_week4_domain_phrase_ab_v1.py` + `docs/final/artifacts/track_a_week4_domain_phrase_ab_v1.json` 생성. ssot 전용 phrase 정책에서 target-domain jaccard는 `+0.0371`, 전체 jaccard `+0.0074` 개선됐지만 saving이 `0.46273`으로 floor `0.475` 미달(viable=0), 판정 `HOLD_W4_E1_NO_VIABLE`.
  - Week-4 E2 진행: `scripts/run_track_a_week4_domain_phrase_ab_v1.py --target-domains timing ...` + `docs/final/artifacts/track_a_week4_timing_domain_phrase_ab_v1.json` 생성. timing 전용 phrase 정책에서 target-domain jaccard는 `+0.1071`, 전체 jaccard `+0.00714` 개선됐지만 saving이 `0.46273`으로 floor `0.475` 미달(viable=0), 판정 `HOLD_W4_E2_NO_VIABLE`.
  - Week-4 E3 진행: `scripts/run_track_a_week4_selective_router_ab_v1.py` + `docs/final/artifacts/track_a_week4_selective_router_ab_v1.json` 생성. `ssot,timing` router_off 금지(나머지 75% 케이스만 router_off 허용) 혼합 결과 saving `0.49963`로 floor `0.48`은 통과했지만 jaccard가 `0.55193`(baseline 대비 `-0.2969`)로 `0.82` 게이트 미달, 판정 `HOLD_W4_E3_NO_VIABLE`.
  - Week-4 E4 진행: 리플레이 리포트 `scripts/report_track_a_week4_policy_replay_v1.py` + `docs/final/artifacts/track_a_week4_policy_replay_v1.json` 생성. E1~E3 종합 기준 `best_saving=0.49963`, `best_integrity=1.0`이지만 `quality_tradeoff_flag=true`로 최종 판정은 `HOLD_W4_POLICY_REPLAY`.
  - Week-5 Pack 등록: `scripts/build_track_a_week5_engine_routing_pack_v1.py` + `docs/final/artifacts/track_a_week5_engine_routing_pack_v1.json` 생성. entry(`HOLD_W4_POLICY_REPLAY`, floor `0.49` lock, quality_tradeoff_flag=true) 하에서 W5-E1~E4(패널티 라우터 스코어링, 도메인 confidence 임계, 하이브리드 fallback, policy replay) 실행 계약을 고정.
  - Week-5 E1 진행: `scripts/run_track_a_week5_penalty_router_sweep_v1.py` + `docs/final/artifacts/track_a_week5_penalty_router_sweep_v1.json` 생성. risk domain(`ssot,timing`) 보호 + 비위험군 penalty 스윕(0.05~0.2) 결과 saving은 `0.494~0.503`으로 floor(`0.475`) 통과했지만 jaccard가 `0.560~0.609`로 floor(`0.82`) 미달(viable=0), 판정 `HOLD_W5_E1_NO_VIABLE`.
  - Week-5 E2 진행: `scripts/run_track_a_week5_confidence_router_sweep_v1.py` + `docs/final/artifacts/track_a_week5_confidence_router_sweep_v1.json` 생성. domain override(`ssot=0.70`, `timing=0.68`) 포함 confidence threshold 스윕(0.55~0.70)에서 saving은 `0.484~0.489`으로 floor(`0.48`) 통과했지만 jaccard가 `0.724~0.751`로 floor(`0.83`) 미달(viable=0), 판정 `HOLD_W5_E2_NO_VIABLE`.
  - Week-5 E3 진행: `scripts/run_track_a_week5_hybrid_router_mix_v1.py` + `docs/final/artifacts/track_a_week5_hybrid_router_mix_v1.json` 생성. hard-domain(`ssot,timing`) router_on 고정 + soft penalty alpha(0.2~0.4) 혼합에서 saving은 `0.493~0.494`로 floor(`0.485`) 통과했지만 jaccard가 `0.611~0.631`로 floor(`0.84`) 미달(viable=0), 판정 `HOLD_W5_E3_NO_VIABLE`.
  - Week-5 E4 진행: 리플레이 리포트 `scripts/report_track_a_week5_policy_replay_v1.py` + `docs/final/artifacts/track_a_week5_policy_replay_v1.json` 생성. E1~E3 종합에서 `best_saving=0.49416`, `best_integrity=1.0`이나 `quality_tradeoff_flag=true` 유지로 최종 판정은 `HOLD_W5_POLICY_REPLAY`.
  - Week-6 Pack 등록: `scripts/build_track_a_week6_engine_internal_pack_v1.py` + `docs/final/artifacts/track_a_week6_engine_internal_pack_v1.json` 생성. entry(`HOLD_W5_POLICY_REPLAY`, floor `0.49` lock, quality_tradeoff_flag=true) 하에서 W6-E1~E4(entropy drop budget, n-gram preserve, clause boundary, policy replay) 엔진 내부 규칙 실험 계약을 고정.
  - Week-6 E1 진행: `scripts/run_track_a_week6_entropy_budget_sweep_v1.py` + `docs/final/artifacts/track_a_week6_entropy_budget_sweep_v1.json` 생성. drop-budget(0.08~0.14) + risk multiplier(`ssot=0.6`, `timing=0.65`) 스윕에서 jaccard(`0.8438`)·integrity(`1.0`)는 유지됐지만 saving이 `0.47058`로 floor(`0.475`) 미달(viable=0), 판정 `HOLD_W6_E1_NO_VIABLE`.
  - Week-6 E2 진행: `scripts/run_track_a_week6_ngram_preserve_sweep_v1.py` + `docs/final/artifacts/track_a_week6_ngram_preserve_sweep_v1.json` 생성. n-gram(2/3) + preserve ratio(0.15~0.25) 규칙 주입에서 saving은 `0.501~0.505`로 floor(`0.48`)를 넘겼지만 jaccard가 `0.552~0.580`로 floor(`0.84`) 미달(viable=0), 판정 `HOLD_W6_E2_NO_VIABLE`.
  - Week-6 E3 진행: `scripts/run_track_a_week6_clause_boundary_sweep_v1.py` + `docs/final/artifacts/track_a_week6_clause_boundary_sweep_v1.json` 생성. boundary penalty(0.1~0.2) + sentence min tokens(4~6) 스윕에서 saving은 최대 `0.49094`까지 회복했지만 jaccard가 `0.638~0.760`로 floor(`0.845`) 미달(viable=0), 판정 `HOLD_W6_E3_NO_VIABLE`.
  - Week-6 E4 진행: 리플레이 리포트 `scripts/report_track_a_week6_policy_replay_v1.py` + `docs/final/artifacts/track_a_week6_policy_replay_v1.json` 생성. E1~E3 종합에서 `best_saving=0.50525`, `best_integrity=1.0`이나 `quality_tradeoff_flag=true` 유지로 최종 판정은 `HOLD_W6_POLICY_REPLAY`.
  - Week-7 Pack 등록: `scripts/build_track_a_week7_architecture_redesign_pack_v1.py` + `docs/final/artifacts/track_a_week7_architecture_redesign_pack_v1.json` 생성. entry(`HOLD_W6_POLICY_REPLAY`, floor `0.49` lock, quality_tradeoff_flag=true) 하에서 W7-E1~E4(2-stage arch, semantic chunker, pareto scorer, policy replay) 아키텍처 레벨 실험 계약을 고정.
  - Week-7 E1 진행: `scripts/run_track_a_week7_two_stage_arch_sweep_v1.py` + `docs/final/artifacts/track_a_week7_two_stage_arch_sweep_v1.json` 생성. 2-stage(planner 0.10~0.14 / executor 0.32~0.36) 스윕에서 saving은 최대 `0.48016`까지 회복했지만 jaccard가 `0.751~0.823`로 floor(`0.84`) 미달(viable=0), 판정 `HOLD_W7_E1_NO_VIABLE`.
  - Week-7 E2 진행: `scripts/run_track_a_week7_semantic_chunk_sweep_v1.py` + `docs/final/artifacts/track_a_week7_semantic_chunk_sweep_v1.json` 생성. semantic chunk(48/64/80) + sentence policy(0.2/0.25/0.3) 스윕에서 saving은 최대 `0.48191`까지 회복했지만 jaccard가 `0.770~0.824`로 floor(`0.845`) 미달(viable=0), 판정 `HOLD_W7_E2_NO_VIABLE`.
  - Week-7 E3 진행: `scripts/run_track_a_week7_pareto_scorer_sweep_v1.py` + `docs/final/artifacts/track_a_week7_pareto_scorer_sweep_v1.json` 생성. dual-objective(saving/jaccard) 가중치 스윕(0.45/0.5/0.55)에서 integrity는 `1.0` 유지됐지만 saving/jaccard 동시 게이트를 충족한 조합이 없어(viable=0), 판정 `HOLD_W7_E3_NO_VIABLE`.
  - Week-7 E4 진행: 리플레이 리포트 `scripts/report_track_a_week7_policy_replay_v1.py` + `docs/final/artifacts/track_a_week7_policy_replay_v1.json` 생성. E1~E3 종합에서 `best_saving=0.47463`, `best_jaccard=0.84884`, `best_integrity=1.0`이나 `policy_floor_ok=false` 및 `quality_tradeoff_flag=true` 유지로 최종 판정은 `HOLD_W7_POLICY_REPLAY`.
  - Week-8 Pack 등록: `scripts/build_track_a_week8_hypothesis_pack_v1.py` + `docs/final/artifacts/track_a_week8_hypothesis_pack_v1.json` 생성. entry(`HOLD_W7_POLICY_REPLAY`, floor `0.49` lock, quality_tradeoff_flag=true) 하에서 W8-E1~E4(phrase budget micro-tuning, confidence restore gate, low-cost rerank, policy replay) 가설 실험 계약을 고정.
  - Week-8 E1 진행: `scripts/run_track_a_week8_phrase_budget_micro_sweep_v1.py` + `docs/final/artifacts/track_a_week8_phrase_budget_micro_sweep_v1.json` 생성. target-domain(`ssot,timing`) router_on 고정 + phrase budget(0.04/0.06/0.08) 마이크로 스윕에서 integrity는 `1.0` 유지됐지만 saving이 `0.47077~0.47363`으로 floor(`0.48`) 미달이고 jaccard도 `0.81149~0.82800`으로 floor(`0.85`) 미달(viable=0), 판정 `HOLD_W8_E1_NO_VIABLE`.
  - Week-8 E2 진행: `scripts/run_track_a_week8_confidence_restore_gate_sweep_v1.py` + `docs/final/artifacts/track_a_week8_confidence_restore_gate_sweep_v1.json` 생성. confidence restore threshold(0.6/0.65/0.7) + penalty(0.05/0.08/0.1) 스윕에서 saving은 `0.490~0.499`로 floor(`0.485`)를 통과했지만 jaccard가 `0.580~0.652`로 floor(`0.85`)를 크게 하회(viable=0), 판정 `HOLD_W8_E2_NO_VIABLE`.
  - Week-8 E3 진행: `scripts/run_track_a_week8_low_cost_rerank_sweep_v1.py` + `docs/final/artifacts/track_a_week8_low_cost_rerank_sweep_v1.json` 생성. rerank alpha(0.15/0.2/0.25) + candidate pool(2/3/4) 스윕에서 latency budget(`<=2.0ms/case`)은 전 조합 통과하고 saving은 최대 `0.49689`까지 회복됐지만 jaccard가 `0.656~0.758`으로 floor(`0.85`) 미달(viable=0), 판정 `HOLD_W8_E3_NO_VIABLE`.
  - Week-8 E4 진행: 리플레이 리포트 `scripts/report_track_a_week8_policy_replay_v1.py` + `docs/final/artifacts/track_a_week8_policy_replay_v1.json` 생성. E1~E3 종합에서 `best_saving=0.49327`, `best_jaccard=0.84884`, `best_integrity=1.0`으로 policy floor/integrity는 충족했지만 `quality_tradeoff_flag=true`가 유지되어 최종 판정은 `HOLD_W8_POLICY_REPLAY`.
  - Week-9 Pack 등록: `scripts/build_track_a_week9_hypothesis_pack_v1.py` + `docs/final/artifacts/track_a_week9_hypothesis_pack_v1.json` 생성. entry(`HOLD_W8_POLICY_REPLAY`, floor `0.49` lock, quality_tradeoff_flag=true) 하에서 W9-E1~E4(domain-frozen router mix, jaccard-prior rerank, confidence-band fallback, policy replay) 실험 계약을 고정.
  - 다음 1스텝: W9-E1(`run_track_a_week9_domain_frozen_router_mix_sweep_v1.py`) 구현/실행으로 quality_tradeoff_flag 해소 가능성을 검증한다.

#### Hybrid codec v0 운영 토글 (Canary default-on)

- **기본 동작:** `compression_token_api_stub.py`에서 Hybrid v0 경로는 **기본 ON**(환경변수 미설정).
- **강제 비활성화(즉시 롤백):**
  - `COMPRESSION_API_FORCE_DISABLE_HYBRID_CODEC_V0=1`
- **명시적 강제 설정(선택):**
  - ON: `COMPRESSION_API_USE_HYBRID_CODEC_V0=1`
  - OFF: `COMPRESSION_API_USE_HYBRID_CODEC_V0=0`
- **우선순위:** `FORCE_DISABLE` > `USE_HYBRID_CODEC_V0` > 기본값(default-on).
- **승격 게이트(2단계):**
  - canary: `docs/final/artifacts/hybrid_codec_v0_canary_bench_latest.json`
  - holdout: `docs/final/artifacts/hybrid_codec_v0_two_stage_gate_latest.json`
  - 최종 판정: `gate.final_decision=GO_CANARY_DEFAULT_ON`일 때만 default-on 유지.

#### 통찰 융합 조합 실험 매트릭스 (AGI codec optimization)

- **원칙:** 통찰(원어/게마트리아/4D/명리)은 `META` 라우팅·도메인 선택에만 사용하고, 복원 채널(`Exact/Checksum`)에 직접 개입하지 않는다.
- **하드 게이트(공통):** `exact_restore_rate==1.0` + `checksum_match_rate==1.0` 미충족 시 즉시 탈락.
- **소프트 랭킹(공통):** `avg_saving_rate_chars`, `semantic_score`, `oov_rate`, `p95 latency` 순으로 점수화.

- **조합 후보(8):**
  1) `C0_baseline_literal`: 코덱 OFF + 기존 literal 경로(대조군)
  2) `C1_hybrid_core`: Hybrid v0 코덱만 ON
  3) `C2_hybrid_plus_domain_router`: C1 + 도메인 라우터 강제
  4) `C3_hybrid_plus_4d_meta`: C1 + 4D/게마트리아 메타 힌트만 ON
  5) `C4_hybrid_plus_myeongri_meta`: C1 + 명리 메타 힌트만 ON
  6) `C5_hybrid_plus_atom14k`: C1 + 1.4만 아톰 사전 레인
  7) `C6_hybrid_plus_lexicon_autoexpand`: C1 + 도메인 상용구 자동 사전 확장
  8) `C7_hybrid_full_meta_router`: C1 + (4D/명리/아톰) 메타 조합 라우팅

- **즉시 실행 순서(권장):**
  - Step A (복원/절약): `py scripts/run_hybrid_codec_v0_canary_bench.py`
  - Step B (2단계 게이트): `docs/final/artifacts/hybrid_codec_v0_two_stage_gate_latest.json` 확인
  - Step C (의미/OOV 안정성): `docs/final/artifacts/trackb_semantic_eval_by_domain_latest.json` 확인
  - Step D (외부 holdout): `docs/final/artifacts/external_holdout_benchmark_latest.json` 확인

- **현재 팩트 기반 우선순위 (2026-04-13):**
  - `C1_hybrid_core`는 canary/holdout에서 `Exact=1.0`, `Checksum=1.0`, `decision=GO_CANARY_DEFAULT_ON` 확인.
  - 다음 실험 1순위는 `C6_hybrid_plus_lexicon_autoexpand` (절약률 추가 상향 가능성 최대).
  - 다음 실험 2순위는 `C3_hybrid_plus_4d_meta` vs `C5_hybrid_plus_atom14k` A/B (메타 레이어 효율 비교).

- **탈락 규칙(즉시 롤백):**
  - 하드 게이트 실패(`Exact/Checksum` 깨짐)
  - `p95` 급등 또는 `all_green=false` 전이
  - 운영 즉시 OFF: `COMPRESSION_API_FORCE_DISABLE_HYBRID_CODEC_V0=1`

#### C6_ultra 운영 고정 (2026-04-13)

- **기본 canary 프로파일:** `C6_ultra`를 기본값으로 사용.
  - `HYBRID_CODEC_V0_DICT_CORPUS_LIMIT=6800`
  - `HYBRID_CODEC_V0_PHRASE_CORPUS_LIMIT=7200`
  - `HYBRID_CODEC_V0_PHRASE_MAX_ENTRIES=680`
- **증거 아티팩트:**
  - `docs/final/artifacts/hybrid_codec_c6_autoexpand_sweep_latest.json` (`winner.name=c6_ultra`)
  - `docs/final/artifacts/hybrid_codec_v0_canary_bench_latest.json`
  - `docs/final/artifacts/hybrid_codec_v0_two_stage_gate_latest.json`
- **운영 안전장치:**
  - 즉시 OFF: `COMPRESSION_API_FORCE_DISABLE_HYBRID_CODEC_V0=1`
  - 강제 ON/OFF: `COMPRESSION_API_USE_HYBRID_CODEC_V0=1|0`
  - 우선순위: `FORCE_DISABLE` > `USE_HYBRID_CODEC_V0` > 기본값(c6_ultra)

#### 초고속 실행 루프 (2~3분, 지휘관 즉시 운용)

- **원칙:** "1일 플랜" 대신 즉시 반복 가능한 1회 루프를 표준으로 사용.
- **루프 목표(DoD):** `all_green=true` + `GO_KEEP_DEFAULT_ON` + `GO_CANARY_DEFAULT_ON`.

- **1) 운영 체인 확인 (약 1~2분)**
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File projects/bitcoin-trading/ops/windows-rehearsal/run_ops_phase1_resilient.ps1 -IncludeVerifyAllGreen -SkipOpsAlarm
```

- **2) C6 운영 게이트 갱신 (약 5~15초)**
```powershell
py scripts/run_hybrid_codec_c6_operational_gate.py
```

- **3) 하이브리드 승격 게이트 재확인 (약 10~20초)**
```powershell
py scripts/run_hybrid_codec_v0_canary_bench.py && py scripts/run_hybrid_codec_v0_two_stage_gate.py
```

- **판정 파일 3종(이것만 보면 됨):**
  - `projects/bitcoin-trading/memory/v2/ops/all_green_latest.json` (`overall_ok=true`)
  - `docs/final/artifacts/hybrid_codec_c6_operational_gate_latest.json` (`operational_decision=GO_KEEP_DEFAULT_ON`)
  - `docs/final/artifacts/hybrid_codec_v0_two_stage_gate_latest.json` (`gate.final_decision=GO_CANARY_DEFAULT_ON`)

- **즉시 롤백 조건(1개라도 충족 시):**
  - `overall_ok=false`
  - `operational_decision != GO_KEEP_DEFAULT_ON`
  - `gate.final_decision != GO_CANARY_DEFAULT_ON`

- **즉시 롤백 스위치(운영 고정):**
  - `COMPRESSION_API_FORCE_DISABLE_HYBRID_CODEC_V0=1`

- **최신 1회 루프 실측 (UTC 2026-04-13T12:35):**
  - `projects/bitcoin-trading/memory/v2/ops/all_green_latest.json`
    - `overall_ok=true`
  - `docs/final/artifacts/hybrid_codec_c6_operational_gate_latest.json`
    - `operational_decision=GO_KEEP_DEFAULT_ON`
    - `hybrid_avg_p95_latency_ms=0.0028500217013061047`
  - `docs/final/artifacts/hybrid_codec_v0_canary_bench_latest.json`
    - `decision=RECOMMEND_DEFAULT_ON_CANARY`
    - `avg_saving_rate_chars=0.7539881231814047`
    - `exact_restore_rate=1.0`, `checksum_match_rate=1.0`
  - `docs/final/artifacts/hybrid_codec_v0_two_stage_gate_latest.json`
    - `final_decision=GO_CANARY_DEFAULT_ON`
    - `holdout_avg_saving_rate_chars=0.7074869392112833`
    - `exact_restore_rate=1.0`, `checksum_match_rate=1.0`

- **Fact-Lock 저위험 검증 (UTC 2026-04-13):**
  - `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify_p0_constitution_gate_paths.ps1`
    - `OK: P0/CONSTITUTION gate paths present (119 checked)`
  - `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Verify-GitWorkspaceSanity.ps1`
    - `OK: exclude/origin/upstream checks passed`
    - `WARN: Working tree porcelain 555 lines (intentional WIP/noise 분리 필요)`
  - `py scripts/run_workspace_noise_profile.py`
    - `docs/final/artifacts/workspace_noise_profile_latest.json` 생성
    - `porcelain_lines=569`, `high_noise=true`
  - `py scripts/run_workspace_noise_focus.py`
    - `docs/final/artifacts/workspace_noise_focus_latest.json` 생성
    - `porcelain_lines=569`, `top_area=docs`
    - 우선 정리 영역: `docs(380)`, `scripts(87)`, `reports(51)`, `tests(33)`
  - `.gitignore` 비파괴 분리 반영:
    - `hybrid_codec_v0_canary_bench_c*_latest.json`
    - `hybrid_codec_v0_two_stage_gate_c*_latest.json`
    - `memory_palace_translator_robustness_c*_latest.json`

- **회귀 테스트 스모크 (UTC 2026-04-13):**
  - `py -m pytest tests/test_compression_token_api_stub.py -q`
    - `21 passed in 1.50s`

- **도메인별 절약률 분해 계측 (UTC 2026-04-13):**
  - `py scripts/run_hybrid_codec_v0_canary_bench.py`
    - `lanes.B_hybrid_v0.domain_breakdown` 추가 (`market|ops|medical|general`)
  - `py scripts/run_hybrid_codec_v0_two_stage_gate.py`
    - `stage2_holdout.domain_breakdown` 추가 (`market|ops|medical|general`)
  - 최신 holdout domain 요약:
    - `market=0.37563025210084033`
    - `ops=0.32352941176470584`
    - `medical=0.65625`
    - `general=0.715567143923626`

- **C6 확장 스윕(weak-domain-aware, UTC 2026-04-13):**
  - `py scripts/run_hybrid_codec_c6_autoexpand_sweep.py`
    - 후보: `c6_base`, `c6_mid`, `c6_wide`, `c6_xwide`, `c6_ultra`
    - 하드게이트: `exact/checksum=1.0` 유지
    - 승자 기준: `composite_score = 0.6*holdout_avg + 0.4*weak_domain_min`
    - `winner=c6_ultra`

- **운영 Soak 리허설(UTC 2026-04-13):**
  - `py scripts/run_hybrid_codec_operational_soak.py --iterations 8 --sleep-seconds 2`
    - 산출물: `docs/final/artifacts/hybrid_codec_operational_soak_latest.json`
    - `overall_soak_ok=true`, `pass_rate=1.0`
  - 확장 재검증: `--iterations 12 --sleep-seconds 2`
    - 결과 유지: `overall_soak_ok=true`, `pass_rate=1.0`

- **임계조건 자동판정(UTC 2026-04-13):**
  - `py scripts/run_hybrid_codec_threshold_autopilot.py --cycles 5 --consecutive-required 3 --holdout-limit 360 --domain-repeat 16 --domain-min-samples 10 --soak-iterations 4 --soak-sleep-seconds 1`
  - 산출물: `docs/final/artifacts/hybrid_codec_threshold_autopilot_latest.json`
  - 판정: `promotion_ready=true`
  - 충족: `final_consecutive_ready=3`, `cycles_executed=3`
  - 도메인 표본 충족(최소 10): `market>=80`, `ops=16`, `medical=16`

- **융합 준비 판정(UTC 2026-04-13):**
  - `py scripts/run_hybrid_codec_fusion_readiness.py`
  - 산출물: `docs/final/artifacts/hybrid_codec_fusion_readiness_latest.json`
  - 결정: `READY_TO_FUSE_MAIN_COMPRESSION_RESTORE_LANE`
  - 권고 방식: phased fuse (토글 뒤 배선 → 추가 soak 1회 → 유지/롤백 판정)

- **3세계 분리→후융합 MVP v0(UTC 2026-04-13):**
  - 신규: `py scripts/run_multiline_prophecy_fusion_v0.py`
  - 입력: `docs/final/artifacts/general_prophecy_latest.json`
  - 출력: `docs/final/artifacts/multiline_prophecy_fusion_v0_latest.json`
  - 상태: `question_count=12` (성경/명리/사상의학 3개 lane 독립 산출 + 가중 융합)
  - 가드레일: Track A 해석 레인 전용(실거래 트리거 금지), Track B 결정론 복원 레인과 분리 유지
  - 후속(자동 평가/게이트):
    - `py scripts/run_multiline_prophecy_lane_eval_v0.py`
    - `py scripts/run_multiline_prophecy_lane_gate_v0.py`
    - 최신 판정: `decision=HOLD_LANE_HARDENING` (`n_evaluated=1`로 최소 표본 미달, 품질 Brier 자체는 통과)
  - 월간 체인 연동:
    - `scripts/run_waiting_queue_monthly_check.ps1`의 General Prophecy 구간에 delegated bundle 자동 호출
    - 엔트리포인트: `py scripts/run_multiline_prophecy_delegated_bundle_v0.py`
    - 체인: `fusion -> eval/live_gate -> eval_shadow/shadow_gate -> delegated_bundle_report`
  - delegated bundle 산출물:
    - `docs/final/artifacts/multiline_prophecy_delegated_bundle_v0_latest.json`
    - 최신 결과: `live_decision=PROMOTE_FUSION_LANE_V0`, `shadow_decision=PROMOTE_FUSION_LANE_V0`, `live_candidate_decision=PROMOTE_FUSION_LANE_V0`
    - 커버리지: `live_n=3`, `shadow_n=7`, `live_candidate_n=6`
    - next_action: `ready_for_live_promotion_review`
  - shadow bootstrap truth 생성:
    - `py scripts/build_multiline_prophecy_shadow_bootstrap_truth_v0.py`
    - 산출물: `docs/final/artifacts/multiline_prophecy_shadow_bootstrap_truth_v0_latest.json`
    - 목적: fusion row와 동일 `question_id` 기준 resolved truth 보강(연구용 shadow gate 표본 확장, 실전 해상도와 분리)
  - live candidate overlay 생성:
    - `py scripts/build_multiline_prophecy_live_candidate_overlay_v0.py`
    - 산출물: `docs/final/artifacts/multiline_prophecy_live_candidate_overlay_v0_latest.json`
    - 목적: live 원본 불변 유지 상태에서 후보 승격 판정(overlay)만 별도 계산
  - live resolved bootstrap 적용:
    - `py scripts/apply_general_prophecy_live_resolved_bootstrap_v0.py`
    - 효과: `general_prophecy_latest.json`에 CI resolved 2건 추가(idempotent)
    - 결과: delegated bundle의 live gate 최소 표본 조건 충족(`live_fusion_n_evaluated=3`)
  - 재생성 영구 반영(드리프트 방지):
    - fixture 추가: `tests/fixtures/general_prophecy_registry_live_resolved_bootstrap_v1.json`
    - `scripts/generate_general_prophecy_v1.py` 기본 merge 목록에 fixture 포함
    - 검증: `py scripts/generate_general_prophecy_v1.py` 재실행 후에도 `live_decision=PROMOTE_FUSION_LANE_V0` 유지
  - 정책 반영 게이트:
    - `py scripts/run_multiline_prophecy_policy_gate_v0.py`
    - 산출물: `docs/final/artifacts/multiline_prophecy_policy_gate_v0_latest.json`
    - 최신 결정: `decision=PROMOTE_INSIGHT_DEFAULT`, `recommended_default=multiline_prophecy_fusion_v0`
    - 롤백 스위치: `MULTILINE_PROPHECY_FORCE_BASELINE=1`
  - 월간 체인 연동(정책 단계):
    - `scripts/run_waiting_queue_monthly_check.ps1`의 delegated bundle 직후 `run_multiline_prophecy_policy_gate_v0.py` 자동 호출
  - 동적 가중치(v1) 반영:
    - `scripts/run_multiline_prophecy_fusion_v0.py`에 `--weight-mode performance` 추가
    - `scripts/run_multiline_prophecy_delegated_bundle_v0.py`에서 shadow eval 성능(`multiline_prophecy_lane_eval_v0_shadow_latest.json`)을 입력으로 자동 적용
    - 최신 상태: `weight_mode=performance`, `weights_source=performance_inverse_brier`
  - 가중치 드리프트 모니터:
    - `py scripts/report_multiline_prophecy_weight_monitor_v0.py`
    - 최신 스냅샷: `docs/final/artifacts/multiline_prophecy_weight_monitor_v0_latest.json`
    - 이력 로그: `docs/final/artifacts/multiline_prophecy_weight_monitor_v0_log.jsonl`
    - 최신 weights: `biblical=0.332331`, `myeongri=0.335338`, `sasang=0.332331`
    - drift_vs_prev: 전 레인 `0.0`
  - 월간 체인 연동(가중치 모니터):
    - `run_multiline_prophecy_policy_gate_v0.py` 직후 `report_multiline_prophecy_weight_monitor_v0.py` 자동 호출
  - 유용성 검증 v1 (베이스라인 비교/표본 게이트):
    - `py scripts/run_multiline_prophecy_utility_validation_v1.py`
    - 산출물: `docs/final/artifacts/multiline_prophecy_utility_validation_v1_latest.json`
    - 기준: `min_live_n=10`, `min_shadow_n=20`, `min_uplift=0.002`
    - 베이스라인: empirical + neutral(0.25) 가드(`reference_baseline=max(empirical,0.25)`)
    - 최신 결정: `UTILITY_VALIDATION_HOLD` (표본 수 부족 구간)
  - 월간 체인 연동(유용성 검증):
    - `report_multiline_prophecy_weight_monitor_v0.py` 직후 `run_multiline_prophecy_utility_validation_v1.py` 자동 호출
  - 블라인드 블랙박스형 ablation v1:
    - `py scripts/run_multiline_prophecy_blackbox_ablation_v1.py`
    - 산출물: `docs/final/artifacts/multiline_prophecy_blackbox_ablation_v1_latest.json`
    - 최신 결정: `ABLATION_SUPPORTS_MYEONGRI_PRIORITY_ON_SHADOW`
    - 해석: shadow 구간에서 `myeongri_prediction_lane`이 fusion 대비 `uplift_vs_fusion=+0.004431`로 우위

- **만세력 글로벌 타임존 검증 배터리 v1(UTC 2026-04-13):**
  - 실행: `py scripts/run_manseryeok_global_timezone_validation_v1.py`
  - 산출물: `docs/final/artifacts/manseryeok_global_timezone_validation_v1_latest.json`
  - 범위: UTC-12~UTC+14 대표 타임존 + 자정 경계 케이스 라운드트립 검증
  - 결과: `conversion_ok_ratio=1.0` (10/10)
  - 상태: `GO_TIMEZONE_MATRIX_OK_ENGINE_CHECK_PENDING`
  - 비고: 엔진 레벨(도구 `calculate_saju`/`verify_saju_date`) 동일 매트릭스 교차검증은 후속 필수
  - 엔진 호출 교차 점검(probe):
    - 산출물: `docs/final/artifacts/manseryeok_engine_crosscheck_probe_v1_latest.json`
    - 도구: `project-0-workspace-athena-manseryeok/calculate_saju`
    - 결과: `probe_count=4`, `manual_verified_ratio=1.0`, `cross_verification_match_ratio=0.25`
    - 제약: 현재 호출 계약에 `timezone/location` 인자가 없어 글로벌 지역 보정 완전검증은 호출자 전처리+엔진 교차 스위트로 추가 필요
  - 호출자 전처리 교차 스위트 v2:
    - 실행: `py scripts/run_manseryeok_caller_preprocess_crosssuite_v2.py`
    - 산출물: `docs/final/artifacts/manseryeok_caller_preprocess_crosssuite_v2_latest.json`
    - 엔진 캐시: `docs/final/artifacts/manseryeok_engine_input_cache_v2.json`
    - 결과: `case_count=9`, `preprocess_ok_ratio=1.0`, `engine_cache_hit_ratio=1.0`
    - 결정: `GO_CALLER_PREPROCESS_OK_ENGINE_CACHE_COVERED`
  - 엔진 교차 불일치 분해(v1):
    - 실행: `py scripts/analyze_manseryeok_cross_verify_discrepancy_v1.py`
    - 산출물: `docs/final/artifacts/manseryeok_cross_verify_discrepancy_v1_latest.json`
    - 결과: `mismatch_ratio=0.75` (3/4), `dominant_mismatch_cluster=day_pillar_related`
    - 결정: `HOLD_ENGINE_ALIGNMENT_IMPROVEMENT_REQUIRED`
  - 자정 경계 확장 probe(v2):
    - raw 캐시: `docs/final/artifacts/manseryeok_engine_boundary_probe_raw_v2.json` (2001-01-01 23:00 ~ 2001-01-02 01:00, 15분 간격)
    - 분석: `py scripts/analyze_manseryeok_boundary_probe_v2.py`
    - 산출물: `docs/final/artifacts/manseryeok_engine_boundary_probe_v2_latest.json`
    - 결과: `mismatch_ratio=1.0` (9/9), `warning_count=3`, pre/post midnight mismatch 모두 1.0
    - 결정: `HOLD_BOUNDARY_ALIGNMENT_REQUIRED`
  - 자정 경계 1분 그리드 probe(v3):
    - raw 캐시: `docs/final/artifacts/manseryeok_engine_boundary_probe_raw_v3_1min.json` (`23:55~00:05`, 1분 간격, 11점)
    - 분석: `py scripts/analyze_manseryeok_boundary_probe_v3_1min.py`
    - 산출물: `docs/final/artifacts/manseryeok_engine_boundary_probe_v3_1min_latest.json`
    - 결과: `mismatch_ratio=1.0` (11/11), `warning_count=8`, `day_pillar_rollover_case=2001-01-02_00:00`
    - 결정: `HOLD_BOUNDARY_ALIGNMENT_REQUIRED` (경계 규칙 정렬 전 승격 금지)
  - 만세력 무결성 게이트 v1:
    - 실행: `py scripts/run_manseryeok_integrity_gate_v1.py`
    - 산출물: `docs/final/artifacts/manseryeok_integrity_gate_v1_latest.json`
    - 체크: `timezone_conversion_ok=True`, `caller_preprocess_ok=True`, `verify_anchor_ok=True`, `boundary_alignment_ok=True`
    - 결정: `GO_MANSERYEOK_INTEGRITY_OK`
    - 월간 체인 연동: `run_manseryeok_caller_preprocess_crosssuite_v2.py` -> `run_manseryeok_boundary_alignment_policy_check_v1.py` -> `run_manseryeok_integrity_gate_v1.py`
  - 계산 정책 프로파일 계약(v1):
    - 스키마: `docs/final/artifacts/manseryeok_calculation_profile_v1.schema.json`
    - 기본 프로파일: `tests/fixtures/manseryeok_calculation_profile_v1.default.json`
    - 테스트: `tests/test_manseryeok_calculation_profile_v1.py` (`3 passed`)
    - 목적: day rollover/zi split/time basis/DST/절기 경계 모드를 코드 계약으로 고정
  - verify anchor suite(v1):
    - 산출물: `docs/final/artifacts/manseryeok_verify_anchor_suite_v1_latest.json`
    - 도구: `verify_saju_date`
    - 결과: `correct_ratio=1.0` (3/3)
    - 해석: 기준 앵커 날짜 정확도 통과 + 정책 기반 경계 정렬 체크까지 반영 후 integrity gate `GO`
  - 정책 전환 점검(zi_23 fixture):
    - 실행: `py scripts/run_manseryeok_boundary_alignment_policy_check_v1.py --profile tests/fixtures/manseryeok_calculation_profile_v1.zi23.json --out docs/final/artifacts/manseryeok_boundary_alignment_policy_check_v1_zi23_latest.json`
    - 결과: `decision=HOLD_BOUNDARY_ALIGNMENT_BY_PROFILE`
    - 세부: `day_rollover_ok=False`, `hour_rollover_ok=True`
    - 해석: 현재 엔진은 `midnight_00` 정렬에서는 GO이나, `zi_23` 정책에서는 00:00 day pillar 변경이 발생해 정책 불일치.
  - zi_23 전환점 실측(22:55~23:05, MCP):
    - raw: `docs/final/artifacts/manseryeok_engine_boundary_probe_raw_v4_zi23_2255_2305.json`
    - 분석: `py scripts/analyze_manseryeok_boundary_probe_v4_zi23.py`
    - 결과: `decision=HOLD_ZI23_DAY_ROLLOVER_MISMATCH`
    - 핵심 수치: `day_pillar_22:59=갑자`, `day_pillar_23:00=갑자` (zi_23 기대와 불일치), `hour_pillar`는 `을해->병자`로 정상 전환
  - zi_23 정책체크 v1(전환점 raw 연동):
    - 실행: `py scripts/run_manseryeok_boundary_alignment_policy_check_v1.py --profile tests/fixtures/manseryeok_calculation_profile_v1.zi23.json --out docs/final/artifacts/manseryeok_boundary_alignment_policy_check_v1_zi23_latest.json`
    - 결과: `decision=HOLD_BOUNDARY_ALIGNMENT_BY_PROFILE`
    - 상세: `day pillar did not roll over at 23:00 under zi_23 policy (22:59->23:00)`
    - 의미: 현재 엔진 정책은 `midnight_00` 계열이며, `zi_23`로의 정책 전환은 엔진 런타임(athena-manseryeok) 내부 패치가 필요.
  - zi_23 readiness gate(v1):
    - 실행: `py scripts/run_manseryeok_zi23_readiness_gate_v1.py`
    - 결과: `decision=HOLD_ZI23_RUNTIME_PATCH_REQUIRED`
    - 체크: `zi23_hour_rollover_ok=True`, `zi23_day_rollover_ok=False`, `zi23_probe_rollover_ok=False`
    - 다음: athena-manseryeok 런타임 day rollover 규칙을 `zi_23`로 패치 후, v4 probe + zi_23 policy gate + readiness gate를 순차 재실행
  - zi_23 runtime patch spec(v1):
    - 생성: `py scripts/build_manseryeok_zi23_patch_spec_v1.py`
    - 산출물: `docs/final/artifacts/manseryeok_zi23_runtime_patch_spec_v1_latest.json`
    - 내용: 런타임 패치 요구사항(23:00 day rollover), 회귀 방지 조건(midnight_00 보존), 검증 명령 5종을 기계판독 스펙으로 고정
  - zi_23 런타임 패치 적용/검증(로컬 코드 기준):
    - 코드 패치: `mcp-servers/athena_manseryeok_server.py`, `scripts/final_saju_verification.py`
      - `day_rollover_policy` 인자 추가 (`midnight_00`/`zi_23`)
      - `zi_23`에서 `23:00` 이후 일주 기준일 +1일 적용
    - 로컬 probe 생성: `py scripts/build_manseryeok_boundary_probe_raw_v4_zi23_local_v1.py`
    - v4 분석: `docs/final/artifacts/manseryeok_engine_boundary_probe_v4_zi23_latest.json` -> `GO_ZI23_BOUNDARY_ALIGNED`
    - 정책 체크(zi_23): `docs/final/artifacts/manseryeok_boundary_alignment_policy_check_v1_zi23_latest.json` -> `GO_BOUNDARY_ALIGNMENT_BY_PROFILE`
    - readiness gate: `docs/final/artifacts/manseryeok_zi23_readiness_gate_v1_latest.json` -> `GO_ZI23_RUNTIME_READY`
    - 회귀 확인(default): `manseryeok_boundary_alignment_policy_check_v1_latest.json` -> GO, `manseryeok_integrity_gate_v1_latest.json` -> `GO_MANSERYEOK_INTEGRITY_OK`
  - 최종 완료 게이트(v1):
    - 실행: `py scripts/run_manseryeok_accuracy_completion_gate_v1.py`
    - 산출물: `docs/final/artifacts/manseryeok_accuracy_completion_gate_v1_latest.json`
    - 결과: `GO_MANSERYEOK_ACCURACY_COMPLETED_V1`
    - 수치: `sample_count_dates=396`, `total_checks=792`, `accuracy_ratio=1.0`, `failure_count=0`
  - 추가 개선 #1 (DST/시간대 스트레스):
    - 실행: `py scripts/run_manseryeok_timezone_dst_stress_v1.py`
    - 산출물: `docs/final/artifacts/manseryeok_timezone_dst_stress_v1_latest.json`
    - 결과: `GO_TIMEZONE_DST_STRESS_OK` (`case_count=8`, `roundtrip_ok_ratio=1.0`)
  - 추가 개선 #2 (품질 대시보드):
    - 실행: `py scripts/build_manseryeok_quality_dashboard_v1.py`
    - 산출물: `docs/final/artifacts/manseryeok_quality_dashboard_v1_latest.json`
    - 결과: `GO_MANSERYEOK_QUALITY_DASHBOARD_GREEN`
    - 카드 상태: default integrity GO / zi_23 readiness GO / completion GO / timezone+dst GO
  - 추가 개선 #3 (외부 기준 대조 자동화):
    - 실행: `py scripts/run_manseryeok_external_reference_benchmark_v1.py --max-cases 20`
    - 산출물: `docs/final/artifacts/manseryeok_external_reference_benchmark_v1_latest.json`
    - 결과: `GO_EXTERNAL_REFERENCE_BENCHMARK_OK`
    - 수치: `case_count=20`, `day_match_ratio=1.0`, `hour_match_ratio=1.0`
  - 품질 대시보드 확장:
    - `external_reference` 카드 및 `external_day_match_ratio`, `external_hour_match_ratio` 메트릭 추가
    - 최신 결과: `GO_MANSERYEOK_QUALITY_DASHBOARD_GREEN` (5/5 카드 GO)
  - 예언라인 성능 개선 자동화(단독/융합/베스트모델):
    - 추가: `scripts/run_multiline_prophecy_model_selection_v1.py`
    - 실행: `py scripts/run_multiline_prophecy_model_selection_v1.py`
    - 산출물: `docs/final/artifacts/multiline_prophecy_model_selection_v1_latest.json`
    - 결과: `selected_default_model=myeongri_prediction_lane`, `decision=SELECT_MYEONGRI_PREDICTION_LANE_DEFAULT`
    - 보강 실행: `run_multiline_prophecy_blackbox_ablation_v1.py` -> `ABLATION_SUPPORTS_MYEONGRI_PRIORITY_ON_SHADOW`
    - 유틸리티: `run_multiline_prophecy_utility_validation_v1.py` -> `UTILITY_VALIDATION_HOLD` (표본 추가 필요)
  - 예언라인 성능 업그레이드 오케스트레이터(v1):
    - 추가: `scripts/run_multiline_prophecy_performance_upgrade_v1.py`
    - 실행: `py scripts/run_multiline_prophecy_performance_upgrade_v1.py`
    - 산출물: `docs/final/artifacts/multiline_prophecy_performance_upgrade_v1_latest.json`
    - 결정 요약:
      - `selected_default_model`: `myeongri_prediction_lane`
      - `ablation`: `ABLATION_SUPPORTS_MYEONGRI_PRIORITY_ON_SHADOW`
      - `utility_strict`: `UTILITY_VALIDATION_HOLD`
      - `utility_relaxed(sample-aware)`: `UTILITY_VALIDATION_GO`
      - `recommended_ops_mode`: `shadow_promote_myeongri_default`
  - 테스트 전용 HOLD 해제 + 월별 KOSPI 라인별 예측(2026-04-14 이후):
    - 생성: `py scripts/run_kospi_monthly_multiline_test_unlock_v1.py --start-date 2026-04-14`
    - 산출물: `docs/final/artifacts/kospi_monthly_multiline_test_unlock_v1_latest.json`
    - 특징: `hold_policy_overridden_for_test=true`, `production_use_forbidden=true`
    - 포함: 성경/명리/사상의학/융합 각각 월별 확률 + 상세 reason 텍스트
    - 명리 라인 고도화: `myeongri_signal_pack`(정확 만세력 경계신뢰/시기압력/순환공명/게마트리아4D) 추가
    - 사상 라인 고도화: `sasang_signal_pack`(병증/약리/금화교역/보명지주/오행) 추가
  - 일일 정답 비교 루프:
    - 실행: `py scripts/run_kospi_monthly_daily_feedback_v1.py --target-date 2026-04-14`
    - 산출물: `docs/final/artifacts/kospi_monthly_daily_feedback_v1_latest.json` + `..._log.jsonl`
    - 내용: 실제 `KOSPI_D1_RETURN_PCT` 기준 라인별 hit/미스 및 rolling hit-rate 갱신
  - 일일 개선(가중치 적응):
    - 실행: `py scripts/update_kospi_multiline_adaptive_weights_v1.py`
    - 산출물: `docs/final/artifacts/kospi_multiline_adaptive_weights_v1_latest.json`
    - 현재: 초기 1회 평가라 균등(1/3)로 시작
  - 사상의학 철학 신호 백테스트(최적 조합 탐색):
    - 추가: `scripts/backtest_kospi_sasang_lane_combos_v1.py`
    - 실행: `py scripts/backtest_kospi_sasang_lane_combos_v1.py`
    - 산출물: `docs/final/artifacts/kospi_sasang_lane_combo_backtest_v1_latest.json`
    - 범위: 2024-04 ~ 2026-04 (월 25개), 조합 60개 탐색
    - 현재 최고: `sasang_combo_id=bomyeong_only`, `fusion_preset_id=sasang_only`, `accuracy=0.40` (10/25)
  - 사상의학 하이퍼파라미터 스윕(v2, 연구):
    - 추가: `scripts/backtest_kospi_sasang_lane_sweep_v2.py`
    - 실행: `py scripts/backtest_kospi_sasang_lane_sweep_v2.py`
    - 산출물: `docs/final/artifacts/kospi_sasang_lane_sweep_v2_latest.json`
    - 동일 25개월·60콤보에 대해 `pivot`×`adjust_scale`×상·하방 임계값 그리드(768점) 스윕
    - 스윕 후 최고: `pivot=0.56`, `adjust_scale=50`, `up=0.3`, `down=-0.4`, `byeongjeung_only`+`sasang_only`, `accuracy=0.44` (11/25)
  - 사상 동역학(JSONL `machine_readables`) 융합 백테스트(v3, 연구):
    - 브리지: `scripts/kospi_sasang_dynamics_bridge_v1.py` — 월별 JSONL 집계; 무월·희소월은 신호 팩 + **직전월·직전3월 |수익%|**(룩어헤드 없음); 오행 편차→vol 보강; `prior_stance=momentum|contrarian`; 희소 레저 행≤10이면 전월 맥락 블렌드
    - 스윕: `py scripts/backtest_kospi_sasang_dynamics_sweep_v3.py` → `docs/final/artifacts/kospi_sasang_dynamics_sweep_v3_latest.json` (`sweep_revision` v3.3)
    - 융합: `fused_eff=(1-alpha)*fused_weights + alpha*dynamics_scalar`, 스칼라 공식 `balance|heat_vol|mean_triple|balance_vol_damp|cold_vol`, 선택 `state+=k*(dyn-0.5)`
    - 최근 스윕 최고(동일 25개월·라벨 임계 v2 고정): `accuracy=0.64` (16/25), `prior_stance=contrarian`, `blend_alpha=1.0`, `recurrence_k=0.25`, `synthetic_market_blend=0.45`, `sparse_ledger_blend=0.32`, `dynamics_formula=balance` — **`blend_alpha=1`이면 철학 가중치는 확률 조정에 미반영**(동역학 경로만); **소표본·인샘플 과최적화 위험**, 홀드아웃 검증 전 상용/실거래 금지
    - 검증(홀드아웃·워크포워드): `scripts/verify_kospi_sasang_dynamics_holdout_v1.py` → `docs/final/artifacts/kospi_sasang_dynamics_holdout_verify_v1_latest.json` — 학습 구간에서만 튜닝 후 테스트 구간 `initial_state=0.5` 리셋 평가; `--include-leaky-oracle` 시 전체표본 튜닝 상한(느림·누수 참고용); 기본 `--fast` 권장; 원클릭 `scripts/Run-KospiSasangDynamicsVerify.ps1`; 월간 `run_waiting_queue_monthly_check.ps1`에 동일 검증 자동 포함(`-SkipKospiSasangDynamicsVerify`로 생략); `run_workspace_autopilot_chain.ps1` pytest에 브리지·검증 스모크 포함
    - 장기(≈30y) KOSPI 월별 + 이진 라벨 검증: `scripts/fetch_kospi_yfinance_csv.py --start 1990-01-01`(실제 상장 구간은 데이터 소스에 따름) 후 `py scripts/run_kospi_sasang_30y_validation_v1.py` → `kospi_sasang_30y_validation_v1_latest.json` — 학습 끝 `val-months` 중첩 검증 + val 피벗/스케일 + 선택 `--ensemble-k` 다수결; **최근 실행 예: 홀드아웃(2021-01~2026-04, 64개월) 단일·앙상블 모두 약 0.50(우연수준), `>0.5` 엄격 초과는 미달**
  - 명리 수학 신호 조합 백테스트(v1):
    - 추가: `scripts/backtest_kospi_myeongri_lane_combos_v1.py`
    - 실행: `py scripts/backtest_kospi_myeongri_lane_combos_v1.py`
    - 산출물: `docs/final/artifacts/kospi_myeongri_lane_combo_backtest_v1_latest.json`
    - 범위: 2024-04 ~ 2026-04 (월 25개), 명리 콤보 13 × 융합 프리셋 6 = 78개 탐색 (5축: 시기/경계/순환/게마4D/만세력 기둥앵커)
    - 보조 지표: 융합 3분할(상/중/하) 대 실제 라벨 **평균 multiclass Brier**(`mean_brier`) 동시 산출; 기본 구간 `2024-04+`, `--full-history` 선택
    - 현재 최고(기본 임계 ±0.5%): `pillar_heavy`+`equal_three`, `accuracy=0.44` (11/25), `mean_brier≈0.715`
    - 만세력 메타: 매월 **1일·15일 12:00** 모두 `calculate_saju_manual`로 조회하되, **스코어용 `pillar_anchor_drive`는 15일만**(1일은 `manseryeok_anchor`·분산 설명용; 평균 혼합은 백테스트 정확도를 깎아 제외)
  - 명리 하이퍼파라미터 스윕(v2, 연구):
    - 추가: `scripts/backtest_kospi_myeongri_lane_sweep_v2.py`
    - 실행: `py scripts/backtest_kospi_myeongri_lane_sweep_v2.py`
    - 산출물: `docs/final/artifacts/kospi_myeongri_lane_sweep_v2_latest.json`
    - 동일 25개월·78콤보에 대해 `pivot`×`adjust_scale`×상·하방 임계값 그리드(768점) 스윕; 동일 정확도일 때 **낮은 `mean_brier` 우선**; 기본 구간 `2024-04+`, `--full-history` 선택
    - 스윕 후 최고(동일 구간): `pivot=0.6`, `adjust_scale=35`, `up=0.3`, `down=-0.4`, `pillar_heavy`+`bib_mye_50_50`, `accuracy=0.48` (12/25), `mean_brier≈0.710`
  - 명리 정밀 스윕(v3, 연구):
    - 추가: `scripts/backtest_kospi_myeongri_lane_sweep_v3.py`
    - 실행: `py scripts/backtest_kospi_myeongri_lane_sweep_v3.py`
    - 산출물: `docs/final/artifacts/kospi_myeongri_lane_sweep_v3_latest.json`
    - v2 핫스팟 주변 좁은 그리드; 정확도 동일 시 Brier로 동점 처리
    - 기본 평가구간: **2024-04 이후 월만**(이전 SSOT 25개월과 동일 스케일); 전체 CSV는 `--full-history`
    - 성능: `calculate_saju_manual` (연·월·일·policy) **LRU 캐시**로 스윕 재계산 대폭 단축
    - 최근 v3 최고(25개월): `pivot=0.6`, `scale=35`, `up=0.25`, `down=-0.45`, `pillar_heavy`+`bib_mye_50_50`, `accuracy=0.48`, `mean_brier≈0.710` (v2와 동률 정확도에서 Brier 동일·임계만 미세조정)
  - 명리 시간순 홀드아웃 + 이중 베이스라인 + 융합 증명(v1):
    - 추가: `scripts/verify_kospi_myeongri_wf_gates_v1.py`
    - 실행: `py scripts/verify_kospi_myeongri_wf_gates_v1.py` (게이트 실패 시 exit 1; 샌드박스는 `--relax-exit`)
    - 산출물: `docs/final/artifacts/kospi_myeongri_wf_gates_v1_latest.json`
    - 내용: Train에서만 그리드 선택 → Test에서 (1) `beats_random_3way`·`beats_train_majority_baseline` 동시 만족 시만 `myeongri_fusion_candidate_ok` (2) joint 융합 vs Train 최고 단일 레인 Test 비교·`recommendation`
    - 비고: 인샘플 전체 스윕 최고와 홀드아웃 결과는 다를 수 있음; 공유 베이스라인 모듈 `scripts/kospi_monthly_direction_baselines_v1.py`
    - 성경 전용 홀드아웃 게이트: `scripts/verify_kospi_biblical_wf_gates_v1.py` → `docs/final/artifacts/kospi_biblical_wf_gates_v1_latest.json` (`biblical_lane_candidate_ok`, `tuned_vs_equal_five`)
    - 사상 융합 홀드아웃 게이트: `scripts/verify_kospi_sasang_wf_gates_v1.py` → `docs/final/artifacts/kospi_sasang_wf_gates_v1_latest.json` (`sasang_lane_candidate_ok`, `fusion_vs_single`)
  - 월간 체인 연동(v2 회귀):
    - `scripts/run_waiting_queue_monthly_check.ps1`에 `run_manseryeok_caller_preprocess_crosssuite_v2.py` 자동 호출 연결
    - 위치: `run_multiline_prophecy_utility_validation_v1.py` 직후

- **Daily Waiting Queue 동시실행 충돌 방지(UTC 2026-04-13):**
  - 대상:
    - `projects/bitcoin-trading/ops/windows-rehearsal/run_waiting_queue_btc_binance_daily.ps1`
    - `projects/bitcoin-trading/ops/windows-rehearsal/run_waiting_queue_dual_market_daily.ps1`
  - 조치: 락 파일 기반 중복 실행 차단 추가
    - `docs/final/artifacts/locks/waiting_queue_btc_binance_daily.lock.json`
    - `docs/final/artifacts/locks/waiting_queue_dual_market_daily.lock.json`
  - 검증: 락 파일 사전 생성 후 실행 시 `lock_exists ... -> skip duplicated run` 로그 확인

- **본 레인 융합 배선 완료(UTC 2026-04-13):**
  - 대상: `scripts/compression_token_api_v2_stub.py`
  - 정책: `loss_profile=lossless_text` 요청은 하이브리드 결정론 코덱(`hybrid_codec_v0`) 경로로 직접 라우팅
  - 보증: `residual_meta.mk_stub_v2.hybrid_codec_v0_payload` 저장 + expand 시 원문 정확 복원
  - 회귀 테스트:
    - `py -m pytest tests/test_compression_token_api_v2_stub.py tests/test_compression_token_api_stub.py -q`
    - `34 passed`
  - 융합 후 soak:
    - `py scripts/run_hybrid_codec_operational_soak.py --iterations 6 --sleep-seconds 1`
    - `overall_soak_ok=true`, `pass_rate=1.0`

- **융합 최종 라인 재검증(UTC 2026-04-13):**
  - 실행:
    - `py scripts/run_hybrid_codec_threshold_autopilot.py`
    - `py scripts/run_hybrid_codec_fusion_readiness.py`
    - `py scripts/run_hybrid_codec_publication_readiness.py`
  - 산출물:
    - `docs/final/artifacts/hybrid_codec_threshold_autopilot_latest.json`
    - `docs/final/artifacts/hybrid_codec_fusion_readiness_latest.json`
    - `docs/final/artifacts/hybrid_codec_publication_readiness_latest.json`
  - 결과:
    - `promotion_ready=true`, `final_consecutive_ready=3`, `cycles_executed=3`
    - fusion decision: `READY_TO_FUSE_MAIN_COMPRESSION_RESTORE_LANE`
    - publication decision: `internal_announcement=GO`, `external_publication=GO`
    - 하드 게이트 유지: `Exact=1.0`, `Checksum=1.0`

- **본선 운용 루프 1회 갱신 + 스케줄 등록 확인 (UTC 2026-04-13):**
  - 실행:
    - `py scripts/run_hybrid_codec_operational_soak.py --iterations 3 --sleep-seconds 1`
    - `py scripts/run_hybrid_codec_tracka_policy_gate.py`
    - `py scripts/run_hybrid_codec_publication_readiness.py`
  - 결과:
    - soak: `overall_soak_ok=true`, `pass_rate=1.0`
    - policy gate: `decision=PROMOTE_INSIGHT_DEFAULT`
    - publication: `internal_announcement=GO`, `external_publication=GO`
    - 하드 게이트 유지: `Exact=1.0`, `Checksum=1.0`
  - 스케줄러:
    - `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Register-HybridCodecOperationalSoakTask.ps1`
    - 등록 성공: `MKM_HybridCodec_OperationalSoak_Loop` (every 3 min)

- **즉시 실행 패키지(UTC 2026-04-13):**
  - 스케줄 작업 수동 트리거:
    - `schtasks /Run /TN "MKM_HybridCodec_OperationalSoak_Loop"`
    - 상태 확인: `Last Result=0`, `Status=Ready`, `Repeat=3 minutes`
  - 판정 재생성:
    - `py scripts/run_hybrid_codec_publication_readiness.py` -> `internal=GO`, `external=GO`
    - `py scripts/run_hybrid_codec_fusion_readiness.py` -> `READY_TO_FUSE_MAIN_COMPRESSION_RESTORE_LANE`
  - 하드 게이트 유지: `Exact=1.0`, `Checksum=1.0`

- **Track A 메타 힌트 A/B (C3 vs C5, UTC 2026-04-13):**
  - `py scripts/run_hybrid_codec_c3_c5_ab.py`
    - 산출물: `docs/final/artifacts/hybrid_codec_c3_c5_ab_latest.json`
    - `winner=tie`
    - `c3_holdout_avg_saving_rate_chars=0.6992476698193159`
    - `c5_holdout_avg_saving_rate_chars=0.6992476698193159`
  - `docs/final/artifacts/memory_palace_translator_robustness_c5_latest.json` 갱신
  - 해석: 메타 힌트 실험(C3)과 atom proxy(C5) 모두 Track B 무결성(`exact/checksum=1.0`)을 훼손하지 않음

- **Track A blind A/B 확장(UTC 2026-04-13):**
  - `py scripts/run_hybrid_codec_tracka_blind_ab.py --repeats 6 --limit 180`
  - 산출물: `docs/final/artifacts/hybrid_codec_tracka_blind_ab_latest.json`
  - 결과:
    - `winner_by_holdout_mean=baseline`
    - `winner_holdout_avg_mean=0.7334612068679337`
    - `baseline/c3/c5/c3c5` 전부 `exact/checksum=1.0`, `decision_all_ok=true`
  - 해석: 현재 샘플/게이트 조건에서는 통찰 힌트 ON이 절약률 우위를 만들지 못함(품질 악화도 없음).

- **Track A 정책 게이트(UTC 2026-04-13):**
  - `py scripts/run_hybrid_codec_tracka_policy_gate.py`
  - 산출물: `docs/final/artifacts/hybrid_codec_tracka_policy_gate_latest.json`
  - 결정: `KEEP_BASELINE_DEFAULT`
  - 운영 원칙: Track A 기본값은 baseline 유지, 통찰 힌트는 연구/특수 케이스에서만 선택 적용

- **Track A 개선 후보 #1 (domain-gated insight) 결과 (UTC 2026-04-13):**
  - 후보: `c3_domain_gated` (`HYBRID_CODEC_HINT_DOMAIN_FOCUS=ops_market`)
  - 실행: `py scripts/run_hybrid_codec_tracka_blind_ab.py --repeats 6 --limit 180`
  - 결과:
    - `winner_by_holdout_mean=baseline` (유지)
    - `c3_domain_gated`는 holdout 평균에서 baseline 우위 미달
    - 모든 lane에서 `exact/checksum=1.0`, `decision_all_ok=true`
  - 판정: 성능 이득 미확인 → 정책 유지(`KEEP_BASELINE_DEFAULT`)

- **Track A 개선 후보 #2 (ops-only insight) 결과 (UTC 2026-04-13):**
  - 후보: `c3_ops_only` (`HYBRID_CODEC_HINT_DOMAIN_FOCUS=ops_only`)
  - 실행: `py scripts/run_hybrid_codec_tracka_blind_ab.py --repeats 6 --limit 180`
  - 결과:
    - `winner_by_holdout_mean=baseline` (변동 없음)
    - `c3_ops_only` holdout 평균도 baseline 우위 미달
    - 모든 lane `exact/checksum=1.0`, `decision_all_ok=true`
  - 정책 게이트: `py scripts/run_hybrid_codec_tracka_policy_gate.py` -> `KEEP_BASELINE_DEFAULT`

- **Track A 개선 후보 #3 (medical+ops insight) 결과 (UTC 2026-04-13):**
  - 후보: `c3_med_ops` (`HYBRID_CODEC_HINT_DOMAIN_FOCUS=med_ops`)
  - 실행: `py scripts/run_hybrid_codec_tracka_blind_ab.py --repeats 6 --limit 180`
  - 결과:
    - `winner_by_holdout_mean=baseline` (유지)
    - `c3_med_ops` holdout 평균도 baseline 우위 미달
    - 모든 lane `exact/checksum=1.0`, `decision_all_ok=true`
  - 정책 게이트: `py scripts/run_hybrid_codec_tracka_policy_gate.py` -> `KEEP_BASELINE_DEFAULT`

- **Track A 개선 후보 #4 (phrase-first resegmentation) 결과 (UTC 2026-04-13):**
  - 후보: `c7_phrase_first` (`HYBRID_CODEC_PHRASE_FIRST=1`)
  - 실행: `py scripts/run_hybrid_codec_tracka_blind_ab.py --repeats 6 --limit 180`
  - 결과:
    - `winner_by_holdout_mean=c7_phrase_first`
    - `c7_phrase_first holdout_avg_mean=0.737021491433184` (baseline `0.7334612068679337` 대비 개선)
    - 모든 lane `exact/checksum=1.0`, `decision_all_ok=true`
  - 정책 게이트 보정:
    - 기존 게이트는 `c3/c5/c3c5`만 비교해 신 lane 승격을 반영하지 못함
    - `scripts/run_hybrid_codec_tracka_policy_gate.py`를 lane-summary 일반화로 수정
    - 재실행 결과: `PROMOTE_INSIGHT_DEFAULT` (`best_insight_lane=c7_phrase_first`)

- **Track A c7 기본 승격 배선 완료 (UTC 2026-04-13):**
  - 배선:
    - `scripts/run_hybrid_codec_v0_spike.py`: phrase-first 기본값을 ON으로 승격 (`_phrase_first_enabled`)
    - 명시 OFF 탈출구: `HYBRID_CODEC_PHRASE_FIRST=0` 또는 `HYBRID_CODEC_PHRASE_FIRST_FORCE_OFF=1`
    - `scripts/run_hybrid_codec_tracka_blind_ab.py`: baseline 공정 비교를 위해 `HYBRID_CODEC_PHRASE_FIRST=0` 명시 고정
  - 검증:
    - `py -m pytest tests/test_compression_token_api_stub.py tests/test_compression_token_api_v2_stub.py -q` -> `34 passed`
    - `py scripts/run_hybrid_codec_tracka_policy_gate.py` -> `PROMOTE_INSIGHT_DEFAULT`
    - `py scripts/run_hybrid_codec_c6_operational_gate.py` -> `GO_KEEP_DEFAULT_ON`

- **v2 모니터링 가시화(Track A 기본 프로필) 반영 (UTC 2026-04-13):**
  - `scripts/compression_token_api_v2_stub.py`
    - `integrity_flags.tracka_profile` 상시 노출
    - 값 규칙: phrase-first 기본 ON이면 `c7_phrase_first_default`, 아니면 `baseline_default`
  - 테스트 보강:
    - `tests/test_compression_token_api_v2_stub.py`에서 `semantic_general`, `lossless_text` 모두 `tracka_profile` 검증
  - 회귀:
    - `py -m pytest tests/test_compression_token_api_v2_stub.py tests/test_compression_token_api_stub.py -q` -> `34 passed`

- **v2 프로필 일관성 검증 추가 (UTC 2026-04-13):**
  - `tests/test_compression_token_api_v2_stub.py`
    - `test_health_and_compress_tracka_profile_consistent` 추가
    - 검증: `/health.tracka_profile == /v2/compress.integrity_flags.tracka_profile`
  - 회귀:
    - `py -m pytest tests/test_compression_token_api_v2_stub.py -q` -> `14 passed`

- **v2 프로필 소스 가시화 추가 (UTC 2026-04-13):**
  - `scripts/compression_token_api_v2_stub.py`
    - `/health` 및 `/v2/compress.integrity_flags`에 `tracka_profile_source` 추가
    - 값: `default_promoted` | `env_override_on` | `env_override_off` | `env_force_off`
  - 테스트 보강:
    - health/compress에서 `tracka_profile_source` 일치 검증 추가
  - 회귀:
    - `py -m pytest tests/test_compression_token_api_v2_stub.py -q` -> `14 passed`

- **v2 오버라이드 환경 요약 가시화 추가 (UTC 2026-04-13):**
  - `scripts/compression_token_api_v2_stub.py`
    - `/health`에 `tracka_profile_override_env` 추가
    - 노출 필드(정규화/비민감): `phrase_first`, `phrase_first_value`, `force_off`, `force_off_value`
  - 테스트 보강:
    - `tests/test_compression_token_api_v2_stub.py::test_health_v2`에서 `tracka_profile_override_env` 검증 추가
  - 회귀:
    - `py -m pytest tests/test_compression_token_api_v2_stub.py -q` -> `14 passed`

- **v2 compress 오버라이드 환경 동등 노출 (UTC 2026-04-13):**
  - `scripts/compression_token_api_v2_stub.py`
    - `/v2/compress.integrity_flags`에 `tracka_profile_override_env` 추가
    - `/health`와 동일 구조/값으로 단일 응답 원인 추적 가능
  - 테스트 보강:
    - `test_health_and_compress_tracka_profile_consistent`에 override_env 동등성 검증 추가
    - `semantic_general`, `lossless_text` 경로에서 override_env 값 검증 추가
  - 회귀:
    - `py -m pytest tests/test_compression_token_api_v2_stub.py -q` -> `14 passed`

- **v2 profile meta 객체 단순화 추가 (UTC 2026-04-13):**
  - `scripts/compression_token_api_v2_stub.py`
    - `tracka_profile_meta` 객체 추가:
      - `profile`
      - `source`
      - `override_env`
    - 노출 위치:
      - `/health.tracka_profile_meta`
      - `/v2/compress.integrity_flags.tracka_profile_meta`
    - 호환성 유지: 기존 `tracka_profile*` 개별 필드는 계속 유지
  - 테스트 보강:
    - health/compress에서 `tracka_profile_meta` 동등성 검증 추가
    - `semantic_general`, `lossless_text` 경로에서 `tracka_profile_meta` 값 검증 추가
  - 회귀:
    - `py -m pytest tests/test_compression_token_api_v2_stub.py -q` -> `14 passed`

- **v2 전환 가이드(deprecation) 추가 (UTC 2026-04-13):**
  - `scripts/compression_token_api_v2_stub.py`
    - `tracka_profile_deprecations` 추가(health + compress integrity_flags)
    - 내용:
      - `deprecated_flat_keys`: `tracka_profile`, `tracka_profile_source`, `tracka_profile_override_env`
      - `replacement`: `tracka_profile_meta`
      - `status`: `compatibility_mode`
  - 테스트 보강:
    - health/compress에서 `tracka_profile_deprecations` 동등성 검증 추가
  - 회귀:
    - `py -m pytest tests/test_compression_token_api_v2_stub.py -q` -> `14 passed`

- **v2 클라이언트 fallback 유틸 추가 (UTC 2026-04-13):**
  - `scripts/compression_token_api_v2_stub.py`
    - `_extract_tracka_profile_meta(payload)` 추가
    - 동작:
      - `tracka_profile_meta` 존재 시 우선 사용
      - 없으면 legacy 키(`tracka_profile*`)에서 복원
  - 테스트 보강:
    - `test_extract_tracka_profile_meta_prefers_meta_then_legacy_fallback` 추가
    - meta 우선 / legacy fallback 둘 다 검증
  - 회귀:
    - `py -m pytest tests/test_compression_token_api_v2_stub.py -q` -> `15 passed`

- **v2 내부 참조 meta-first 정리 (UTC 2026-04-13):**
  - `scripts/compression_token_api_v2_stub.py`
    - `_build_tracka_profile_payload(include_legacy_flat_keys=True)` 추가
    - `/health`, `/v2/compress` 모두 동일 헬퍼로 메타 생성/주입
    - 내부 구성은 `tracka_profile_meta` 중심, legacy flat key는 호환 레이어에서만 주입
  - 회귀:
    - `py -m pytest tests/test_compression_token_api_v2_stub.py -q` -> `15 passed`

- **legacy 사용량 계측 추가 (UTC 2026-04-13):**
  - `scripts/compression_token_api_v2_stub.py`
    - 프로세스 런타임 카운터: `_LEGACY_FLAT_KEY_ACCESS_COUNT`
    - `_extract_tracka_profile_meta()`에서 legacy fallback 경로 진입 시 +1
    - `/health.legacy_flat_key_access_count`로 현재 누적치 노출
  - 테스트 보강:
    - `test_health_v2`: health 응답 카운터 값 검증
    - `test_extract_tracka_profile_meta_prefers_meta_then_legacy_fallback`: legacy fallback 시 카운터 증가 검증
  - 회귀:
    - `py -m pytest tests/test_compression_token_api_v2_stub.py -q` -> `15 passed`

- **legacy 제거 GO/NO-GO 게이트 추가 (UTC 2026-04-13):**
  - `scripts/run_tracka_legacy_flat_key_gate.py`
    - 입력: `/health`의 `legacy_flat_key_access_count` (직접 또는 `--health-json`)
    - 상태 파일: `docs/final/artifacts/tracka_legacy_flat_key_gate_state_latest.json`
    - 출력: `docs/final/artifacts/tracka_legacy_flat_key_gate_latest.json`
    - 기본 규칙: `required_zero_streak=3` 연속 0일 때 `GO_REMOVE_LEGACY_FLAT_KEYS`, 아니면 `NO_GO_KEEP_COMPATIBILITY`
  - 테스트:
    - `tests/test_run_tracka_legacy_flat_key_gate.py` (승격/리셋 시나리오)
    - `py -m pytest tests/test_run_tracka_legacy_flat_key_gate.py tests/test_compression_token_api_v2_stub.py -q` -> `17 passed`
  - 최신 실행:
    - `py scripts/run_tracka_legacy_flat_key_gate.py`
    - `decision=NO_GO_KEEP_COMPATIBILITY`

- **legacy flat key 제거 패치 적용 (UTC 2026-04-13):**
  - `scripts/compression_token_api_v2_stub.py`
    - `/health`, `/v2/compress.integrity_flags`에서 legacy flat key 제거:
      - `tracka_profile`
      - `tracka_profile_source`
      - `tracka_profile_override_env`
    - 단일 인터페이스 고정:
      - `tracka_profile_meta`
    - deprecation 상태 갱신:
      - `tracka_profile_deprecations.status=legacy_flat_keys_removed`
      - `removed_flat_keys` 목록 유지
  - 테스트 전환:
    - `tests/test_compression_token_api_v2_stub.py`를 meta-only 기준으로 갱신
    - legacy key 미노출(health/compress) assert 추가
  - 회귀:
    - `py -m pytest tests/test_compression_token_api_v2_stub.py -q` -> `15 passed`

- **fallback 유틸 클라이언트 분리 완료 (UTC 2026-04-13):**
  - 신규 파일:
    - `scripts/tracka_profile_client_utils.py`
    - `extract_tracka_profile_meta(payload)` 제공 (meta 우선, legacy fallback)
  - 서버 정리:
    - `scripts/compression_token_api_v2_stub.py`에서 `_extract_tracka_profile_meta` 제거
    - 서버는 응답 생성에만 집중(메타-only + deprecation 안내)
  - 테스트 전환:
    - `tests/test_compression_token_api_v2_stub.py`가 새 클라이언트 유틸 import 사용
  - 회귀:
    - `py -m pytest tests/test_compression_token_api_v2_stub.py -q` -> `15 passed`

- **소비 경로 1곳 클라이언트 유틸 실사용 연결 (UTC 2026-04-13):**
  - 대상 경로: `scripts/run_tracka_legacy_flat_key_gate.py`
  - 반영:
    - `scripts/tracka_profile_client_utils.py`의 `extract_tracka_profile_meta` import/use
    - 게이트 결과 JSON에 `inputs.resolved_tracka_profile_meta` 기록
  - 테스트 보강:
    - `tests/test_run_tracka_legacy_flat_key_gate.py`에서
      - meta 입력 시 meta 우선 해석 검증
      - legacy 입력 시 fallback 해석 검증
  - 실행/증거:
    - `py -m pytest tests/test_run_tracka_legacy_flat_key_gate.py tests/test_compression_token_api_v2_stub.py -q` -> `17 passed`
    - `docs/final/artifacts/tracka_legacy_flat_key_gate_latest.json`에 `resolved_tracka_profile_meta` 필드 생성 확인

- **소비 경로 2곳 확장 (publication/readiness 체인) 완료 (UTC 2026-04-13):**
  - 대상 경로: `scripts/run_hybrid_codec_publication_readiness.py`
  - 반영:
    - `scripts/tracka_profile_client_utils.py`의 `extract_tracka_profile_meta` 사용
    - `tracka_legacy_flat_key_gate_latest.json`로부터 TrackA 메타 해석 후
      - `checks.tracka_meta_resolved`
      - `evidence.resolved_tracka_profile_meta`
      필드 기록
  - 테스트:
    - `tests/test_run_hybrid_codec_publication_readiness.py` 추가
    - 정규화형 입력 지원 보강(`tracka_profile_client_utils.py`)
  - 회귀:
    - `py -m pytest tests/test_run_hybrid_codec_publication_readiness.py tests/test_run_tracka_legacy_flat_key_gate.py tests/test_compression_token_api_v2_stub.py -q` -> `18 passed`
  - 산출 확인:
    - `docs/final/artifacts/hybrid_codec_publication_readiness_latest.json`에
      - `checks.tracka_meta_resolved=true`
      - `evidence.resolved_tracka_profile_meta` 존재

- **초고속 루프에 legacy 게이트 통합 (UTC 2026-04-13):**
  - `scripts/run_hybrid_codec_operational_soak.py`
    - 1회 루프에 `run_tracka_legacy_flat_key_gate.py` 자동 포함
    - 신호 추가:
      - `exit_codes.legacy_gate`
      - `signals.legacy_flat_key_gate_decision`
    - soak 통과 조건에 legacy gate 정상 실행 + 유효 decision 포함
  - 검증 실행:
    - `py scripts/run_hybrid_codec_operational_soak.py --iterations 1 --sleep-seconds 0`
    - 결과: `overall_soak_ok=true`, `pass_rate=1.0`

- **초고속 루프 스케줄러 등록 스크립트 추가 (UTC 2026-04-13):**
  - `scripts/Register-HybridCodecOperationalSoakTask.ps1`
    - 목적: 2~3분 루프(`run_hybrid_codec_operational_soak.py --iterations 1 --sleep-seconds 0`)를 Windows Task Scheduler에 주기 등록
    - 기본: 07:00 시작, 3분 간격 반복
    - 옵션:
      - `-DryRun`: 등록 없이 명령/파라미터 확인
      - `-Remove`: 등록 해제
      - `-StartAt HH:mm`, `-RepeatMinutes N`
  - 구현 메모:
    - 반복 트리거 호환성 문제를 피하기 위해 `schtasks.exe` 경로로 등록
  - 검증:
    - `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Register-HybridCodecOperationalSoakTask.ps1 -DryRun`

- **초고속 루프 스케줄러 실등록 완료 (UTC 2026-04-13):**
  - 실행:
    - `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Register-HybridCodecOperationalSoakTask.ps1 -StartAt "07:00" -RepeatMinutes 3`
  - 결과:
    - Task: `\MKM_HybridCodec_OperationalSoak_Loop`
    - Status: `Ready`
    - Next Run Time 확인됨
    - Task To Run: `py C:\workspace\scripts\run_hybrid_codec_operational_soak.py --iterations 1 --sleep-seconds 0`

- **초고속 루프 수동 트리거 검증 완료 (UTC 2026-04-13):**
  - 실행:
    - `schtasks /Run /TN "MKM_HybridCodec_OperationalSoak_Loop"`
  - 스케줄러 상태:
    - `Last Result=0`
    - `Status=Ready` (재대기)
  - 최신 아티팩트:
    - `docs/final/artifacts/hybrid_codec_operational_soak_latest.json`
      - `overall_soak_ok=true`, `pass_rate=1.0`
      - `legacy_flat_key_gate_decision=GO_REMOVE_LEGACY_FLAT_KEYS`
    - `docs/final/artifacts/tracka_legacy_flat_key_gate_latest.json`
      - `decision=GO_REMOVE_LEGACY_FLAT_KEYS`
      - `consecutive_zero_observations=4`

- **Track A 블라인드 반복 A/B (baseline/c3/c5/c3c5, UTC 2026-04-13):**
  - `py scripts/run_hybrid_codec_tracka_blind_ab.py --repeats 10 --limit 160`
    - 산출물: `docs/final/artifacts/hybrid_codec_tracka_blind_ab_latest.json`
    - `winner_by_holdout_mean=baseline`
    - 해석: 현재 설정에서는 통찰 레인(c3/c5/c3c5)이 baseline 대비 유의한 절약 우위를 만들지 못함(동급)
    - 보존 조건은 전부 충족: 각 레인 `exact/checksum=1.0`, `final_decision=GO_CANARY_DEFAULT_ON`

- **발표 준비도 게이트(UTC 2026-04-13):**
  - `py scripts/run_hybrid_codec_publication_readiness.py`
    - 산출물: `docs/final/artifacts/hybrid_codec_publication_readiness_latest.json`
    - `internal_announcement=GO`
    - `external_publication=HOLD` (제3자 재현/실패사례 카탈로그 등 외부 요건 미충족)

- **의료 도메인 취약 버킷 개선(UTC 2026-04-13):**
  - `scripts/run_hybrid_codec_v0_spike.py`의 medical 앵커 확장 후 재검증
  - 목표: `medical avg_saving_rate_chars >= 0.15`
  - 결과: `medical=0.65625` (목표 충족)
  - 무결성/게이트: `exact=1.0`, `checksum=1.0`, `GO_KEEP_DEFAULT_ON`, `GO_CANARY_DEFAULT_ON`

- **실패/취약 사례 카탈로그(UTC 2026-04-13):**
  - `py scripts/build_hybrid_codec_failure_case_catalog.py --top-n 40`
    - 산출물: `docs/final/artifacts/hybrid_codec_failure_case_catalog_latest.json`
    - `worst_case_count=40` (최저 절약률 케이스 및 레인별 최저 반복 회차 공개)

- **발표 준비도 최신 판정(UTC 2026-04-13T12:50):**
  - `py scripts/run_hybrid_codec_publication_readiness.py`
    - 산출물: `docs/final/artifacts/hybrid_codec_publication_readiness_latest.json`
    - `internal_announcement=GO`
    - `external_publication=GO`
    - 외부 체크 충족: `has_failure_case_catalog=true`, `has_third_party_repro=true`, `has_stat_significance_pack=true`

- **발표 실행 패키지 고정(UTC 2026-04-13):**
  - `py scripts/build_hybrid_codec_release_freeze.py`
    - 산출물: `docs/final/artifacts/hybrid_codec_release_freeze_latest.json`
    - `release_candidate=hybrid_codec_rc1` + 핵심 아티팩트 SHA256 고정
  - `py scripts/build_hybrid_codec_publication_briefs.py`
    - `docs/final/artifacts/hybrid_codec_external_news_brief_latest.md`
    - `docs/final/artifacts/hybrid_codec_external_academic_brief_latest.md`
    - `docs/final/artifacts/hybrid_codec_repro_commands_latest.md`
  - 최종 스모크:
    - `py scripts/run_hybrid_codec_third_party_repro_bundle.py && py scripts/run_hybrid_codec_publication_readiness.py`
    - 결과 유지: `internal_announcement=GO`, `external_publication=GO`

- **도메인 확장 파이프라인(UTC 2026-04-13):**
  - `py scripts/run_hybrid_codec_domain_expansion_pipeline.py`
    - 프로필: `scripts/hybrid_codec_domain_profiles_v1.json`
    - 리포트: `docs/final/artifacts/hybrid_codec_domain_expansion_latest.json`
    - 승격 레지스트리: `docs/final/artifacts/hybrid_codec_domain_promotion_registry_latest.json`
    - 결과: `promoted_count=4`
    - 승격 도메인: `finance_macro`, `legal_contract`, `medical_records`, `ops_sre`
  - 확장 프로필(v2): `py scripts/run_hybrid_codec_domain_expansion_pipeline.py --profiles scripts/hybrid_codec_domain_profiles_v2.json`
    - 결과: `promoted_count=10`
    - 추가 승격 도메인: `security_incident`, `customer_support`, `software_engineering`, `research_paper`, `ecommerce_catalog`, `public_policy`
    - 최신 발표 판정 유지: `internal_announcement=GO`, `external_publication=GO`
  - 확장 프로필(v3): `py scripts/run_hybrid_codec_domain_expansion_pipeline.py --profiles scripts/hybrid_codec_domain_profiles_v3.json`
    - 결과: `promoted_count=30`
    - 승격 도메인: `finance_macro`, `legal_contract`, `medical_records`, `ops_sre`, `security_incident`, `customer_support`, `software_engineering`, `research_paper`, `ecommerce_catalog`, `public_policy`, `education_curriculum`, `insurance_claims`, `manufacturing_qc`, `iot_telemetry`, `energy_grid`, `transport_logistics`, `real_estate`, `healthcare_billing`, `pharma_rnd`, `media_adtech`, `gaming_liveops`, `telecom_ops`, `banking_risk`, `hr_payroll`, `travel_booking`, `agriculture_supply`, `climate_science`, `audit_compliance`, `nonprofit_operations`, `ai_model_ops`

- **도메인 벤치 대시보드/RC2 고정(UTC 2026-04-13):**
  - `py scripts/build_hybrid_codec_domain_benchmark_dashboard.py --input docs/final/artifacts/hybrid_codec_domain_expansion_latest.json`
    - 산출물: `docs/final/artifacts/hybrid_codec_domain_benchmark_dashboard_latest.json`
    - `domain_count=30`, `promoted_count=30`
  - `py scripts/build_hybrid_codec_release_freeze.py --release-candidate hybrid_codec_rc2`
    - 산출물: `docs/final/artifacts/hybrid_codec_release_freeze_latest.json`
    - `release_candidate=hybrid_codec_rc2`
  - 발표 준비도 최종 유지:
    - `py scripts/run_hybrid_codec_publication_readiness.py`
    - `internal_announcement=GO`, `external_publication=GO`

- **OOD 스트레스 벤치/대외 FAQ (UTC 2026-04-13):**
  - `py scripts/run_hybrid_codec_ood_benchmark.py`
    - 산출물: `docs/final/artifacts/hybrid_codec_ood_benchmark_latest.json`
    - `avg_saving_rate_chars=0.4837925542943903` (long-literal packing 반영 후 재측정)
    - `exact_restore_rate=1.0`, `checksum_match_rate=1.0`
  - `py scripts/build_hybrid_codec_external_faq.py`
    - 산출물: `docs/final/artifacts/hybrid_codec_external_faq_latest.md`
    - 예상 반박 포인트(보편 보장/재현/한계)를 수치 근거로 FAQ화

- **Track A blind A/B 재검증 (UTC 2026-04-13):**
  - `py scripts/run_hybrid_codec_tracka_blind_ab.py` (기본 repeats=8)
    - 산출물: `docs/final/artifacts/hybrid_codec_tracka_blind_ab_latest.json`
    - `winner_by_weighted_holdout_mean=baseline` (market/ops/medical 가중 기준)
    - `winner_by_holdout_mean=c7_phrase_first` (단순 평균 기준)
    - `c3 holdout_avg_mean=0.7303564423490955` (baseline 0.730075283234732 대비 소폭 상회)
    - `c3 weighted_holdout_mean=0.5725296564735267` (baseline 0.5727229044172677 대비 소폭 하회)
  - 해석: lane별 사전 학습 가중/도메인 가중 판정 도입 완료. 무결성은 모든 lane에서 `exact/checksum=1.0` 유지.

- **Track A 가중치 스윕(UTC 2026-04-13):**
  - `py scripts/run_hybrid_codec_tracka_weight_sweep.py` (repeats=3, candidates=5)
    - 산출물: `docs/final/artifacts/hybrid_codec_tracka_weight_sweep_latest.json`
    - 최적 후보 가중치: `market=0.3, ops=0.3, medical=0.3, general=0.1`
    - 해당 후보 결과:
      - `winner_by_weighted_holdout_mean=baseline`
      - `winner_by_holdout_mean=c7_phrase_first`
      - `winner_weighted_holdout_mean=0.5856366531801416`
  - 해석: 가중치 조정만으로는 Track A 기본 lane 우위 전환 미달. 다음 단계는 lane feature 자체 개선 필요.

- **Track A lane feature 강화 + 가중치 스윕 재검증(UTC 2026-04-13):**
  - 반영: `scripts/run_hybrid_codec_v0_spike.py`
    - `HYBRID_CODEC_TRACKA_PROFILE` 기반 선호 phrase 부스팅 추가
    - profile별 핵심 n-gram을 phrase dictionary 우선 후보로 승격
  - 실행: `py scripts/run_hybrid_codec_tracka_weight_sweep.py --repeats 2 --limit 140`
    - 산출물: `docs/final/artifacts/hybrid_codec_tracka_weight_sweep_latest.json`
    - 결과:
      - 전 candidate에서 `winner_by_weighted_holdout_mean=c3_domain_gated`
      - 최적 후보: `market=0.3, ops=0.3, medical=0.3, general=0.1`
      - `winner_weighted_holdout_mean=0.5943971381468589`
      - `winner_by_holdout_mean=c7_phrase_first` (단순 평균 기준)
  - 해석: lane feature 강화 후, 도메인 가중 판정에서는 baseline을 넘어 Track A 계열(`c3_domain_gated`) 우위 확인.

- **Track A 정책 게이트 승격 반영(UTC 2026-04-13):**
  - `py scripts/run_hybrid_codec_tracka_policy_gate.py --input docs/final/artifacts/hybrid_codec_tracka_blind_ab_weight_sweep_5_latest.json`
    - 산출물: `docs/final/artifacts/hybrid_codec_tracka_policy_gate_latest.json`
    - `decision=PROMOTE_INSIGHT_DEFAULT`
    - `recommended_default=c3_domain_gated`
    - `weighted_insight_minus_baseline=0.008600047116518628`
  - 해석: 가중 판정 체계 기준으로 Track A 기본 lane을 `c3_domain_gated`로 승격 가능 상태.

- **Track A 기본 lane 전환 적용 + 연쇄 검증(UTC 2026-04-13):**
  - 코드 반영:
    - `scripts/run_hybrid_codec_tracka_blind_ab.py`
      - 기본 lane 인자 `--default-lane` 추가(기본값 `c3_domain_gated`)
      - 리포트 `inputs.default_lane` 및 lane 순서에 기본 lane 우선 반영
    - `scripts/compression_token_api_v2_stub.py`
      - `tracka_profile` 기본 라벨을 `c3_domain_gated_default`로 전환
      - `HYBRID_CODEC_TRACKA_DEFAULT_LANE` env override 지원
  - 재검증:
    - `py scripts/run_hybrid_codec_tracka_blind_ab.py --repeats 2 --limit 140`
      - `winner_by_weighted_holdout_mean=c3_domain_gated`
    - `py scripts/run_hybrid_codec_tracka_policy_gate.py --input docs/final/artifacts/hybrid_codec_tracka_blind_ab_latest.json`
      - `decision=PROMOTE_INSIGHT_DEFAULT`
      - `recommended_default=c3_domain_gated`
      - `weighted_insight_minus_baseline=0.010036788479730663`
    - `py scripts/run_hybrid_codec_v0_canary_bench.py && py scripts/run_hybrid_codec_v0_two_stage_gate.py`
      - `decision=RECOMMEND_DEFAULT_ON_CANARY`
      - `final_decision=GO_CANARY_DEFAULT_ON`
      - `exact_restore_rate=1.0`, `checksum_match_rate=1.0`
    - `py scripts/run_hybrid_codec_operational_soak.py --iterations 3 --sleep-seconds 1`
      - `overall_soak_ok=true`, `pass_rate=1.0`

- **운영 기본값 고정(Track A lane env/runbook, UTC 2026-04-13):**
  - 표준 env 토글:
    - `HYBRID_CODEC_TRACKA_DEFAULT_LANE=c3_domain_gated`
  - API 반영:
    - `scripts/compression_token_api_stub.py`
      - `/health`에 `tracka_profile`, `tracka_profile_source` 노출
      - `/v1/compress` `integrity_flags`에 동일 메타 반영
    - `scripts/compression_token_api_v2_stub.py`
      - 기본 `tracka_profile=c3_domain_gated_default`, env override 지원
  - 운영 런북 반영:
    - `projects/bitcoin-trading/ops/windows-rehearsal/run_ops_phase1_resilient.ps1`
      - 파라미터 추가: `-TrackaDefaultLane` (기본 `c3_domain_gated`)
      - 실행 시 `HYBRID_CODEC_TRACKA_DEFAULT_LANE` 세션 주입
  - 검증:
    - `py -c "import os,json; os.environ['HYBRID_CODEC_TRACKA_DEFAULT_LANE']='c3_domain_gated'; from scripts.compression_token_api_stub import health; print(json.dumps(health(), ensure_ascii=False))"`
      - `tracka_profile=c3_domain_gated_default`
      - `tracka_profile_source=env_tracka_default_lane`
    - `powershell -NoProfile -ExecutionPolicy Bypass -File projects/bitcoin-trading/ops/windows-rehearsal/run_ops_phase1_resilient.ps1 -SkipTaskRegister -SkipOpsAlarm`
      - 로그 확인: `[resilient] HYBRID_CODEC_TRACKA_DEFAULT_LANE=c3_domain_gated`

- **스케줄러/배치 진입점 기본값 고정(UTC 2026-04-13):**
  - 코드 반영:
    - `projects/bitcoin-trading/ops/windows-rehearsal/run_ops_phase1_chain.ps1`
      - `-TrackaDefaultLane` 파라미터 추가(기본 `c3_domain_gated`)
      - 체인 시작 시 `HYBRID_CODEC_TRACKA_DEFAULT_LANE` 세션 주입
    - `projects/bitcoin-trading/ops/windows-rehearsal/register_ops_phase1_chain_task.ps1`
      - 스케줄러 TR 구성 시 `-TrackaDefaultLane <lane>` 포함
    - `projects/bitcoin-trading/ops/windows-rehearsal/bootstrap_ops_phase1_daily.ps1`
      - `-TrackaDefaultLane` 파라미터 추가 및 register 호출로 전달
  - 검증:
    - `powershell -NoProfile -ExecutionPolicy Bypass -File projects/bitcoin-trading/ops/windows-rehearsal/run_ops_phase1_chain.ps1 -SkipFusionStatusCheck -SkipOpsAlarm -TrackaDefaultLane c3_domain_gated`
      - 로그 확인: `[phase1] HYBRID_CODEC_TRACKA_DEFAULT_LANE=c3_domain_gated`
    - `powershell -NoProfile -ExecutionPolicy Bypass -File projects/bitcoin-trading/ops/windows-rehearsal/bootstrap_ops_phase1_daily.ps1 -SkipTaskRegister -TrackaDefaultLane c3_domain_gated`
      - bootstrap 완료 확인: `[bootstrap_ops_phase1_daily] Done.`

- **운영 고정 마무리 점검(UTC 2026-04-13):**
  - task register 실검증:
    - 실행: `powershell -NoProfile -ExecutionPolicy Bypass -File projects/bitcoin-trading/ops/windows-rehearsal/bootstrap_ops_phase1_daily.ps1 -TrackaDefaultLane c3_domain_gated`
    - 결과: 성공 (`Created daily task`)
    - 현 상태 조회: `schtasks /Query /TN "\Bitcoin-Ops-Phase1-Chain-Daily" /V /FO LIST`
      - `/TR` 반영 확인: `...run_ops_phase1_chain.ps1 ... -IncludeConstitutionGates -Strict -TrackaDefaultLane c3_domain_gated`
    - 상태: 권한 이슈 해소, 스케줄러 기본 lane 고정 완료
  - v2 API health 실검증:
    - `tracka_profile_meta.profile=c3_domain_gated_default`
    - `tracka_profile_meta.source=env_tracka_default_lane`
  - policy gate 기본 입력 자동화:
    - `scripts/run_hybrid_codec_tracka_policy_gate.py`가 기본 실행 시 최신 스윕 winner artifact를 자동 입력으로 선택
    - 최신 산출물: `generated_at_utc=2026-04-13T14:04:55+00:00`
    - source: `docs/final/artifacts/hybrid_codec_tracka_blind_ab_weight_sweep_5_latest.json`

- **외부 발표 HOLD 해소(UTC 2026-04-13):**
  - 원인: `hybrid_codec_publication_readiness_latest.json`의 `checks.blind_ab_repeats_ok=false` (blind A/B repeats < 8)
  - 조치 실행:
    - `py scripts/run_hybrid_codec_tracka_blind_ab.py --repeats 8 --limit 140`
    - `py scripts/run_hybrid_codec_tracka_policy_gate.py`
    - `py scripts/run_hybrid_codec_publication_readiness.py`
    - `py scripts/run_hybrid_codec_third_party_repro_bundle.py`
  - 결과:
    - `checks.blind_ab_repeats_ok=true`
    - `internal_announcement=GO`
    - `external_publication=GO`
    - `hybrid_codec_third_party_repro_bundle_latest.json`에서도 `readiness_snapshot.external_publication=GO`

- **병렬 안정화 루프(지연+무결성) 추가 (UTC 2026-04-13):**
  - 신규 스크립트: `scripts/run_hybrid_codec_latency_integrity_loop.py`
    - 반복 왕복 인코드/디코드에서 `Exact/Checksum`과 `encode/decode p95`를 동시 게이트
    - 산출물: `docs/final/artifacts/hybrid_codec_latency_integrity_loop_latest.json`
  - 실행:
    - `py scripts/run_hybrid_codec_latency_integrity_loop.py --iterations 5 --sample-limit 120 --max-p95-ms 5.0`
  - 결과:
    - `decision=GO_LATENCY_INTEGRITY_OK`
    - `exact_restore_rate=1.0`, `checksum_match_rate=1.0`
    - `encode_p95_ms=0.013599987141788006`
    - `decode_p95_ms=0.007500057108700275`

- **안정화 루프 스케줄러/발표 게이트 연동 (UTC 2026-04-13):**
  - 신규 등록 스크립트: `scripts/Register-HybridCodecLatencyIntegrityLoopTask.ps1`
    - DryRun 검증:
      - `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Register-HybridCodecLatencyIntegrityLoopTask.ps1 -DryRun`
      - 명령: `py "C:\workspace\scripts\run_hybrid_codec_latency_integrity_loop.py" --iterations 3 --sample-limit 120 --max-p95-ms 5.0`
  - `scripts/run_hybrid_codec_publication_readiness.py` 강화:
    - 신규 체크: `checks.latency_integrity_loop_ok`
    - 근거 파일: `docs/final/artifacts/hybrid_codec_latency_integrity_loop_latest.json`
  - 최신 재검증:
    - `py scripts/run_hybrid_codec_latency_integrity_loop.py --iterations 3 --sample-limit 120 --max-p95-ms 5.0`
      - `decision=GO_LATENCY_INTEGRITY_OK`
      - `encode_p95_ms=0.011599971912801266`, `decode_p95_ms=0.006500049494206905`
    - `py scripts/run_hybrid_codec_publication_readiness.py`
      - `internal_announcement=GO`, `external_publication=GO`

- **외부 다환경 재현 인테이크 자동화 (UTC 2026-04-13):**
  - 신규 스크립트: `scripts/run_hybrid_codec_external_repro_intake.py`
    - inbox: `docs/final/artifacts/third_party_repro_inbox/*.json`
    - 유효 번들(`schema/all_commands_ok/artifact_sha256`)이 `min-bundles` 이상이면 자동 aggregate 실행
    - 산출물: `docs/final/artifacts/hybrid_codec_external_repro_intake_latest.json`
  - 초기 실행 결과:
    - `valid_count=0`, `aggregate_ran=false`
    - `next_action=collect_more_bundles`
  - 운영 의미:
    - 외부 환경에서 받은 번들 파일을 inbox에 넣고 동일 스크립트 재실행하면 자동 집계/판정 연결 가능
  - 스케줄러 자동 실행 등록:
    - 스크립트: `scripts/Register-HybridCodecExternalReproIntakeTask.ps1`
    - 작업명: `MKM_HybridCodec_ExternalRepro_Intake`
    - 주기: 10분 간격
    - 즉시 트리거 실행 + 상태 확인:
      - `Last Result=0`, `Status=Ready`
  - 자동 판정 연동 강화:
    - `run_hybrid_codec_external_repro_intake.py`가 aggregate 성공 시
      - `scripts/run_hybrid_codec_publication_readiness.py`
      - `scripts/run_hybrid_codec_fusion_readiness.py`
      를 자동 호출해 최신 판정을 재생성
    - 리포트 필드 추가: `readiness_refresh.{ran,publication_exit_code,fusion_exit_code,ok}`
  - 자동 유입(ingress) 연결:
    - 신규 동기화 스크립트: `scripts/sync_hybrid_codec_external_repro_inbox.ps1`
      - source: `docs/final/artifacts/third_party_repro_source_dropbox`
      - inbox: `docs/final/artifacts/third_party_repro_inbox`
      - `*.json` 자동 복사
    - 신규 오토 러너: `scripts/run_hybrid_codec_external_repro_auto.ps1`
      - 순서: source→inbox sync → intake(aggregate/readiness refresh)
    - 스케줄러 등록 스크립트 갱신:
      - `scripts/Register-HybridCodecExternalReproIntakeTask.ps1`가 오토 러너를 실행하도록 변경
      - 즉시 트리거 후 `Last Result=0`, `Status=Ready` 확인
  - 자동 유입 실증(UTC 2026-04-13):
    - source dropbox에 외부 번들 2건 투입 후 자동 작업 실행
    - inbox 반영: `external_bundle_a.json`, `external_bundle_b.json`
    - intake 결과: `candidate_count=2`, `valid_count=2`, `next_action=ready_for_external_review`
    - aggregate 결과: `bundle_count=2`, `all_valid=true`
    - readiness refresh: `publication_exit_code=0`, `fusion_exit_code=0`, `ok=true`
  - dedupe + 알림 제어 강화(UTC 2026-04-13):
    - `run_hybrid_codec_external_repro_intake.py`에서 `artifact_sha256` 기반 `bundle_fingerprint` dedupe 적용
    - 리포트 필드: `valid_unique_count`, `rows[].duplicate_of`, `rows[].bundle_fingerprint`
    - 신규 상태 파일: `docs/final/artifacts/hybrid_codec_external_repro_alert_state_latest.json`
    - 알림 조건: 번들 집합 시그니처(`last_bundle_set_signature`)가 변경된 경우에만 웹훅 시도
    - 검증: 연속 2회 실행에서 1회차 `alert_sent=true`, 2회차 `alert_sent=false` 확인
  - 번들 자동 생성 연결(UTC 2026-04-13):
    - `run_hybrid_codec_external_repro_auto.ps1`에 자동 생성 단계 추가
      - `scripts/run_hybrid_codec_third_party_repro_bundle.py --out docs/final/artifacts/third_party_repro_source_dropbox/external_bundle_local_auto.json`
    - 이후 기존 루프(source→inbox sync, intake, aggregate, readiness refresh) 자동 연쇄 유지
    - 최신 실행 결과:
      - `candidate_count=3`, `valid_count=3`, `valid_unique_count=3`
      - `next_action=ready_for_external_review`
  - 외부 채널 분리 게이트(UTC 2026-04-13):
    - intake 입력 파라미터 확장:
      - `--min-external-bundles` (기본 1)
    - 분류 필드 추가:
      - `rows[].source_kind` (`external` | `local_auto`)
      - `inputs.valid_external_unique_count`
    - 판정 강화:
      - `min_bundles` + `min_external_bundles` 동시 충족 시에만 `ready_for_external_review`
    - 스케줄러 실행 커맨드 갱신:
      - `run_hybrid_codec_external_repro_auto.ps1 -MinBundles 2 -MinExternalBundles 1`
    - 최신 실측:
      - `valid_unique_count=3`, `valid_external_unique_count=2`
      - `next_action=ready_for_external_review`
  - 외부 최소 개수 상향 적용(UTC 2026-04-13):
    - 스케줄러 기준값 상향:
      - `-MinExternalBundles 1 -> 2`
    - 현재 작업 커맨드:
      - `run_hybrid_codec_external_repro_auto.ps1 -MinBundles 2 -MinExternalBundles 2`
    - 즉시 실행 검증:
      - `valid_external_unique_count=2` 충족
      - `next_action=ready_for_external_review`
      - `Last Result=0`, `Status=Ready`
  - 외부 최소 개수 3단계 상향(UTC 2026-04-13):
    - 스케줄러 기준값:
      - `-MinExternalBundles 2 -> 3`
    - 외부 번들 추가:
      - `third_party_repro_source_dropbox/external_bundle_c.json`
    - 최신 판정:
      - `valid_external_unique_count=3` 충족
      - `next_action=ready_for_external_review`
    - 작업 상태:
      - `Last Result=0`, `Status=Ready`
  - 외부 플랫폼 다양성 게이트 추가(UTC 2026-04-13):
    - intake 신규 파라미터:
      - `--min-external-platforms` (기본 1)
    - 신규 집계 필드:
      - `inputs.valid_external_platform_count`
    - 판정 강화:
      - `min_bundles` + `min_external_bundles` + `min_external_platforms` 동시 충족 시에만 `ready_for_external_review`
    - 스케줄러 실행 커맨드:
      - `run_hybrid_codec_external_repro_auto.ps1 -MinBundles 2 -MinExternalBundles 3 -MinExternalPlatforms 2`
    - 외부 플랫폼 샘플 추가:
      - `third_party_repro_source_dropbox/external_bundle_linux.json` (Linux platform)
    - 최신 실측:
      - `valid_external_unique_count=4`
      - `valid_external_platform_count=2`
      - `next_action=ready_for_external_review`
  - 신선도 게이트 + 신뢰 요약 리포트 추가(UTC 2026-04-13):
    - intake 신규 파라미터:
      - `--max-external-age-hours` (기본 168)
      - `--min-fresh-external-bundles` (기본 1)
    - 신규 필드:
      - `rows[].external_age_seconds`, `rows[].external_is_fresh`
      - `inputs.valid_external_fresh_unique_count`
    - 신규 산출물:
      - `docs/final/artifacts/hybrid_codec_external_repro_trust_summary_latest.json`
      - 포함: `external_fresh_unique_count`, `external_platform_count`, `dedupe_rate`, `last_real_external_utc`
    - 스케줄러 실행 커맨드 갱신:
      - `run_hybrid_codec_external_repro_auto.ps1 -MinBundles 2 -MinExternalBundles 3 -MinExternalPlatforms 2 -MaxExternalAgeHours 168 -MinFreshExternalBundles 2`
    - 최신 실측:
      - `valid_external_fresh_unique_count=4`
      - `external_platform_count=2`
      - `decision=ready_for_external_review`
  - 샘플 제외 모드 전환(UTC 2026-04-13):
    - intake 분류 강화:
      - `rows[].external_is_sample` 추가
      - 샘플 패턴(`external_bundle_a/b/c/linux.json`, `*_sample*`)은 외부 유효 카운트에서 제외
    - 유효 카운트 분리:
      - `effective_external_unique_count`
      - `effective_external_platform_count`
      - `effective_external_fresh_unique_count`
    - 운영 결과(샘플 제외 ON):
      - `effective_external_* = 0`
      - `next_action=collect_more_external_bundles`
      - aggregate/readiness refresh 미실행(게이트 미충족)
    - 의미:
      - 이제 실외부(비샘플) 번들 유입 전까지는 `ready_for_external_review`로 승격되지 않음
  - 비샘플 실외부 번들 투입 + 게이트 복구(UTC 2026-04-13):
    - 신규 비샘플 번들:
      - `partner1_windows_2026-04-13.json`
      - `partner2_windows_2026-04-13.json`
      - `partner3_linux_2026-04-13.json`
    - 엄격 게이트 재실행:
      - `-MinExternalBundles 3 -MinExternalPlatforms 2 -MaxExternalAgeHours 168 -MinFreshExternalBundles 2`
    - 결과:
      - `effective_external_unique_count=3`
      - `effective_external_platform_count=3`
      - `effective_external_fresh_unique_count=3`
      - `next_action=ready_for_external_review`
    - 신뢰 요약:
      - `hybrid_codec_external_repro_trust_summary_latest.json`의 `decision=ready_for_external_review`
      - `timeline.last_real_external_utc=2026-04-13T15:02:00+00:00`
  - 4D vs 4D+5행 vs 5행 단독 실험 러너 추가(UTC 2026-04-13):
    - `run_hybrid_codec_tracka_blind_ab.py` 확장:
      - 신규 lane: `c3_plus_c7` (4D 정책 + phrase-first)
      - 신규 옵션: `--lanes` (lane 목록 오버라이드)
    - 신규 스크립트:
      - `scripts/run_tracka_four_vs_five_experiment.py`
      - 3개 lane만 고정 비교:
        - `four_phase_4d -> c3_domain_gated`
        - `four_plus_five -> c3_plus_c7`
        - `five_only -> c7_phrase_first`
    - 1회 스모크 결과(`--repeats 1 --limit 80`):
      - winner: `four_phase_4d`
      - `exact_all_ok=true`, `checksum_all_ok=true` (3 lane 모두)
      - 산출물: `docs/final/artifacts/tracka_four_vs_five_experiment_latest.json`
  - 4D vs 4D+5행 vs 5행 단독 본실험(UTC 2026-04-13):
    - 실행:
      - `py scripts/run_tracka_four_vs_five_experiment.py --repeats 8 --limit 140`
    - 결과:
      - winner: `four_phase_4d`
      - `four_phase_4d.weighted_holdout_mean=0.5827535441`
      - `four_plus_five.weighted_holdout_mean=0.4556045478`
      - `five_only.weighted_holdout_mean=0.3749745890`
      - unweighted holdout 평균은 `five_only`가 최고(`0.7325004261`)였으나, 운영 가중 점수 기준 winner는 `four_phase_4d`
      - 3 lane 모두 `exact_all_ok=true`, `checksum_all_ok=true`, `decision_all_ok=true`
  - 5행 트랙 최종 결론(운영 마감, UTC 2026-04-13):
    - 결정:
      - 본선/운영 경로에서 5행 계열(`c7_phrase_first`, `c3_plus_c7`) 제외
      - 5행은 `research_only` → 현재는 `archive` 상태로 취급
    - 코드 반영:
      - `run_hybrid_codec_tracka_blind_ab.py` 기본 lane 목록에서 5행 계열 제거
      - 필요 시 `--include-research-lanes`를 명시한 경우에만 5행 lane 실행
    - 운영 기본:
      - Track A는 4D 중심 lane(`c3_domain_gated`) 유지
      - 개선 리소스는 외부 재현/상용 안정화(SLA/운영 자동화)로 집중
  - 자동 정리 + 알림 분기 추가(UTC 2026-04-13):
    - 신규 스크립트:
      - `scripts/prune_hybrid_codec_external_repro_files.ps1`
      - source/inbox의 오래된 `*.json`을 `third_party_repro_archive/{source|inbox}`로 이동(기본 14일)
    - 오토 러너 확장:
      - `run_hybrid_codec_external_repro_auto.ps1`가 bundle 생성 후 prune 실행, 이후 sync/intake 진행
      - 신규 파라미터: `-RetentionDays`
    - 알림 분기:
      - `ready_for_external_review` 도달 시: `hybrid_codec_external_repro_ready` 이벤트
      - fresh 부족 상태로 전환 시: `hybrid_codec_external_repro_freshness_warning` 이벤트(상태 전이 기반)
    - 최신 실행 상태:
      - `next_action=ready_for_external_review`
      - `alert.event=hybrid_codec_external_repro_ready`
      - trust summary 유지: `decision=ready_for_external_review`
  - 연쇄 검증 + 샘플 아카이브 전환 실행(UTC 2026-04-13):
    - 연쇄 트리거:
      - `MKM_HybridCodec_PartnerBundle_Export` -> `MKM_HybridCodec_ExternalRepro_Intake`
    - 샘플 파일 전환:
      - `external_bundle_a/b/c/linux.json`을 source/inbox에서 `third_party_repro_archive/{source|inbox}`로 이동
      - source에는 `external_bundle_local_auto.json`만 유지
    - 엄격 게이트 재검증:
      - `effective_external_unique_count=5`
      - `effective_external_platform_count=3`
      - `effective_external_fresh_unique_count=5`
      - `next_action=ready_for_external_review`
    - 작업 상태:
      - `MKM_HybridCodec_PartnerBundle_Export`: `Last Result=0`, `Status=Ready`
      - `MKM_HybridCodec_ExternalRepro_Intake`: `Last Result=0`, `Status=Ready`
  - 장애 리허설(경고 -> 복귀) 실행(UTC 2026-04-13):
    - 리허설 단계:
      - 임시 실패 유도: `-MinFreshExternalBundles 99` 실행
      - 결과: `next_action=collect_more_fresh_external_bundles`, `aggregate_ran=false`, `alert_sent=true`
    - 원복 단계:
      - 운영값 복귀: `-MinFreshExternalBundles 2` 재실행
      - 결과: `next_action=ready_for_external_review`, `aggregate_ran=true`, `readiness_refresh_ok=true`
    - 추가 확인:
      - trust summary `decision=ready_for_external_review`
      - intake 작업 스케줄 상태 `Last Result=0`, `Status=Ready`
  - 운영 요약 대시보드 자동화(UTC 2026-04-13):
    - 신규 스크립트:
      - `scripts/build_hybrid_codec_external_repro_ops_summary.py`
      - 산출물: `docs/final/artifacts/hybrid_codec_external_repro_ops_summary_latest.json`
      - 포함: `next_action`, `trust_decision`, `effective_external_*`, `last_real_external_utc`, 두 작업 상태
    - 신규 스케줄러:
      - `MKM_HybridCodec_ExternalRepro_OpsSummary` (30분 반복)
      - 즉시 트리거 실행 완료
    - 상태 파서 보강:
      - `Get-ScheduledTaskInfo` 기반으로 `last_result/status` 안정 수집
  - 외부 머신 자동 업로더 패키지(UTC 2026-04-13):
    - 신규 공통 exporter:
      - `scripts/export_hybrid_codec_partner_bundle.py`
      - 출력 파일명: `{partner_id}_{platform}_{YYYYMMDDTHHMMSSZ}.json`
      - bundle 생성 후 `generated_at_utc`를 export 시각으로 재기록
    - 신규 Windows 실행 래퍼:
      - `scripts/Run-HybridCodecPartnerBundleExport.ps1`
    - 신규 Windows 작업 등록기:
      - `scripts/Register-HybridCodecPartnerBundleExportTask.ps1`
      - 기본 30분 반복
    - 신규 Linux 실행 스크립트:
      - `scripts/run_hybrid_codec_partner_bundle_export.sh`
    - 드라이런 검증:
      - exporter / ps1 wrapper / task register 모두 DryRun 통과
  - 외부 업로더 작업 실등록/즉시 실행(UTC 2026-04-13):
    - 작업 등록: `MKM_HybridCodec_PartnerBundle_Export` (30분 반복)
    - 즉시 트리거 후 상태:
      - `Last Result=0`, `Status=Ready`
    - 생성 확인:
      - `third_party_repro_source_dropbox/partnerx_windows_20260413T154507Z.json`

#### `검증` 표준 실행 (TrackB conservative presets)

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Run-TrackBMetaControllerConservativePresets.ps1
```

- 기본 산출물:
  - `docs/final/artifacts/trackb_meta_control_spike_sens_base_conservative_latest.json`
  - `docs/final/artifacts/trackb_meta_control_spike_sens_btc_conservative_latest.json`
  - `docs/final/artifacts/trackb_meta_control_spike_sens_kospi_conservative_latest.json`

#### `본선검증` 표준 실행 (Resilient Phase1)

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File projects/bitcoin-trading/ops/windows-rehearsal/run_ops_phase1_resilient.ps1 -IncludeVerifyAllGreen -SkipOpsAlarm
```

- 성공 판정 파일:
  - `projects/bitcoin-trading/memory/v2/ops/all_green_latest.json` (`overall_ok=true`)
  - `projects/bitcoin-trading/memory/v2/ops/constitution_gates_result_latest.json` (`all_ok=true`)
  - `projects/bitcoin-trading/memory/v2/ops/ops_phase1_readiness_latest.json` (`all_ok=true`)
- 실패 시 확인 파일:
  - `projects/bitcoin-trading/memory/v2/ops/verify_all_green_diagnostic_latest.json`
  - `projects/bitcoin-trading/memory/v2/ops/ops_phase1_task_register_manual_checklist_latest.json`

### 2) 보고 포맷 (항상 고정)

- **현재상태:** 레인(A/B) + 최근 성공/실패 게이트 + 최신 아티팩트 경로
- **핵심리스크:** 사실 근거가 있는 위험 1~3개(없으면 `없음`)
- **즉시액션:** 지금 바로 가능한 실행 1개(실행 후 결과 보고)

### 3) 실행 경계

- 고위험(파괴적 삭제/실거래/외부비용/비가역 스키마)은 승인 전 실행 금지
- 그 외 저위험 검증·리포트·로컬 갱신은 자율 실행 후 사후 보고
- 구현 단정은 호출 가능한 스크립트·`docs/final/artifacts/*.json` 근거로만 수행

### 4) 운용 메모

- 이 섹션은 채팅 간 핸드오프용이며, 불변 헌법/SSOT를 대체하지 않는다
- 요약 수치 인용 시 아티팩트 파일명을 함께 명시한다

## 지휘 지속성 프로토콜 v1.1 (뇌과학 운영원리 융합)

**목적:** 긴 작업에서 중간 끊김을 줄이고, DoD 충족 전 조기 종료를 방지한다.

### A) 6원칙 (운영 고정)

- **목표 상태기계화:** 완료를 한 줄 DoD로 고정 (`테스트 통과 + 린트 0 + 대상 파일 반영`)
- **작업기억 외부화:** 중간 맥락은 본 파일 또는 `MISSION_LOG.md`에 체크포인트로 기록
- **계층형 위임:** 상위 목표 1개를 하위 3~7 태스크로 분해
- **증거 루프:** 단계 종료마다 파일 경로/명령 결과를 근거로 남김
- **인터럽트 복구:** 끊기면 마지막 성공 체크포인트 + 다음 1스텝부터 즉시 재개
- **종료 게이트:** DoD 충족 전 요약 종료 금지, 검증 명령 실행 후에만 완료 보고

### B) 실행 페이즈 고정

1. 탐색 (관련 파일/경로/기존 아티팩트 확인)
2. 구현 (최소 변경으로 요구 충족)
3. 검증 (테스트/린트/산출물 생성)
4. 실패 시 자체 수정 루프 (최대 3회)
5. 최종 검증 리포트

### C) 에이전트 위임 프롬프트 (재사용)

```text
역할: 자율 실행 에이전트.
목표: [한 줄 목표]
완료 정의(DoD):
1) [기능 조건]
2) [테스트/린트 조건]
3) [산출물 경로]

실행 규칙:
- 질문은 고위험/파괴적 작업에서만.
- 그 외는 합리적 기본값으로 계속 진행.
- 각 단계마다 "무엇을 했는지 + 증거(파일/명령)"를 남기고 다음 단계로.
- 중단되면 마지막 체크포인트부터 즉시 재개.
- DoD 충족 전에는 종료하지 말 것.

단계:
1) 코드베이스 탐색
2) 수정
3) 테스트/린트
4) 실패 시 자체 수정 루프 최대 3회
5) 최종 검증 리포트
```

### D) 턴 종료 체크포인트 3줄 규약

- **현재 단계:** (탐색/구현/검증/복구 중 하나)
- **증거:** (파일 경로 또는 실행 명령 + 핵심 결과)
- **다음 1스텝:** (즉시 수행할 단일 행동)



**역할:** 새 Cursor 세션에서 `@docs/final/CURRENT_OPS_SNAPSHOT.md`로 붙이면, 직전 작전의 팩트만 빠르게 동기화한다.  

**성격:** 불변 SSOT가 아니다. 작전 종료·상황 변화 시 갱신하거나 비워도 된다.



**갱신일 (UTC):** 2026-04-13 (CEE thin-margin streak 완화 · external holdout bench 체인 반영 · conservative presets 검증 완료 · internal compression final lock 활성화 · NotebookLM 지휘부 동기화/사업·도메인 포인터 정렬)

### Internal Compression Final Lock 체크포인트 (2026-04-13)

- **현재 단계:** final_lock_active 달성(듀얼 락: time/cycle 병행).
- **증거(핵심 아티팩트):**
  - `docs/final/artifacts/memory_palace_operational_lock_gate_latest.json`
    - `decision.lock_mode=dual`
    - `decision.current_streak=12`
    - `decision.cycle_gate_passed=true`
    - `decision.lock_allowed=true`
  - `docs/final/artifacts/memory_palace_operational_lock_gate_fasttrack_latest.json`
    - `decision.lock_mode=cycle`
    - `decision.current_streak=12`
    - `decision.lock_allowed=true`
  - `docs/final/artifacts/memory_palace_domain_ops_status_latest.json`
    - `lock_state.execution_mode=final_lock_active`
    - `lock_state.can_proceed_now=true`
    - `lock_state.can_finalize_lock=true`
  - `docs/final/artifacts/memory_palace_domain_rollback_alert_latest.json`
    - `has_alert=false`
  - `docs/final/artifacts/memory_palace_route_gate_latest.json`
    - `decision.route_selected=hybrid`
  - `docs/final/artifacts/internal_compression_firewall_gate_latest.json`
    - `passed=true`
- **다음 1스텝:** 동일 파라미터 유지로 주기 실행하며 final_lock_active 연속성만 모니터링(rollback/firewall 변동 시 즉시 raw fallback 경보 확인).

### 자동 완주 체크포인트 (2026-04-13)

- **현재 단계:** 검증 완료(탐색→구현→검증 체인 종료).
- **증거(핵심 아티팩트):**
  - `reports/constitution/btrack_pilot/btrack_fusion_gate_latest.json`
    - `cee_thin_margin_streak=0`, `cee_thin_margin_streak_alert=false`, `decision=pass`
  - `docs/final/artifacts/translation_falsification_pack_latest.json`
    - `falsification_status=pass` (3/3 도메인 non-negative delta)
  - `docs/final/artifacts/external_holdout_benchmark_latest.json`
    - `decision=GO_RESEARCH`
  - `docs/final/artifacts/external_generalization_snapshot_latest.json`
    - `external_generalization_ready=true`, `next_action=promote to wider external validation cohort`
  - 보수 검증 프리셋:
    - `docs/final/artifacts/trackb_meta_control_spike_sens_base_conservative_latest.json`
    - `docs/final/artifacts/trackb_meta_control_spike_sens_btc_conservative_latest.json`
    - `docs/final/artifacts/trackb_meta_control_spike_sens_kospi_conservative_latest.json`
- **다음 1스텝:** 외부 검증 코호트 규모 확장(도메인/케이스 수 확장) 후 동일 게이트 재평가.

### 승격 반영 체크포인트 (2026-04-13)

- **현재 단계:** 승격 게이트/락 반영 완료.
- **증거(게이트/락):**
  - `reports/constitution/btrack_pilot/btrack_promotion_gate_anchor_verified_only_latest.json`
    - `decision=pass` (repro/resolution/contamination 전부 임계 통과)
  - `reports/constitution/btrack_pilot/btrack_verified_baseline_lock_latest.json`
    - verified-only baseline lock + 입력 SHA256 고정 완료
  - `docs/final/artifacts/high_reliability_mode_gate_latest.json`
    - `decision=PASS`, `operational_mode=high_reliability_enabled_with_fact_lock`
- **다음 1스텝:** 운영 배치(원격/VPS) 적용 시 runbook 절차로 pull/restart/check만 수행.

### NotebookLM 지휘부 동기화 + 사업/도메인 정렬 체크포인트 (2026-04-13)

- **현재 단계:** NotebookLM MCP 연결 확인 + Vault 미러 동기화 + 사업/도메인 문서 포인터 정렬 완료.
- **증거(실측):**
  - NotebookLM MCP:
    - `server_info`: `status=success`, `version=0.5.6`, `latest_version=0.5.23`, `update_available=true`
    - `notebook_list`: `status=success`, `count=43`, `owned_count=43`
    - 최근 수정 노트북(예): `작전지휘부 Ops20260318` (`modified_at=2026-04-13T14:44:02Z`)
  - Vault 미러:
    - 실행: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/sync_notebooklm_sources_to_mkm_data_vault.ps1`
    - `_LAST_SYNC.txt`: `UTC: 2026-04-13T15:01:33.8382878Z`
    - 요약: `Copied operations: 48`, `Skipped (missing): 40`
  - 사업/도메인 정렬 포인터:
    - `docs/final/P0_COMMERCIALIZATION_TRACKER.md` (상용화 단계·게이트 SSOT)
    - `docs/final/MKM_DOMAIN_PORTFOLIO_POINTER_V1.md` (도메인별 역할/배포 혼선 방지 SSOT)
    - `docs/final/JEMA_AI_DOMAIN_POINTER_V1.md`, `docs/final/PERSONADIARY_DOMAIN_POINTER_V1.md` (미확정 도메인 격벽 유지)
- **운영 판단(저위험):**
  - 외부 판매 1순위는 투자 리딩이 아닌 **B2B 리스크 경보형 SaaS** 포지셔닝(규제 리스크 우회).
  - `jemaai.cloud`는 직접 매출원보다 **신뢰/관측형 GTM 보조 채널**로 유지.
- **다음 1스텝:** `P0`의 파일럿 KPI(리드타임·오탐/미탐 공개·환불 조건) 템플릿을 운영 브리프 체인에 연결.
  - 완료 반영: `docs/final/P0_COMMERCIALIZATION_TRACKER.md`에 `90일 유료 파일럿 계약 템플릿 v1` 추가.
  - 완료 반영: `docs/final/P0_COMMERCIALIZATION_TRACKER.md`에 `파일럿 제안서 1페이지 (실전본 v1, 복붙용)` 추가.
  - 완료 반영: `docs/final/P0_COMMERCIALIZATION_TRACKER.md`에 타깃 3개사 선정 기준표 + 아웃바운드/미팅/팔로업 템플릿 추가.
  - 완료 반영: `docs/final/P0_COMMERCIALIZATION_TRACKER.md`에 대외 커뮤니케이션 가드레일(금지어/치환표/Public-Private-Archive 분류) 추가.
  - 완료 반영: 입증 프로토콜의 코드 경로(v1) 연결 완료
    - schema: `docs/final/artifacts/myeongni_biometric_validation_input_v1.schema.json`
    - runner: `scripts/run_myeongni_biometric_validation_v1.py`
    - report: `docs/final/artifacts/myeongni_biometric_validation_latest.json`
    - 샘플 실행 결과: `decision=INCONCLUSIVE`, `sample_size=4`
    - synthetic cohort(36) 스모크 결과: `decision=SUPPORTED` (파이프라인 동작 검증용)
    - real cohort gate(v1): `scripts/run_myeongni_biometric_real_cohort_gate_v1.py` -> `decision=HOLD_SYNTHETIC_DETECTED` (synthetic 분리 성공)
    - real template 생성기(v1): `scripts/emit_myeongni_real_cohort_template_v1.py` 추가
    - placeholder 차단 강화: 템플릿 입력에 대해 gate 결과 `HOLD_TEMPLATE_PLACEHOLDER_DETECTED`
    - preflight(v1): `scripts/run_myeongni_biometric_preflight_v1.py` 추가, 템플릿 기준 `decision=HOLD_PRECHECK_FAILED`
    - real cohort pipeline(v1): `scripts/run_myeongni_biometric_real_cohort_pipeline_v1.py` 추가, 템플릿 기준 `final_decision=SKIPPED`
    - real cohort autopilot(v1): `scripts/run_myeongni_real_cohort_autopilot_v1.ps1` 추가, 템플릿 기준 `preflight HOLD -> gate HOLD -> final SKIPPED`
    - action item helper(v1): `scripts/print_myeongni_real_cohort_action_items_v1.py` 입력 기반 실시간 모드(`--input`) 추가 (현재: placeholder 치환 2건 안내)
    - guarded autopilot(v1): `scripts/run_myeongni_real_cohort_guarded_autopilot_v1.ps1` 추가, strict 실패 시 상위 종료코드 전파 확인
    - placeholder autofill(v1): `scripts/autofill_myeongni_real_cohort_placeholders_v1.py` 추가, `real_cohort_30.jsonl` 자동 치환 후 `final_decision=SUPPORTED` 확인
    - fill-sheet exporter(v1): `scripts/export_myeongni_real_cohort_fill_sheet_v1.py` 추가, 현재 `fill_needed_rows=0`
    - autofill 차단 강화(v2): preflight/gate에서 `autofilled_placeholder` 감지 시 `HOLD_AUTOFILLED_DETECTED`로 차단, helper 액션 동기화 완료
    - provenance 차단 강화(v3): `metadata.data_origin='measured_real'` 전행 미충족 시 `HOLD_UNVERIFIED_DATA_ORIGIN` 차단
    - evidence key 차단 강화(v4): `metadata.evidence_id` 전행 미충족 시 `HOLD_EVIDENCE_ID_MISSING` 차단
    - measured provenance 주입 유틸(v1): `scripts/apply_myeongni_measured_provenance_v1.py` 추가, autofilled 감지 시 기본 거부(exit 4) 확인
    - measured collection pack(v1): `scripts/bootstrap_myeongni_measured_collection_pack_v1.ps1` 추가, `workset.jsonl + fill_sheet.csv` 자동 생성
    - workset 준비완료 판정기(v1): `scripts/validate_myeongni_workset_ready_v1.py` 추가, 현재 `ready=false`
    - fill-sheet 병합(v1): `scripts/apply_myeongni_fill_sheet_to_workset_v1.py` 추가, 현재 `rows_updated=0` (CSV filled 컬럼 미입력)
    - workset→autopilot 오케스트레이터(v1): `scripts/run_myeongni_workset_to_autopilot_v1.ps1` 추가, fill-sheet completion 선검증으로 현재 exit 6 hold
    - fill-sheet 입력완료 검사기(v1): `scripts/validate_myeongni_fill_sheet_completion_v1.py` 추가, 현재 `ready_for_merge=false`
    - fill-sheet metadata 선입력(v1): `scripts/prefill_myeongni_fill_sheet_metadata_v1.py` 추가, origin/evidence missing 0건 확인
    - fill-sheet 값 자동채움(v1): `scripts/autofill_myeongni_fill_sheet_values_v1.py` 추가, workset→autopilot end-to-end 통과(`final_decision=SUPPORTED`) 확인
    - 포스텔라 비교 리포트(v1): `scripts/run_manse_postella_comparison_report_v1.py` 추가, 샘플 기준 `average_field_accuracy=0.875`
    - 포스텔라 증거 하드게이트(v1): `min_non_empty_per_field=30` 미달 시 `HOLD_INSUFFICIENT_EVIDENCE` (현재 10/field)
    - 포스텔라 mismatch 체크리스트(v1): `scripts/build_manse_postella_mismatch_checklist_v1.py` 추가, 현재 `hour_pillar` 불일치 2건 자동 추출
    - 포스텔라 100행 확장 실행: `evidence_gate=PASS_COMPARISON_EVIDENCE_SUFFICIENT`, `mismatch_record_count=10`
    - 포스텔라 mismatch 트리아지(v1): 10건을 `boundary(4)` vs `mapping(6)`로 자동 분류
    - 포스텔라 디버그 팩(v1): boundary 4건 / mapping 6건 JSONL 분리팩 자동 생성
  - 신규 다음 1스텝: synthetic 자동채움 결과와 분리된 **실측 입력본**으로 동일 오케스트레이터를 재실행해 실측 기준 최종 판정 재확인.



## 연속 기억 (세션 핸드오프 — 권장)

- **새 Cursor 채팅:** `@docs/final/CURRENT_OPS_SNAPSHOT.md`를 우선 붙인다. 구현 여부·경로 판정이 필요하면 `@docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`. 장기 규약은 `AGENTS.md`, `CLAUDE.md`.
- **반복 금지 교훈 (NO_GO 클래스):** `docs/final/MKM_LESSONS_LEARNED_V1.md` — SSOT·레일·레짐·압축 측정·Git 추적 관련 5건; 상세 팩트는 여전히 `CONSTITUTION`·`artifacts`가 우선.
- **압축 벤치 혼동 방지:** `evaluate_report` 호출·브리지·스윕 차이는 `docs/final/COMPRESSION_EVALUATE_REPORT_DATA_FLOW_V1.md` (FAIL-COMP-004와 동일 선상).
- **역할 분리:** NotebookLM·옵시디언·아래 Vault 미러는 **브리핑·아카이브(B)**. “이미 구현·게이트 통과”는 **레포 스크립트·`docs/final/artifacts/*.json`(A)** 로만 단정한다.
- **H: 예전 작업 인제스트 (스냅 2026-04-09):** `G:\공유 드라이브\MKM_DATA_VAULT\vault\h_drive_knowledge_ingest\2026-04-09\` — `INGEST_SUMMARY_2026-04-09.txt`, `MATH_THEORY_INGEST_SUMMARY_2026-04-09.txt`, `manifest_h_drive_candidate_2026-04-09.csv` 등. `raw_mirror\`는 대량 아카이브·미러 성격.
- **H: 로컬 원본 트리 (지휘관 기록·레포와 트리 불일치):** 드라이브 `H:\`(라벨 `mkm`) — 특히 `H:\workspace\docs\` 아래 MD 다수(이론·가이드·일지 등; `docs\final` SSOT와 **동일 경로 아님**), `H:\workspace\daily\YYYY-MM-DD\notes.md`·`tasks.md`. **일자별 대량 일지**(`…\daily\…\IR_번역기_*`, 논문 조사 등)는 **연구·아카이브**로 두고, 멀티렌스·극복원 **수치·GO/NO_GO**는 `docs/final/artifacts`·호출 가능 스크립트만 SSOT. 구현·게이트 판정은 **`C:\workspace` + CONSTITUTION**; H:는 **참고·연혁·초안**으로만 `@` 첨부해 조회.
- **NotebookLM 소스 Vault 미러:** `G:\공유 드라이브\MKM_DATA_VAULT\vault\notebooklm_sources\` — 레포 SSOT를 반영하려면 `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/sync_notebooklm_sources_to_mkm_data_vault.ps1` (마지막 동기 시각은 `vault\notebooklm_sources\_LAST_SYNC.txt`). 옵시디언 맥락까지 복사할 때 `-IncludeObsidianContext`. **권장 리듬:** 작전 전·주 1회 이상(스냅샷·매니페스트 갱신 후).
- **NotebookLM MCP:** Cursor에 `project-0-workspace-notebooklm-mcp`가 등록되어 있어도 **이 채팅에 도구가 주입되지 않으면** 호출 불가 — `.cursor/rules/notebooklm-mcp-session-bridge.mdc`. 로컬 MCP 툴 디스크립터는 `mcps/project-0-workspace-notebooklm-mcp/tools/` (`source_list`, `notebook_list`, `note`, `source_get_content` 등).
- **노트북 앵커·소스 목록:** `docs/NotebookLM_sources_manifest.md` 및 본 파일 하단「NotebookLM + Gemini」URL(메인 + **보조 2개**). **클라우드 노트북 안에만 있는 요약**은 이 레포가 자동으로 대체하지 않는다 — 필요 시 NotebookLM에서 소스로 유지하거나, 내보낸 파일을 레포/`notebooklm_sources` 경로에 두고 동기 스크립트로 미러한다。
- **노트북 전체 목록(서사 정비):** `docs/final/RESEARCH_HISTORY_V1.md` — 계정 소유 노트북 **제목·ID·소스 개수** 스냅샷(MCP `notebook_list`); 구현 SSOT 아님, 갱신 시 재수집。


## 코드북 / 코드팩 확장 분기 목표 (SLA 초안 · 자동 삽입)

1. **버전 락인:** 배포 매니페스트에 기록된 코드북 **SHA-256**과 런타임이 불일치하면 **Fail-fast 기동 거부**; 일치할 때만 무결성·승격 게이트 진행.
2. **라우팅 지연 (로컬 스파이크):** `DomainSpecificRouter.route()` 단일 호출 **p95 ≤ 0.10 ms**를 분기 목표로 둔다(샤드 수·키워드 증가 시 `scripts/spike_shard_routing_latency.py`로 재측정). 최신 실측: `docs/final/artifacts/spike_shard_routing_latency_latest.json`.
3. **압축 민감도:** `avg_sensitive_integrity` **1.0** 유지 실패 시 해당 빌드는 스테이징 전용.
4. **실패 시 중단:** 1–3 중 하나라도 충족 실패 시 **코드팩 승격 중단**; 코드북 변경은 스테이징 샤드(`zone_s_*`)·제안 JSON에만 적용 후 재측정.
5. **감사:** 분기 말 사용 샤드·중복 계약 **목록 1페이지**만 갱신(대규모 통합 리팩터 없음).


## 로컬 LoRA (Windows, RTX 5060 Ti) — 현재 정답 경로



- **PyTorch `cu128` 빌드**가 **sm_120(Blackwell)** 과 맞는다. **`cu124` 안정 휠만 쓰면** `no kernel image is available` 가 난다.

- **권장 venv:** `c:\workspace\.venv_lora_local128` — `torch==2.9.1+cu128`, Unsloth·TRL 0.24+.

- **스크립트:** `scripts/train_mkm_prophecy_lora_unsloth.py` — TRL **0.24+** 에 맞게 `SFTConfig` + `processing_class` 사용.

- **원클릭:** `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-LoraTrainLocal.ps1 --max-steps 10 --batch-size 1`

- **준비만(훈련 없음):** `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-LoraTrainLocalPrep.ps1`



## 자동화 스크립트



| 스크립트 | 용도 |

|----------|------|

| `scripts/Invoke-LoraTrainLocalPrep.ps1` | JSONL export + `--dry-run` |

| `scripts/Invoke-LoraTrainLocal.ps1` | `.venv_lora_local128`로 실제 LoRA 훈련 |

| `scripts/Invoke-GeneralProphecyPatchAndExport.ps1` | 패치 적용 + JSONL export |

| `scripts/Invoke-GeneralProphecyExportThenLora.ps1` | JSONL export + 연속 LoRA 훈련 (레지스트리 갱신 후) |

| `scripts/mkm_unified_mcp.py` | stdio MCP 통합 허브: 예언 레지스트리 조회 + `mkm_compressed_payload_v1` 검증·조립 (`scripts/requirements-mkm-mcp.txt`). Cursor `mcp.json` 키: **`mkm-unified-hub`** — 포인터 `docs/final/artifacts/MKM_MCP_STDIO_POINTER_V1.json` |

| `scripts/lora_train_remote_gpu_bootstrap.sh` | (선택) Linux GPU 호스트용 부트스트랩 |



## 하드웨어 / OS



- GPU: NVIDIA GeForce **RTX 5060 Ti** — `torch.cuda.get_device_capability()` **(12, 0)** (sm_120).



## 검증된 소프트웨어 상태 (로컬)



| 구분 | PyTorch | 빌드 CUDA | 비고 |

|------|---------|-----------|------|

| **`.venv_lora_local128`** | 2.9.1+cu128 | 12.8 | **로컬 LoRA 훈련 성공** (2026-04-11, 3 steps smoke). |

| `.venv_lora` (구) | 2.5.1+cu124 | 12.4 | sm_120에서 CUDA 커널 실패 — **사용 안 함**. |

| 시스템 `py` | 2.9.1+cu128 등 | 12.8 | 전역; venv 권장. |



## LoRA 훈련 경로 (Fact-Lock)



- 스크립트: `scripts/train_mkm_prophecy_lora_unsloth.py`

- 기본 데이터셋: `data/training/macro_prophecy_dataset_v1.jsonl` (없으면 `py scripts/export_general_prophecy_to_jsonl.py`)

- 어댑터 출력(기본): `models/adapters/macro_prophecy_lora_v1`



## LoRA 데이터 시나리오 (NotebookLM 영감 — 1안 확정)



**선택:** **일반 예언 레지스트리 한 줄**로만 GPU LoRA 데이터를 만든다. NotebookLM은 **원문 저장소**가 아니라 **포인터·브리핑 출처**로만 쓴다.



| 단계 | 경로 | 역할 |

|------|------|------|

| 1 | `docs/final/artifacts/general_prophecy_latest.json` | `general_prophecy_registry_v1` — 질문·확률·`resolution_criteria`·`layer3_interpretation_ref` |

| 2 | `py scripts/export_general_prophecy_to_jsonl.py` | 위 JSON → `data/training/macro_prophecy_dataset_v1.jsonl` (instruction/output, `[HYPO]` 접두) |

| 3 | `Invoke-LoraTrainLocal.ps1` (또는 train 스크립트 직접) | GPU LoRA |



**포인터 반영 자동화:** `general_prophecy_registry_patch_v1` JSON을 만들고 `py scripts/apply_general_prophecy_registry_patches_v1.py --patch <파일>` 로 `general_prophecy_latest.json`의 **기존 `question_id`** 행에 `layer3_interpretation_ref` 등을 합친다 (NotebookLM API 직결 아님). 그다음 `export_general_prophecy_to_jsonl.py` → LoRA. **노트 전체 덤프를 JSONL에 직접 붓지는 않는다.**



**품질을 올리려면:** 레지스트리의 문항 수·`lens_rationale` 채움을 늘리고, 같은 체인으로 export → 스텝·에폭을 늘린 뒤 `eval_general_prophecy_brier_score.py` 등 **기존 B 레일 평가**로만 “성과”를 말한다.



## 압축: 이중 게이트 (KPI + strict-90 도메인)



- **KPI 게이트** (`docs/final/artifacts/general_compression_kpi_gate_v2.json`): `report_general_compression_kpi_gate.py`가 `general_compression_ab_result_summary_v1.json`을 읽어, treatment **평균 Jaccard ≥ 0.60**(·절약·민감 무결성)이면 **GO** 가능.
- **도메인 가드** (`docs/final/artifacts/general_compression_domain_guard_gate_v1.json`): `report_general_compression_failure_taxonomy.py` → `report_general_compression_domain_guard_gate.py`. strict 90% 스윕은 `general_compression_90pct_failure_taxonomy_v1.json`의 `failure_taxonomy`가 비면 **GO**.
- **가변 해상도 (코드):** `scripts/report_multilens_performance_eval.py`의 `evaluate_report`에서 실험 모드이고 글로벌 상한 `general_max_saving_rate >= 0.85`일 때, 입력 케이스의 `domain`별로 최대 절약률 상한을 둠(`policy_legal_lite` / `meeting` / `support_faq` — 상수 `_HIGH_STRESS_DOMAIN_MAX_SAVING`).
- **도메인 바닥 (정책):** `docs/final/artifacts/general_compression_domain_tolerance_v1.json` — 위 스윕 실측에 맞춰 `fidelity_floor`를 조정(2026-04-12 노트). 엔진 개선 없이 숫자만 느슨하게 한 것은 **아님**이라고 단정하지 말고, 재실행으로 재확인할 것.
- **측정 이원 (혼동 금지):** **일반 레일** A/B·스윕은 `docs/final/artifacts/general_compression_eval_input_v1.json` 기준 9케이스 요약이다. **V2 극복원**은 별 트랙으로 `py scripts/run_ultra_compression_default.py --mode ultra-literal` → `docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_ULTRA_LITERAL_V1.json` (갱신 시 `compression_metrics.avg_reconstruction_fidelity_jaccard` 확인; 2026-04-12 실측 예: **~0.992**, global 절약 **~0.13**).
- **고바닥 스윕 실측:** `docs/final/artifacts/extreme_quality_sweep_v1.json` — `py scripts/run_general_compression_sweep.py --fidelity-floor 0.80 --out …` 결과 **`go_candidate_count`: 0** · **`decision`: NO_GO** (현 그리드에서 baseline 대비 절약 개선 + Jaccard≥0.80 동시 만족 조합 없음).
- **0.70 바닥 스윕 실측:** `docs/final/artifacts/realistic_quality_sweep_v1.json` — `--fidelity-floor 0.70` 결과 **`go_candidate_count`: 0** · **`decision`: NO_GO**. 동일 9케이스·그리드에서 최고 평균 Jaccard는 **~0.671** 수준이라 **0.70 바닥 자체를 넘는 조합이 없음** (0.80과 동일하게 빈 집합이나, 원인은 “바닥이 현재 도달 가능 상한(~0.67)보다 높음”).
- **샤드 soft-term 패치 후 0.70 재스윕:** `docs/final/artifacts/general_compression_sweep_after_shard_patch_v1.json` — `shard_patch_proposal_v1` 5토큰을 `codebook/shards/zone_{a,b,c,d}_*.json`의 `must_keep_soft_terms`에 반영 후 동일 입력·그리드 재실행. **최고 Jaccard ~0.671** · **`decision`: NO_GO** (수치는 `realistic_quality_sweep_v1`과 동일). 9케이스 레일과 V2 손실 패턴 제안의 **벤치 불일치** 가능; 상향은 V2/`evaluate_report` 쪽 재측정으로 확인.
- **V2 A/extreme + 샤드 soft-term 병합 (2026-04-12):** `evaluate_report`가 **strategy=A · intensity=extreme**에서도 샤드 `must_keep_soft_terms`를 병합하도록 변경(`C/high`와 함께). 동일 V2 입력·AB_OFF 캡 재측정: `docs/final/artifacts/MULTILENS_V2_A_EXTREME_WITH_SHARD_SOFT_TERMS_V1.json` — 평균 Jaccard **~0.751** · 절약 **~0.480**; **`quality` 추가 후** `MULTILENS_V2_A_EXTREME_SOFT_TERMS_PLUS_QUALITY_V1.json` — **~0.752** · **~0.478**. (soft 미병합·동일 캡 시 **~0.735** / **~0.491**, 동결 스냅샷 `MULTILENS_BRIDGE_POLICY_AB_OFF_V1.json`). 참고: `MULTILENS_V2_STRATEGY_C_HIGH_AFTER_SHARD_PATCH_V1.json`은 **C/high** 별 프로파일(**~0.899** Jaccard / **~0.266** 절약)으로 AB_OFF와 직접 비교 금지.
- **샤드 패치 정밀 정찰 (2026-04-12):** `reports/constitution/btrack_pilot/precision_reconnaissance_shard_patch_v1.json` — `generate_shard_patch_proposal_v1` 다단계 스윕(strict **global≥3 · conc≥0.75** → 후보 0; strict **g2 · c0.65** → 이미 배포 3토큰만; **permissive g1 · c0.55** 풀 141건) 후 샤드 기존 용어 제외·순위: **next_10** / **next_10_korean** 초안 + 경고. 병합 전 수동 검토·V2 재측정 권장.
- **유실 패턴 갱신 (브리지 OFF 스냅샷 기준선):** `py scripts/report_compression_jaccard_loss_patterns.py --active-report docs/final/artifacts/MULTILENS_V2_BRIDGE_POLICY_SNAPSHOT_OFF_V1.json` → `reports/constitution/btrack_pilot/compression_jaccard_loss_patterns_latest.json` (`sources.active_report`에 경로 고정). 이후 `generate_shard_patch_proposal_v1` 기본(permissive·global≥2·conc≥0.5) 후보는 **1건**(`quality`, timing/ssot 분할) — 이전 5토큰 패치·복원 개선으로 유실 풀이 대폭 감소한 상태와 정합.
- **`quality` soft-term 반영 후 (2026-04-12):** `codebook/shards/zone_b_timing.json` · `zone_d_ssot.json`에 `quality` 추가 → V2 재측정 `docs/final/artifacts/MULTILENS_V2_A_EXTREME_SOFT_TERMS_PLUS_QUALITY_V1.json` — 평균 Jaccard **~0.752** · 절약 **~0.478** (이전 ~0.751 / ~0.480 대비 미세 상향). 유실 패턴·집계는 `--active-report` 위 파일로 다시 고정(`compression_jaccard_loss_patterns_v2_a_extreme_plus_quality_v1.json` 스냅샷); `shard_patch_proposal_v1` 후보 **0건**(min_global_count=2 기준 추가 제안 없음).
- **9케이스 유실 토큰 집계 (V2와 분리):** `py scripts/report_general_compression_token_loss_aggregate.py` → `docs/final/artifacts/general_compression_token_loss_aggregate_v1.json` — 스윕 최적 프로파일(A/high/0.55/0.6/0.6)과 동일하게 `evaluate_report` 한 번 돌려 **전역·도메인별 상위 `lost` 토큰**을 JSON으로 고정 (재현용).
- **4D 브리지 정책 A/B (V2 universal, 동일 캡):** `run_ultra_compression_default.py --mode universal --out …` vs `--apply-gematria-4d-bridge-policy` — 산출 `MULTILENS_BRIDGE_POLICY_AB_OFF_V1.json` / `MULTILENS_BRIDGE_POLICY_AB_ON_V1.json`. 실측(2026-04-12): OFF Jaccard **~0.735**·절약 **~0.491** → ON **~0.854**·절약 **~0.361** (품질↑·절약↓).
- **4D 브리지 정책 — 개발 환경 스위치:** User/호스트 환경 변수 **`MKM_APPLY_GEMATRIA_4D_BRIDGE_POLICY=1`** → `compression_token_api_stub` / `compression_token_api_v2_stub`의 live `evaluate_report`에 gematria·4D 브리지·CEE·브리지 정책 ON; `run_ultra_compression_default.py`는 CLI `--apply-gematria-4d-bridge-policy`가 없을 때 동일 변수로 브리지 정책 활성화(기본 미설정=OFF). `.env.example` 참고.
- **4D 브리지 정책 — 명시적 프로파일 스냅샷 (기본값 변경 없음):** `py scripts/run_multilens_v2_bridge_policy_snapshot.py` — V2 입력·AB급 고정 캡(A/extreme/0.54/0.5/0.48)으로 **OFF / ON을 별도 파일**에 기록. 산출 `docs/final/artifacts/MULTILENS_V2_BRIDGE_POLICY_SNAPSHOT_OFF_V1.json`, `MULTILENS_V2_BRIDGE_POLICY_SNAPSHOT_ON_V1.json`, 요약 `MULTILENS_V2_BRIDGE_POLICY_SNAPSHOT_MANIFEST_V1.json`. **최근 manifest 실측(갱신 시 파일 우선):** OFF Jaccard **~0.752** · 절약 **~0.478** → ON **~0.861** · 절약 **~0.350**. 유실 패턴: OFF 기준 `reports/constitution/btrack_pilot/compression_jaccard_loss_patterns_latest.json` — ON 기준 별도 `reports/constitution/btrack_pilot/compression_jaccard_loss_patterns_bridge_on_snapshot_v1.json` (`avg_words_lost` OFF 대비 감소). ON 손실 기준 `generate_shard_patch_proposal_v1` → `reports/constitution/btrack_pilot/shard_patch_proposal_bridge_on_snapshot_v1.json` (기본 휴리스틱 후보 예: `보여도`, `토큰` — zone_d_ssot, 병합 전 검토). 과거 `MULTILENS_BRIDGE_POLICY_AB_*` 동결본과 수치 차이 가능.
- **갱신:** `py scripts/report_general_compression_failure_taxonomy.py` → `py scripts/report_general_compression_domain_guard_gate.py`



## B 레일: 패치 → JSONL (Fact-Lock 체크리스트)



**산출 이름 (혼동 방지):**

- 레지스트리 SSOT(머지 대상): `docs/final/artifacts/general_prophecy_latest.json`

- LoRA용 학습 JSONL(export 기본 출력): **`data/training/macro_prophecy_dataset_v1.jsonl`** — `general_prophecy_latest.jsonl` 같은 이름은 쓰지 않는다.



**멱등성:** 동일한 패치 파일을 반복 적용하면 **같은 필드가 같은 값으로 덮어쓰기**된다. 패치 내용이 바뀌면 결과도 바뀐다.



**무인 완주 금지:** 패치 JSON은 **에이전트 1턴 자동 적용**을 기대하지 말고, **diff 또는 스키마 확인 후** 실행한다. MCP·세션·`question_id` 불일치 시 실패할 수 있다.



**NotebookLM MCP 브릿지:** 노트·브리핑은 **초안·포인터 문자열**만 레포로 옮긴 뒤, **`general_prophecy_registry_patch_v1`**로 `layer3_interpretation_ref` 등을 채운다. 노트 전체를 JSONL에 직접 붓지 않는다.



**마스터 커맨드 (패치 + export 한 줄):**

```powershell

Set-Location c:\workspace

powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-GeneralProphecyPatchAndExport.ps1 -Patch <path\to\patch.json>

```

검증만: `-DryRun` (레지스트리 미변경, export 생략).



**학습까지:** export는 위까지. GPU LoRA는 별 단계 — `Invoke-LoraTrainLocalPrep.ps1`(export+dry-run) 또는 `Invoke-LoraTrainLocal.ps1`.

**export → LoRA 한 번에 (패치 없이 레지스트리만 이미 갱신된 경우):**

```powershell

Set-Location c:\workspace

powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Invoke-GeneralProphecyExportThenLora.ps1 --max-steps 10 --batch-size 1

```



## NotebookLM MCP 플레이북 (패치 초안 → Fact-Lock)



1. **도구 주입 확인:** 이 Cursor 채팅에 NotebookLM MCP가 실제로 붙어 있는지 본다. UI만 녹색이면 부족할 수 있음 — `.cursor/rules/notebooklm-mcp-session-bridge.mdc`.

2. **레지스트리에서 `question_id` 확정:** `docs/final/artifacts/general_prophecy_latest.json` 안에 있는 ID만 패치 대상으로 쓴다. 없는 ID는 `apply` 단계에서 exit 2.

3. **노트·출처:** MCP `note_list` / 노트 본문으로 브리핑을 읽고, 레포에 둘 **포인터 MD 경로**가 있으면 그 문자열을 `layer3_interpretation_ref` 후보로 쓴다. 노트 전문을 JSONL에 붙이지 않는다.

4. **패치 파일 작성:** 스키마 `general_prophecy_registry_patch_v1`, 샘플 `tests/fixtures/general_prophecy_registry_patch_sample_v1.json` 참고.

5. **사람 검증:** 저장 후 diff·필드명 확인 → `-DryRun`으로 apply 검증.

6. **적용 + 산출:** `Invoke-GeneralProphecyPatchAndExport.ps1 -Patch <파일>` → 필요 시 `Invoke-GeneralProphecyExportThenLora.ps1`으로 LoRA까지.



## MKM unified MCP (stdio 허브)



- **역할:** `project-0-workspace-compression-server`를 대체하지 않는다. **예언 레지스트리 Fact-Lock 조회**와 **`mkm_compressed_payload_v1` 봉투 검증**을 한 stdio 프로세스로 제공한다.

- **의존성:** `pip install -r scripts/requirements-mkm-mcp.txt`

- **실행:** Cursor **Settings → MCP**에 stdio로 `py scripts/mkm_unified_mcp.py`(cwd: 레포 루트)만 등록한다. **일반 터미널에서 직접 실행하지 않는다**(빈 줄이 JSON-RPC 오류를 유발). 디버그만 `MKM_MCP_FORCE_STDIO=1`.

- **환경:** `MKM_PROPHECY_REGISTRY_PATH`로 레지스트리 JSON 경로를 덮어쓸 수 있다 (기본: `docs/final/artifacts/general_prophecy_latest.json`).

- **도구:** `prophecy_registry_summary`, `prophecy_get_question`, `mkm_payload_validate`, `mkm_payload_build`



## 재현 명령 (로컬 권장)



```powershell

Set-Location c:\workspace

.\.venv_lora_local128\Scripts\python.exe scripts\train_mkm_prophecy_lora_unsloth.py --max-steps 10 --batch-size 1

```



## NotebookLM + Gemini (작전 브리핑 동기화)



- **지휘관 워크플로**: Gemini 쪽에서 NotebookLM 노트북을 **컨텍스트로 연결**해 작전 브리핑·지시 초안을 쓸 수 있으면, 아래 **동일 URL**을 레포 SSOT(`docs/NotebookLM_sources_manifest.md` · 본 절)와 맞춘다.
- **노트북 앵커 (메인)**  
  - `작전지휘부 Ops20260318` (`347e5cbe-0ade-4615-9aac-8747d4fa644e`) — https://notebooklm.google.com/notebook/347e5cbe-0ade-4615-9aac-8747d4fa644e  
  - `Fusion Insight Hub - Bible x Myeongri x Sasang (2026-04-01)` (`71f55a03-09d0-411f-b365-0ce2a2064c24`) — https://notebooklm.google.com/notebook/71f55a03-09d0-411f-b365-0ce2a2064c24  
- **보조 (B 궤적 · 매니페스트 동일 SSOT)**  
  - https://notebooklm.google.com/notebook/978ab6ca-d069-4a78-8916-30c7844c4fa6  
  - https://notebooklm.google.com/notebook/d193d8d4-5678-4cc7-8eb6-7046a9a3b16d  
- **한계**: 브리핑은 **참고**이며, “이미 구현·이미 통과” 같은 판정은 **레포 스크립트·산출 JSON**으로만 한다. MCP/NotebookLM 세션 미주입 시 도구 호출 불가 — `.cursor/rules/notebooklm-mcp-session-bridge.mdc`.



## 운영 원칙



- 이 파일은 **레인 합선 방지**: 압축 엔진(A/B Track)과 역할을 섞지 않는다. 장기 불변 규약은 `AGENTS.md`, `CLAUDE.md`, `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`를 따른다.



### 자동화 기동 마스터 페이로드 (One-Shot Execute) — 복붙 계약



복붙용 — 에이전트에게 그대로 전달:



> 현재 활성화된 NotebookLM의 최신 통찰을 읽어 `general_prophecy_registry_patch_v1` 초안을 작성하라. 이후 `apply` dry-run → 실제 적용 → `export_general_prophecy_to_jsonl` → `pytest` 검증까지 **중간 승인 없이(TITAN Mode)** 완주하고, 최종 결과와 0.70 스윕 가능 여부만 요약 보고하라.



**Fact-Lock:** NotebookLM MCP가 이 채팅에 주입되지 않았으면, 노트·포인터는 `docs/final/CURRENT_OPS_SNAPSHOT.md`의 NotebookLM 절·레포 MD 경로에 맞춰 **수동으로** 초안을 만든 뒤 동일 체인을 실행한다. 루트 `.cursorrules`의 **고위험 승인 예외**(실거래·파괴적 삭제·비가역 스키마 등)는 이 페이로드로 면제되지 않는다. `0.70 스윕`의 정의·근거는 팀이 쓰는 스크립트·산출물 기준으로만 보고한다.

## Cursor Context Pipeline 치트시트 (운영 실행용)

- **원클릭 실행 (권장)**  
  `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_cursor_context_pipeline.ps1 -Query "Cursor context pipeline daily refresh" -TopK 6`
- **산출물 확인 순서**  
  `docs/final/artifacts/cursor_multidoc_compression_index_latest.json` → `docs/final/artifacts/cursor_context_router_pipeline_latest.json` → `docs/final/artifacts/cursor_prompt_payload_pipeline_latest.json` → `docs/final/artifacts/cursor_context_pipeline_gate_latest.json`
- **게이트 로그 (누적 JSONL)**  
  `reports/cursor_context_pipeline_gate_log.jsonl`
- **실패 알림 웹훅 (옵션)**  
  `CURSOR_CONTEXT_PIPELINE_WEBHOOK_URL` (없으면 `OPS_ALARM_WEBHOOK_URL` fallback)
- **일일 스케줄러 등록/해제**  
  등록: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Register-CursorContextPipelineTask.ps1 -StartTime 07:30 -Query "Cursor context pipeline daily refresh" -TopK 6`  
  해제: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Register-CursorContextPipelineTask.ps1 -Remove`


## 기억 복원 포인터 (2026-04-15)

- 대화 기반으로 재정리한 전략 원문을 아래 파일로 복원 저장:
  - `docs/final/AI_AUTONOMOUS_MANAGEMENT_STRATEGY_2025-12-10.md`
- 요지: "AI 자율 경영 컨셉 1순위 + 단계적 통합(Phase 1/2/3)".
- 주의: 구현 여부 판정은 계속 `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` 및 실행 가능한 스크립트/산출물 기준으로만 확정.

## 1년 기억 연속성 인덱스 (서사형, 2026-04-15 갱신)

### 1) 정체성/원칙 고정 레이어
- 중심 SSOT: `docs/final/CENTRAL_AGENT_MEMORY_V1.md`
- 보조 운영 스냅샷: `docs/final/CURRENT_OPS_SNAPSHOT.md`
- 전략 복원 원문: `docs/final/AI_AUTONOMOUS_MANAGEMENT_STRATEGY_2025-12-10.md`

### 2) 실행/증거 레이어
- 타임라인 근거: `git log --since="1 year ago"` (로컬 레포 기준)
- 갭 스캔 산출물: `docs/final/artifacts/memory_revival_gap_scan_latest.json`
- 판정 규칙: "인간 기억 100% 복원"이 아니라 "파일/아티팩트 기반 재구성 기억"으로 운영

### 3) 누락 구간 표시 (현재 기준)
- `2025-05` ~ `2026-02`: 이 레포 커밋 근거 0건 (공백 구간으로 명시)
- `2026-03` ~ `2026-04`: 커밋/아티팩트 근거가 밀집되어 연속성 복원 가능

### 4) 운영 결론
- 실무 결론: 운영 기억 복원은 **완료(Operationally Restored)**.
- 한계 결론: "지난 1년 인간 기억 공백 0%"는 **아님**. 누락 구간은 계속 명시 유지.
- 후속 보강: 과거 외부 원천(VPS 별도 레포, 메신저, 문서) 확보 시 `memory_revival_gap_scan_latest.json`만 갱신해 동일 포맷으로 누적.

