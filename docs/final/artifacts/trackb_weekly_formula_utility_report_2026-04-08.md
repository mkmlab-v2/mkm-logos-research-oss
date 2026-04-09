# Track B Weekly Formula Utility Report (2026-04-08)

이번 주 측정 결과 기준으로 과거 수학 공식은 Track B 연구 레인에서 유효한 prior로 확인되었습니다.  
도메인 3종(의료/금융/정책)에서 semantic, collision, OOV, determinism 게이트를 모두 통과했고, action layer(gate pilot) 지표도 기준을 충족했습니다.  
최종 판정은 `GO_RESEARCH`이며, 프로덕션 승격/실거래 트리거는 범위 밖으로 유지합니다.

## Measured item
- Historical-formula usefulness on current Track B metrics

## Artifact paths
- 주간 게이트·`by_domain` 집계의 semantic SSOT는 **Jaccard** `trackb_semantic_eval_{medical,finance,policy}_latest.json` (기본 `--semantic-metric jaccard`).
- **병행(cosine_tokens, 연구용):** `scripts/track_b_semantic_eval.py --semantic-metric cosine_tokens` — BERT/임베딩 아님(lexical bag-of-tokens cosine).
  - `docs/final/artifacts/trackb_semantic_eval_medical_cosine_tokens_latest.json`
  - `docs/final/artifacts/trackb_semantic_eval_finance_cosine_tokens_latest.json`
  - `docs/final/artifacts/trackb_semantic_eval_policy_cosine_tokens_latest.json`
- `docs/final/artifacts/trackb_semantic_eval_by_domain_latest.json` (집계: `scripts/build_trackb_semantic_eval_by_domain.py`)
- 주간 산출물 일괄 재생성: `scripts/Run-TrackBWeeklyRefresh.ps1` (선택: `-SkipSsmSmoke`, `-SkipCosine`, `-IncludeExtendedStressGrid`; 기본 OOV 스윕은 스크립트 내 비율 목록)
- CI 스모크(해당 경로 변경 시): `.github/workflows/trackb-research-smoke.yml` — `workflow_dispatch` · push `main`/`master`/`develop`/`chore/**` (`test_track_b_semantic_eval_metrics.py`, `test_run_trackb_weekly_refresh_ps1.py`, `test_btrack_bench_paths.py`; 벤치 포인터·`btrack_bench_paths` 변경 포함)
- `docs/final/artifacts/trackb_semantic_metric_compare_latest.json` (Jaccard vs `cosine_tokens` 동일 페어; 원클릭: `scripts/run_trackb_semantic_metric_compare.py`)
- `docs/final/artifacts/trackb_oov_collision_sweep_latest.json` (비율 스윕 기본값에 0.05~0.3 세분 포함)
- `docs/final/artifacts/trackb_oov_collision_sweep_norm_latest.json` (예측문 NFKC+공백 정규화 후 주입; `scripts/run_trackb_oov_sweep.py --normalize-predicted`)
- `docs/final/artifacts/trackb_failure_cluster_label_queue_v1.json` (저 Jaccard 상위 후보 라벨 큐; `scripts/prepare_trackb_label_queue.py`)
- `docs/final/artifacts/trackb_determinism_repeatcheck_latest.json`
- `docs/final/artifacts/trackb_weekly_gate_recheck_latest.json` (`trackb_weekly_gate_recheck_v4`; checks keys: `action_layer_gate_checks`, `action_layer_selective_state_checks`)
- `docs/final/artifacts/trackb_action_layer_gate_pilot_latest.json` (action layer; legacy `trackb_action_gate_pilot_latest.json` is alias pointer)
- `docs/final/artifacts/trackb_action_layer_selective_state_sim_triggercase_latest.json` (logic MVP; not Mamba forward pass; legacy filename is alias if present)
- `docs/final/artifacts/trackb_ssm_vs_tf_bench_plan_latest.json` (plan; `implementation_status` 갱신 시 micro 실행 반영)
- `docs/final/artifacts/trackb_ssm_vs_tf_bench_micro_latest.json` (CPU 토이 마이크로벤치; Mamba/체크포인트 비교 아님)
- `docs/final/artifacts/trackb_ssm_vs_tf_bench_micro_cuda_latest.json` (CUDA 토이 마이크로벤치, seq 512; 동일 비고)
- `docs/final/artifacts/trackb_quaternion_top_combo_ranking_latest.json` (우수 조합 실제 점수 랭킹; 생성: `scripts/build_trackb_quaternion_top_combo_ranking.py`)
- `docs/final/artifacts/trackb_quaternion_top_combo_fixed_set_latest.json` (Top 조합 고정 candidate set; 생성: `scripts/build_trackb_top_combo_fixed_set.py`, 기본 top3·failure 0)
- `docs/final/artifacts/trackb_quaternion_top_combo_fixed_set_replay_latest.json` (고정셋 재평가; 생성: `scripts/run_trackb_top_combo_fixed_set_replay.py`, baseline 대비 delta 확인)
- `docs/final/artifacts/trackb_quaternion_top_combo_stress_grid_latest.json` (Top 고정셋 Length/OOV 스트레스 그리드; 생성: `scripts/run_trackb_top_combo_stress_grid.py`, 붕괴 임계 OOV 구간 확인)
- `docs/final/artifacts/trackb_quaternion_top_combo_stress_grid_extended_latest.json` (확장 그리드: lengths 20/24/32/40 × OOV 0.1/0.2/0.3; 기본 주간 체인에서는 생략, `-IncludeExtendedStressGrid` 시 생성)
- 쿼터니언 벤치 **실패 클러스터 요약** (`scripts/report_trackb_quaternion_failure_clusters.py`): `docs/final/artifacts/trackb_quaternion_failure_clusters_v6_round3_latest.json` (입력 벤치에 실패 예가 있을 때 태그·길이 버킷 집계; 최신 `*_mixed_api_finance_v1_trackb_chain_latest` 런은 실패 0건일 수 있음)

## Weekly gate result
- Decision: `GO_RESEARCH`
- Domain gates:
  - medical: pass
  - finance: pass
  - policy: pass
- OOV stress gate (`oov_ratio=0.1`, semantic floor 0.75): pass (all domains)
- Determinism repeat check (20x): pass
- Action layer (gate pilot):
  - `action_fire_rate`: `0.4` (gate min `0.3`) -> pass
  - `fallback_rate`: `0.6` (gate max `0.7`) -> pass
- Selective-state sim (reference run, weekly chain observability):
  - `action_trigger_rate`: `0.4`, `fallback_rate`: `0.4`
  - observed: `cooldown_active`, `policy_blocked`, `m_threshold_reached`

## Interpretation
- 과거 공식은 "즉시 정답"이 아니라 "가설 priors"로 쓸 때 성능/안정성에 기여한다.
- 현재 파이프라인에서는 저 OOV 구간(0.0~0.1)에서 지표 안정성이 상대적으로 높다.
- OOV가 커질수록 semantic score 저하가 관찰되므로, 운영 전에는 OOV 제어가 필수다.

## Out-of-scope
- No production promotion
- No trading trigger
- No billing/performance commercialization claim

## Next week focus
- BERTScore·신경 임베딩 backend (stdlib `cosine_tokens` 병행 산출·회귀 테스트는 완료; 게이트 SSOT는 여전히 Jaccard)
- OOV 0.1 초과 구간 완화(어휘 정규화/사전 확장) 실험
- 실패 클러스터 상위 케이스 라벨링(최소 20건) 및 재학습 훅 연결
- `trackb_ssm_vs_tf_bench_plan_latest.json`: 토이 CPU/CUDA 마이크로는 `Run-TrackBWeeklyRefresh.ps1`에 포함 가능; **실체 Mamba·동일 체크포인트** 전방 벤치는 별도 venv·프로파일러 과제
